import requests
import json
from obu_operations import CAR_NAME

def main():
    url = "http://localhost:4000/jsonrpc"

    # Example echo method
    payload = {
        "method": "add",
        "params": [12, 32],
        "jsonrpc": "2.0",
        "id": 0,
    }

    payload = {
        "method" : "fetch",
        "params" : [CAR_NAME],
        "jsonrpc": "2.0",
        "id": 0,
     }


    response = requests.post(url, json=payload).json()
    print(response)

if __name__ == "__main__":
    main()
