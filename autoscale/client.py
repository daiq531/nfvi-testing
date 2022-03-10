import requests
from flask import Flask

app = Flask(__name__)

url = "http://172.30.99.118/cpu"
def httpclient():
    r = requests.get(url=url)
    return r.text

""" This URL will be called by python script. With GET call to this URL, httpclient function will be called.
    httpclient function is intent to call this app's cpuload function (http://FQDN/cpu).
    Check httpclient.py for more information. """
@app.route('/')
def get():
    h = httpclient()
    return h