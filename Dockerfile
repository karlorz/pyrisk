FROM python:3.11-slim

WORKDIR /pyrisk-app

COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade -r requirements.txt

COPY ./instance ./instance
COPY ./riskch ./riskch

RUN flask --app riskch init-db

EXPOSE 8001
CMD [ "flask","--app","riskch","run","--host","0.0.0.0","--port","8001"]