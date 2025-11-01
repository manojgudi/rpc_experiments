"""
Locust load test for benchmarking JSON‑RPC (HTTP) vs CoAP (aiocoap) latency.

It reuses the same request semantics as your uploaded clients:
- JSON‑RPC: POST http://<host>:<port>/jsonrpc method="fetch" params=[CAR_NAME]
- CoAP:     FETCH coap://<host>:<port>/<FETCH_SID> with payload=CAR_NAME (CBOR response)

Run
---
# Install deps
pip install locust requests aiocoap cbor2

# Env configuration (defaults shown)
export JSONRPC_URL="http://localhost:4000/jsonrpc"
export COAP_HOST="localhost"
export COAP_PORT="5683"
# Optional: select which users to run
export ENABLE_JSONRPC="1"   # set to 0 to disable
export ENABLE_COAP="1"      # set to 0 to disable

# Headless 10 users for 10 minutes, spawn rate 2/s
locust -f locustfile.py --headless -u 10 -r 2 -t 10m

# Web UI
locust -f locustfile.py

Notes
-----
* Locust is gevent-based; aiocoap is asyncio-based. We create a dedicated
  asyncio loop in a background thread for CoAP and submit coroutines to it.
* Latency is measured wall-clock (time.monotonic). We report to Locust via
  events.request.fire with request_type "JSONRPC" or "COAP" and name "fetch".
* For CoAP, we pre-create a client Context and reuse it for all requests.
* You can tag tasks with @tag and use --tags include/exclude if needed.
"""
from __future__ import annotations
import os
import time
import json
import threading
import asyncio
from typing import Optional

import requests
from locust import User, task, between, events

# Reuse constants from your codebase
from obu_operations import CAR_NAME, FETCH_SID  # noqa: F401

# ------------------------- JSON-RPC User (HTTP) ------------------------- #
class JsonRpcUser(User):
    wait_time = between(0.01, 0.05)
    abstract = True  # toggled via subclassing below

    def on_start(self):
        self.url = os.getenv("JSONRPC_URL", "http://localhost:4000/jsonrpc")
        self.session = requests.Session()

    @task
    def fetch(self):
        payload = {
            "jsonrpc": "2.0",
            "method": "fetch",
            "params": [CAR_NAME],
            "id": 1,
        }
        start = time.monotonic()
        try:
            resp = self.session.post(self.url, json=payload, timeout=10)
            elapsed_ms = (time.monotonic() - start) * 1000
            ok = (resp.status_code == 200)
            # Try to parse JSON for minimal validation
            try:
                _ = resp.json()
            except Exception:
                ok = False
            events.request.fire(
                request_type="JSONRPC",
                name="fetch",
                response_time=elapsed_ms,
                response_length=len(resp.content),
                response=resp,
                context={},
                exception=None if ok else Exception(f"Bad status or JSON: {resp.status_code}"),
            )
        except Exception as e:
            elapsed_ms = (time.monotonic() - start) * 1000
            events.request.fire(
                request_type="JSONRPC",
                name="fetch",
                response_time=elapsed_ms,
                response_length=0,
                response=None,
                context={},
                exception=e,
            )

# Concrete user enabled/disabled via env
if os.getenv("ENABLE_JSONRPC", "1") == "1":
    class JSONRPCUser(JsonRpcUser):
        abstract = False

# --------------------------- CoAP User (UDP) --------------------------- #
# Robust fix for Python 3.12 + gevent:
# Create ONE global asyncio event loop in a dedicated OS thread and a single
# aiocoap client Context bound to that loop. All Locust users submit their
# CoAP coroutines to that background loop via run_coroutine_threadsafe.
# This avoids calling run_until_complete() inside Locust greenlets and
# eliminates the "another loop is running" error.
from aiocoap import Message, Context, FETCH  # type: ignore
import cbor2  # type: ignore

