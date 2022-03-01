#!/bin/bash

client_svc="http-client"
client_pod="http-client"

svc_node_port=$(oc describe service $client_svc|awk '/^NodePort/{print $3}'|cut -d'/' -f1)
pod_host=$(oc get pods -o wide|awk '/^http-client/{print $7}')


echo "Host: $pod_host"
echo "Port: $svc_node_port"

curl http://$pod_host:$svc_node_port/



