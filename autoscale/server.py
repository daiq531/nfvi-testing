import math
import time

from flask import Flask
app = Flask(__name__)

""" Client app sends GET request to server app container
http://<autoscale-server Service Cluster IP>/cpu, which triggers
this function to create cpu load in container
"""
def cpuload():
    etime = {}
    start_time = time.time()
    for x in range(1, 1000000):
        s = math.sqrt(x)
    end_time = time.time()
    time_taken = end_time - start_time
    etime["start_time"] = start_time
    etime["end_time"] = end_time
    etime["time_taken"] = time_taken
    return etime


""" This URL will be called by http client app. As the client app hits this URL, 
    cpuload function will be called and generate CPU load.
    Check cpuload.py for more information. """
@app.route('/cpu')
def firstapp():
    f = cpuload()
    return f
