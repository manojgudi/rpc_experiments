### What is it?

A test where a simple JSON like message is exchanged between three kind of services:
HTTP/RESTCONF-JSON, CoAP/CORECONF and JSON-RPC webservices

### Setup

#### On both sides
On both the devices: machine1 aka *client* and YoGoKo OBU aka *server* install python 3.5 and above.
Create a *virtualenv* .

Run pip to install all the dependencies:
```
$ pip install -r requirements.txt
```

#### On server side
Run the services on YoGoKo
All the services are configured to be deployment ready as more than performance, we're chasing average response size to see the most light weight combination of transport protocol and encoding.

```
$ python servrestful.py # RESTful Server
$ python servcoap.py    # CoAP Server    
$ python servrpc.py     # RPC Server
```

#### On client side

Configuring the IPs correctly in env.sh (and default values in locustfile.py) so locust knows where the servers are.
```
bash env.sh
```

Then run locust tool from the repository to save the result test10m\_18.csv to spawn 18 concurrent users (6 per service, concurrent requests for 10minutes) :
```
 $ locust -f locustfile.py --csv test10m_18.csv --headless -u 18 -r 1 -t 10m  
```
