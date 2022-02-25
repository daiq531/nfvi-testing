import requests
from concurrent.futures import ThreadPoolExecutor

khost="compute5.ec2.calenglab.spirentcom.com"
svc_port="32151"

k6url = "http://" + khost + ':' + svc_port + '/'
connections_count = 10

def get_url(url):
    return requests.get(url)

def generate_load():
    with ThreadPoolExecutor(max_workers=connections_count) as pool:
        response_list = list(pool.map(get_url, urls))
        return response_list

if __name__ == "__main__":
    urls = [k6url]*connections_count
    load = generate_load()
    req_start_count = 0
    while req_start_count < connections_count:
        print("Connect no: {} and Elapsed time: {}".format((req_start_count + 1), load[req_start_count].elapsed))
        print("Response from server: {}".format(load[req_start_count].text))
        req_start_count += 1