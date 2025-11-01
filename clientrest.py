from obu_operations import CAR_NAME

import requests
res = requests.post('http://localhost:5000/externalLights', json={"carName":CAR_NAME})
if res.ok:
    print(res.json())
