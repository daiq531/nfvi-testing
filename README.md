# nfvi-testing

## testing workflow

1. Open a file and store all data of test workflow in that file (json/yaml) 
- HPA name
- HPA min/max replica
- Deployment Name
- Deployment Replica count

2. Figure out way to monitor the state of HPA(or POD) and write information in log file every 10 secs
3. Immediately send http request to http-client service and write down time in log 
4. Until the request is completed, monitor the HPA/POD state and write info in log file
5. Record http request time completion time in log
6. Stop data collection and read HPA/POD status from logs(or from info stored in vars)
7. Check if PODs count reached to max limit defined in HPA
  - if YES, stop testing
  - if NO, re-iterate through step 3 and stop
