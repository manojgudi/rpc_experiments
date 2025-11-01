import time
import random

# Constants
CAR_NAME = "roadrunner"
FETCH_SID = "60001"

bitToExteriorLightMap = {0:"lowBeamHeadlightsOn",
            1:"highBeamHeadlightsOn",
            2:"leftTurnSignalOn",
            3:"rightTurnSignalOn",
            4:"daytimeRunningLightsOn",
            5:"reverseLightOn",
            6:"fogLightOn",
            7:"parkingLightsOn"}


def returnYANGOutput(status):

    outputMessage = {
      "fetch": {
        "output" : {
        "carStatus": {
          "name": CAR_NAME,
          "exteriorLight": status
        }
      }}
    }

    return outputMessage

def returnCCOutput(stencilPayload, status):
    # Find the code
    bit = list(filter(lambda key: bitToExteriorLightMap[key] == status, bitToExteriorLightMap))[0]
    # Generated from pycoreconf
    stencilPayload[60001][4][1][2] = CAR_NAME
    stencilPayload[60001][4][1][1] = bit

    return stencilPayload



def lightStatus():
    """
    Randomly send a light status
    """
    index = random.randint(0, len(bitToExteriorLightMap)-1)
    status = bitToExteriorLightMap[index]
    return status


def shortTask():
    time.sleep(0.1)
    status = lightStatus()
    return status

def longTask():
    time.sleep(0.5)
    return lightStatus()

#print(shortTask())
