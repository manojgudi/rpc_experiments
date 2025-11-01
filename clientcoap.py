import asyncio
import aiocoap

from obu_operations import CAR_NAME, FETCH_SID, bitToExteriorLightMap
import cbor2


async def main():
    context = await aiocoap.Context.create_client_context()

    # CoAP FETCH with request body car name ""
    req = aiocoap.Message(
        code=aiocoap.FETCH,              # RFC 8132 Fetch
        uri="coap://localhost/%s"%FETCH_SID,
        payload=CAR_NAME.encode()
    )

    try:
        resp = await context.request(req).response
        print(f"Code: {resp.code}")
        output = cbor2.loads(resp.payload)
        # light status
        index = (output[60001][4][1][1])
        lightStatus = bitToExteriorLightMap[index]
        print("Payload", output)
        #print(f"Payload: {resp.payload.decode(errors='ignore')}")
    except Exception as e:
        print("Failed to fetch:", e)

if __name__ == "__main__":
    asyncio.run(main())

