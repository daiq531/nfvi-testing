import requests

url = "http://0.0.0.0:8080/cpu"
def httpclient():
    r = requests.get(url=url)
    return r.text