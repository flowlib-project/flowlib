FROM python:3.7.2-slim-stretch
COPY ./setup.py /opt/flowlib/setup.py
COPY ./flowlib/* /opt/flowlib/flowlib/
RUN apt-get update && \
  apt-get install -y git && \
  pip install --upgrade pip && \
  pip install gitpython && \
  pip install /opt/flowlib
