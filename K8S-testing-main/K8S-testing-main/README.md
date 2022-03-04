# HPA Testing

### Flask Application to run in pod
`flask` dir has `Dockerfile` and other flask files those can be used to generate custom image. The image can be used for both functionalities (server/client). Check `.py` files for more information.

- Pushed `quasarstack/flask` image on docker hub. This image is available to create container directly without building custom image.

### Python Script
- `scripts/hpa-test.py` to send GET call to httpclient app running in K8S cluster
