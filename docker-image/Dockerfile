FROM python:3.8-slim-buster
RUN mkdir /data
COPY app.py requirements.txt cpuload.py httpclient.py /data/
WORKDIR /data
RUN pip install -r requirements.txt && rm -rf requirements.txt
ENV FLASK_APP=app.py
ENV FLASK_ENV=development
EXPOSE 8080
CMD flask run --host 0.0.0.0 --port 8080