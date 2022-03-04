# HPA Testing + CloudSure

### Prerequisite
- Following apps must be running on K8S
    1. HTTP Server App(to generate CPU/Memory workload)
        - Must be accessible using ClusterIP service to other services in cluster
     
    2. HTTP Client App(https://k6.io/docs/using-k6/metrics/) to send GET call to server app
        - Should be accessible from CloudSure and accept HTTP GET request

- Python Script to send GET request to HTTP Client App
  - Script must have capability to store historical data to better analysis

- Helm Charts to deploy Server/Client Apps on demand

### Test cases
#### Test case 1:
- Configuration:
  - HTTP Server App:
    - cpu: 100m
    - memory: 500Mi

  - Python Script param:
    - No. of connections: 10
    - Parallel: yes
    - sleep(in secs): 0

- Execution:
  1. CloudSure python script will initiate the traffic to client App
  2. Monitor HPA state


#### Test case 2:
- Configuration:
  - HTTP Server App:
    - cpu: 100m
    - memory: 500Mi

  - Python Script param:
    - No. of connections: 10
    - Parallel: no
    - sleep(in secs): 2

- Execution:
  1. CloudSure python script will initiate the traffic to client App
  2. Monitor HPA state

