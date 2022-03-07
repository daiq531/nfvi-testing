from sys import stdout
import requests
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import os
import json
import _thread
import time
import subprocess
import sys

"""
- March 7:
    1. On each iteration, add 3 mins wait
    2. Break the loop in two matching conditions (Can we apply and condition over there?)
        - iterate_count is completed
        - OR Pods reached to max replica
    3. End of each iteration, record on which node the pod was running
    4. Fetch 'http_client_svc_external_ip' and 'http_client_svc_external_port' vars values during run time
        Check scripts/get-http-client-url.sh for reference
    5. Take 'iterate_count' vaule as user input or argument
    5. Cleanup of temp files
"""
# Fetch ip and port using 'get-http-client-url.sh' and update here
http_client_svc_external_ip = "compute5.ec2.calenglab.spirentcom.com"
http_client_svc_external_port = "32151"
kube_hpa = "cpuload-hpa"

k6url = "http://" + http_client_svc_external_ip + ':' + http_client_svc_external_port + '/'
connections_count = 10
iterate_count = int(sys.argv[1])
#3count = 1

d = datetime.now().strftime('%y-%m-%d_%H-%M-%S')
test_name = "HPA_test1-"

log_file = os.path.join(os.path.dirname(os.path.realpath(__file__)) + '/logs/' + test_name + str(d) + 'hpa-state.logs')
pod_node_file = os.path.join(os.path.dirname(os.path.realpath(__file__)) + '/logs/' + test_name + str(d) + 'pod-node-details.logs')
tmp_file = os.path.join(os.path.dirname(os.path.realpath(__file__)) + '/logs/' + 'hpa.json')
tmp_file_1 = os.path.join(os.path.dirname(os.path.realpath(__file__)) + '/logs/' + 'hpa_1.json')
tmp_file_2 = os.path.join(os.path.dirname(os.path.realpath(__file__)) + '/logs/' + 'hpa_2.json')
server_response_file = os.path.join(os.path.dirname(os.path.realpath(__file__)) + '/logs/' + test_name + str(d) + '-server.log')
tmp_file_3 = os.path.join(os.path.dirname(os.path.realpath(__file__)) + '/logs/' + 'hpa_3.json')


def get_url(url):
    return requests.get(url)

def generate_load(urls):
    with ThreadPoolExecutor(max_workers=connections_count) as pool:
        response_list = list(pool.map(get_url, urls))
        return response_list

def write_logs(response_from_server,elapse_time,connections_count):
    try:
        attempts = range(0,connections_count)
        #print("Test results will be captured in {}".format(server_response_file))
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
    #hpa_state_data = []
    count = 1
    while True:
        #current_state = {}
        record_time = datetime.now().strftime('%y%m%d_%H%M%S')
        os.system('kubectl get hpa {} -o json > {}'.format(kube_hpa, tmp_file))
        with open(tmp_file, 'r') as input_file:
            data = json.load(input_file)
        """current_state = {
            'date': record_time,
            'name': data['metadata']['name'],
            'min_replicas': data['spec']['minReplicas'],
            'max_replicas': data['spec']['maxReplicas'],
            'current_replicas': data['status']['currentReplicas'],
            'desired_replicas': data['status']['desiredReplicas']
        }"""
        with open(log_file, 'a') as output_file:
            output_file.write('\ndate: {}\n'.format(record_time))
            output_file.write('  name: {}\n'.format(data['metadata']['name']))
            output_file.write('  min_replicas: {}\n'.format(data['spec']['minReplicas']))
            output_file.write('  max_replicas: {}\n'.format(data['spec']['maxReplicas']))
            output_file.write('  current_replicas: {}\n'.format(data['status']['currentReplicas']))
            output_file.write('  desired_replicas: {}\n'.format(data['status']['desiredReplicas']))
        """hpa_state_data.append(current_state)
        if len(hpa_state_data) > 0:
            with open(log_file, 'a') as output_file:
                output_file.write(str(hpa_state_data))"""
        time.sleep(5)
        
"""     
    output_file.write('\n\date: {}\n'.format(record_time))
    output_file.write('  name: {}\n'.format(data['metadata']['name']))
            output_file.write('  min_replicas: {}\n'.format(data['spec']['minReplicas']))
            output_file.write('  max_replicas: {}\n'.format(data['spec']['maxReplicas']))
            output_file.write('  current_replicas: {}\n'.format(data['status']['currentReplicas']))
            output_file.write('  desired_replicas: {}\n'.format(data['status']['desiredReplicas']))

"""        
   
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


def load_generation_req():
    urls = [k6url]*connections_count
    load = generate_load(urls)

    response_from_server = []
    _elapse_time = []

    req_start_count = 0
    while req_start_count < connections_count:
        response_from_server.append(load[req_start_count].text)
        _elapse_time.append(str(load[req_start_count].elapsed))
        req_start_count += 1
    write_logs(response_from_server, _elapse_time, connections_count)
    pod_node_details()
    time.sleep(180)
    """Implement point 3 here"""



def iteration_fun():
    os.system('kubectl get hpa {} -o json > {}'.format(kube_hpa, tmp_file_1))
    with open(tmp_file_1, 'r') as input_file:
            data = json.load(input_file)
    current_replicas =  data['status']['currentReplicas']
    desired_replicas =  data['spec']['maxReplicas']

    if current_replicas < desired_replicas:
        count = 1
        while count <= iterate_count or current_replicas == desired_replicas:
            print("iteration count")
            load_generation_req()
            #print("I am here!")
            os.system('kubectl get hpa {} -o json > {}'.format(kube_hpa, tmp_file_2))
            with open(tmp_file_2, 'r') as input_file_1:
                data_1 = json.load(input_file_1)
            current_replicas =  data_1['status']['currentReplicas']
            desired_replicas =  data_1['spec']['maxReplicas']
            count += 1


def pod_node_details():
    os.system('kubectl get pods -o json > {}'.format(tmp_file_3))
    record_time = datetime.now().strftime('%y%m%d_%H%M%S')
    with open(tmp_file_3, 'r') as input_file_1:
        data = json.load(input_file_1)
    with open(pod_node_file, 'a') as output_file:
        output_file.write('\ndate: {}\n'.format(record_time))
        for d in data['items']:
            output_file.write('  pod_name: {}\n'.format(d['metadata']['name']))
            output_file.write('  node_name: {}\n'.format(d['spec']['nodeName']))



if __name__ == "__main__":
    _thread.start_new_thread(spinner, ())
    #print('hello')
    load_generation_req()
    """os.system('kubectl get hpa {} -o json > {}'.format(kube_hpa, tmp_file_1))
    with open(tmp_file_1, 'r') as input_file:
            data = json.load(input_file)
    current_replicas =  data['status']['currentReplicas']
    desired_replicas =  data['spec']['maxReplicas']
    print(current_replicas)
    print(desired_replicas)"""
    iteration_fun()
    
    """ File Cleanup """
    os.remove(tmp_file)
    os.remove(tmp_file_1)
    os.remove(tmp_file_2)
    os.remove(tmp_file_3)


        
        


    """urls = [k6url]*connections_count
    load = generate_load()

    response_from_server = []
    _elapse_time = []

    req_start_count = 0
    while req_start_count < connections_count:
        response_from_server.append(load[req_start_count].text)
        _elapse_time.append(str(load[req_start_count].elapsed))
        req_start_count += 1
    write_logs(response_from_server, _elapse_time, connections_count)"""
    """ Files cleanup """