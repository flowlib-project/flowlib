FROM apache/nifi:1.8.0

USER root
RUN apt-get update && \
    apt-get install -y git && \
    apt-get install -y python3 && \
    apt-get install -y python3-pip

COPY ./setup.py /opt/flowlib/setup.py
COPY ./flowlib/* /opt/flowlib/flowlib/
RUN pip3 install gitpython && \
    pip3 install /opt/flowlib

ENV SCRIPTS_DIR=/opt/nifi/scripts
ADD nifi-entrypoint-wrapper.sh ${SCRIPTS_DIR}/nifi-entrypoint-wrapper.sh
RUN chown nifi:nifi ${SCRIPTS_DIR}/nifi-entrypoint-wrapper.sh
RUN chmod 750 ${SCRIPTS_DIR}/nifi-entrypoint-wrapper.sh

USER nifi
ENTRYPOINT ["../scripts/nifi-entrypoint-wrapper.sh"]
