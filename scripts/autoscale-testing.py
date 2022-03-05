from sys import stdout
import requests
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import os
import json
import _thread
import time
import subprocess

# Fetch ip and port using 'get-http-client-url.sh' and update here
http_client_svc_external_ip = "compute5.ec2.calenglab.spirentcom.com"
http_client_svc_external_port = "32151"
kube_hpa = "cpuload-hpa"

k6url = "http://" + http_client_svc_external_ip + ':' + http_client_svc_external_port + '/'
connections_count = 500

d = datetime.now().strftime('%y-%m-%d_%H-%M-%S')
test_name = "HPA_test1-"

log_file = os.path.join(os.path.dirname(os.path.realpath(__file__)) + '/logs/' + test_name + str(d) + 'hpa-state.logs')
tmp_file = os.path.join(os.path.dirname(os.path.realpath(__file__)) + '/logs/' + '-hpa.json')
server_response_file = os.path.join(os.path.dirname(os.path.realpath(__file__)) + '/logs/' + test_name + str(d) + '-server.log')

def get_url(url):
    return requests.get(url)

def generate_load():
    with ThreadPoolExecutor(max_workers=connections_count) as pool:
        response_list = list(pool.map(get_url, urls))
        return response_list

def write_logs(response_from_server,elapse_time,connections_count):
    try:
        attempts = range(0,connections_count)
        print("Test results will be captured in {}".format(server_response_file))
        with open(server_response_file, 'a') as f:
            f.write('Connections:')
            for c in attempts:
                f.write('\n  - id: {}'.format(c))
                f.write('\n  elapse_time: {}'.format(elapse_time[c]))
                f.write('\n  server_text: {}'.format(response_from_server[c]))
                f.write('\n')
    except FileNotFoundError:
        print("The directory does not exist")


def spinner():
    while True:
        record_time = datetime.now().strftime('%y%m%d_%H%M%S')
        os.system('kubectl get hpa {} -o json > {}'.format(kube_hpa, tmp_file))
        with open(tmp_file, 'r') as input_file:
            data = json.load(input_file)
        with open(log_file, 'a') as output_file:
            output_file.write('\n\date: {}\n'.format(record_time))
            output_file.write('  name: {}\n'.format(data['metadata']['name']))
            output_file.write('  min_replicas: {}\n'.format(data['spec']['minReplicas']))
            output_file.write('  max_replicas: {}\n'.format(data['spec']['maxReplicas']))
            output_file.write('  current_replicas: {}\n'.format(data['status']['currentReplicas']))
            output_file.write('  desired_replicas: {}\n'.format(data['status']['desiredReplicas']))
        time.sleep(5)
        
def current_value(before_load, after_load):
    l1 = []
    l2 = []
    with open(before_load, 'r') as f:
        data = json.load(f)
        for items in data['items']:
            l1.append([items.get('metadata').get('name'), items.get('status').get('replicas')])

    with open(after_load, 'r') as f:
        data = json.load(f)
        for items in data['items']:
            l2.append([items.get('metadata').get('name'), items.get('status').get('replicas')])

    for i in range(len(l1)):
        if l1[i][1] < l2[i][1]:
            print("HPA happened")
        else:
            print("HPA not happened")

if __name__ == "__main__":
    _thread.start_new_thread(spinner, ())
    urls = [k6url]*connections_count
    load = generate_load()
    response_from_server = []
    _elapse_time = []

    req_start_count = 0
    while req_start_count < connections_count:
        response_from_server.append(load[req_start_count].text)
        _elapse_time.append(str(load[req_start_count].elapsed))
        req_start_count += 1
    write_logs(response_from_server, _elapse_time, connections_count)
    """ Files cleanup """
    os.remove(tmp_file)
    
"""    rs=os.system('kubectl get rs -o wide > rs_details_before_load-' + str(d) +'.log')
    hpa=os.system('kubectl get hpa -o wide > hpa_details_before_load-' + str(d) +'.log')
    pods=os.system('kubectl get pods -o wide > pods_details_before_load-' + str(d)+'.log')
    rs=os.system('kubectl get rs -o json > rs_details_before_load-' + str(d) +'.json')
    rs=os.system('kubectl get rs -o wide > rs_details_after_load-' + str(d) +'.logs')
    hpa=os.system('kubectl get hpa -o wide > hpa_details_after_load-' + str(d)+'.log')
    pods=os.system('kubectl get pods -o wide > pods_details_after_load-' + str(d)+'.log')
    rs=os.system('kubectl get rs -o json > rs_details_after_load-' + str(d) +'.json')"""