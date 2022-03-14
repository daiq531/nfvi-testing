from threading import Thread, Timer
import time
import json
from queue import SimpleQueue
import requests
from flask import Flask, request, Response, make_response

class HttpRequestClient(Thread):

    TIMER_INTERVAL = 0.01

    def __init__(self, url: str, rate: int):
        super().__init__()
        self.url = url
        self.rate = rate
        self.timer = None
        self.queue = SimpleQueue()
        self.flag_stop = False

    def timer_function(self):
        current = time.monotonic()
        
        # caculate http request count based on rate and actual timer interval
        duration = current - self.rate_begin_time
        count = (duration + TIMER_INTERVAL) * rate - self.sent
        self.queue.put_nowait(http_count)

        self.previous_mono = current

    def start_timer(self):
        self.timer = Timer(HttpRequestClient.TIMER_INTERVAL, self.timer_function)
        self.previous_mono = time.monotonic()
        self.timer.start()

    def run(self):
        self.start = time.monotonic()
        self.timer = Timer(HttpRequestClient.TIMER_INTERVAL, self.timer_function)
        self.timer.start()

        while not self.flag_stop:
            # get request count from queue
            request_count = self.queue.get()
            print("request_count: %f" % request_count)
            request_count = 1
            if request_count == 0:
                continue

            for i in range(request_count):
                resp = requests.get(self.url)
                resp.close()
                print("resp len: %d" % resp.length)

    def stop(self):
        self.flag_stop = True
        self.timer.cancel()

    def change_http_rate(self, rate):
        self.rate = rate

clientThread = None
app = Flask(__name__)

@app.route('/', methods=['GET'])
def index():
    ''' For readiness or liveness probe '''
    return 'OK'

@app.route('/start', methods=['GET', 'POST'])
def start():
    """
    Start generate load to http server deployment or query current status.
    For POST method, request body is json like below:
    {
        "target_url": "http://" + http_server_svc_ip,
        "rate": rate
    }
    For GET method, response body is json like below:
    {
        "target_url": "http://" + http_server_svc_ip,
        "rate": rate
    }
    :return: response object
    :rtype: str
    """
    global clientThread
    if request.method == "POST":
        data = request.get_json()
        if not clientThread:
            clientThread = HttpRequestClient(url = data["target_url"], rate = int(data["rate"]))
            # clientThread.start()
            return make_response(("create http traffic client success.", 200))
        else:
            if data["target_url"] == clientThread.url:
                clientThread.change_http_rate(int(data["rate"]))
                return make_response(("change http traffic client rate success.", 200))
            else:
                return make_response(("target url are different from original one.", 400))
    else:
        if clientThread:
            data = {
                "target_url": clientThread.url,
                "rate": clientThread.rate
            }
            return make_response(data)
        else:
            return make_response(("please start http traffic client first.", 400))

@app.route('/stop', methods=['POST'])
def stop():
    global clientThread
    data = request.get_json()
    if clientThread:
        if data["target_url"] == clientThread.url:
            clientThread.stop()
            clientThread = None
            return make_response(("stop http traffic client success.", 200))
        else:
            return make_response(("target url are different from original one.", 400))

    return make_response(("please start http traffic client first.", 400))