class _GlobalCoap:
    _instance = None

    def __init__(self, host: str, port: int, path: str):
        import threading
        self.host = host
        self.port = port
        self.path = path
        self._ready = threading.Event()
        self._loop = asyncio.new_event_loop()
        self._ctx: Context | None = None
        self._thread = threading.Thread(target=self._runner, name="coap-loop", daemon=True)
        self._thread.start()
        if not self._ready.wait(timeout=10):
            raise RuntimeError("CoAP background loop failed to start")

    def _runner(self):
        asyncio.set_event_loop(self._loop)
        async def _setup():
            self._ctx = await Context.create_client_context()
            self._ready.set()
        self._loop.create_task(_setup())
        self._loop.run_forever()

    @classmethod
    def get(cls, host: str, port: int, path: str) -> "_GlobalCoap":
        if cls._instance is None:
            cls._instance = _GlobalCoap(host, port, path)
        return cls._instance

    def fetch(self, car_name: str, timeout: float = 10.0) -> bytes:
        assert self._ctx is not None
        uri = f"coap://{self.host}:{self.port}/{self.path}"
        req = Message(code=FETCH, uri=uri, payload=car_name.encode())
        async def _do():
            resp = await self._ctx.request(req).response
            return resp.payload
        fut = asyncio.run_coroutine_threadsafe(_do(), self._loop)
        return fut.result(timeout=timeout)

class CoapUser(User):
    wait_time = between(0.01, 0.05)
    abstract = True

    def on_start(self):
        host = os.getenv("COAP_HOST", "localhost")
        port = int(os.getenv("COAP_PORT", "5683"))
        path = os.getenv("COAP_PATH", os.getenv("FETCH_SID", str(FETCH_SID)))
        self._coap = _GlobalCoap.get(host, port, path)

    @task
    def fetch(self):
        start = time.monotonic()
        try:
            payload = self._coap.fetch(CAR_NAME)
            elapsed_ms = (time.monotonic() - start) * 1000
            try:
                _ = cbor2.loads(payload)
                exc = None
            except Exception as de:
                exc = de
            events.request.fire(
                request_type="COAP",
                name="fetch",
                response_time=elapsed_ms,
                response_length=len(payload),
                response=None,
                context={},
                exception=exc,
            )
        except Exception as e:
            elapsed_ms = (time.monotonic() - start) * 1000
            events.request.fire(
                request_type="COAP",
                name="fetch",
                response_time=elapsed_ms,
                response_length=0,
                response=None,
                context={},
                exception=e,
            )

if os.getenv("ENABLE_COAP", "1") == "1":
    class COAPUser(CoapUser):
        abstract = False

# --------------------------- RESTful JSON API User (HTTP) --------------------------- #
# Matches your client that POSTs to /externalLights with {"carName": CAR_NAME}
# and expects JSON back. Uses a persistent requests.Session for keep-alive.
class RestApiUser(User):
    wait_time = between(0.01, 0.05)
    abstract = True
    weight = int(os.getenv("REST_WEIGHT", "1"))

    def on_start(self):
        self.url = os.getenv("REST_URL", "http://localhost:5000/externalLights")
        self.session = requests.Session()

    @task
    def external_lights(self):
        start = time.monotonic()
        try:
            resp = self.session.post(self.url, json={"carName": CAR_NAME}, timeout=10)
            elapsed_ms = (time.monotonic() - start) * 1000
            ok = resp.ok
            try:
                _ = resp.json()
            except Exception:
                ok = False
            events.request.fire(
                request_type="REST",
                name="externalLights",
                response_time=elapsed_ms,
                response_length=len(resp.content),
                response=resp,
                context={},
                exception=None if ok else Exception(f"Bad status or JSON: {resp.status_code}"),
            )
        except Exception as e:
            elapsed_ms = (time.monotonic() - start) * 1000
            events.request.fire(
                request_type="REST",
                name="externalLights",
                response_time=elapsed_ms,
                response_length=0,
                response=None,
                context={},
                exception=e,
            )

if os.getenv("ENABLE_REST", "1") == "1":
    class RESTUser(RestApiUser):
        abstract = False

# --------------------------- Tips for analysis --------------------------- #
# After a run, Locust provides p50/p90/p95/p99 latencies per request_type.
# For a paper, export stats CSV (--csv) and report medians and tail latencies.
# Suggest also running tcpdump/wireshark to compute bytes-on-wire per request.

