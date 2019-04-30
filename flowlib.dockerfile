FROM python:3.7.2-slim-stretch
COPY . /opt/flowlib
RUN apt-get update && \
  apt-get install -y git && \
  pip install --upgrade pip && \
  pip install gitpython && \
  pip install /opt/flowlib
