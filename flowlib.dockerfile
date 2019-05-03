FROM apache/nifi:1.8.0

USER root
RUN apt-get update && \
    apt-get install -y git && \
    apt-get install -y python3 && \
    apt-get install -y python3-pip

ENV SCRIPTS_DIR=/opt/nifi/scripts
ADD nifi-entrypoint-wrapper.sh ${SCRIPTS_DIR}/nifi-entrypoint-wrapper.sh
RUN chown nifi:nifi ${SCRIPTS_DIR}/nifi-entrypoint-wrapper.sh && \
    chmod 750 ${SCRIPTS_DIR}/nifi-entrypoint-wrapper.sh && \
    pip3 install gitpython

USER nifi
COPY ./setup.py /opt/flowlib/setup.py
COPY ./flowlib/* /opt/flowlib/flowlib/
RUN pip3 install --user /opt/flowlib/
ENV PATH="/home/nifi/.local/bin:${PATH}"

ENTRYPOINT ["../scripts/nifi-entrypoint-wrapper.sh"]
