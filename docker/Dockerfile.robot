FROM python:3.13-slim

WORKDIR /app

COPY /src /app

RUN pip install --upgrade pip
RUN pip install grpcio==1.71.0rc2 grpcio-tools==1.71.0rc2
RUN pip install paho-mqtt

ENV PYTHONPATH=/app

CMD ["python", "robots/robot.py"]
