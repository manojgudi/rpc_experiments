
from flask import Flask, render_template, request, redirect, jsonify
from obu_operations import CAR_NAME, shortTask, returnYANGOutput

import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__)

@app.route('/externalLights', methods=['POST'])
def handleLight():
    requestCarName = request.json["carName"]
    if requestCarName == CAR_NAME:
        status = shortTask()
        output = returnYANGOutput(status)
        return output

if __name__ == '__main__':
    app.run(host= '0.0.0.0',debug=False, port=5000)
