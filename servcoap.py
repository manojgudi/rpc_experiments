import asyncio
import aiocoap.resource as resource
import aiocoap
from obu_operations import CAR_NAME, FETCH_SID, shortTask, returnCCOutput, returnYANGOutput
import pycoreconf
import cbor2

sidFile = "./yang/car-model@unknown.sid"
ccm = pycoreconf.CORECONFModel(sidFile, model_description_file=None)

stencilPayload = returnYANGOutput(-1)
stencilPayload = ccm.toCORECONFFromJSON(stencilPayload)
stencilPayload = cbor2.loads(stencilPayload)


class FetchDemoResource(resource.Resource):
    async def render_fetch(self, request: aiocoap.Message) -> aiocoap.Message:
        # Check request body; do the "something" (sleep 1s) when car name matches
        if request.payload == CAR_NAME.encode():
            lightStatus = shortTask()
            output = returnCCOutput(stencilPayload, lightStatus)
            payload = cbor2.dumps(output)
            
            #print("OT", payload)

        else:
            print(request.payload)
            payload = b"no-op (send 123 to trigger work)"

        # Default success code for GET/FETCH is 2.05 Content; payload is fine here
        return aiocoap.Message(payload=payload, content_format=42)  # CBOR

async def main():
    # Build a site and bind our resource at /demo
    root = resource.Site()
    root.add_resource([FETCH_SID], FetchDemoResource())

    # Listen on UDP CoAP
    await aiocoap.Context.create_server_context(root, bind=('::', 5683))

    # Keep the server running forever
    await asyncio.get_running_loop().create_future()

if __name__ == "__main__":
    asyncio.run(main())

