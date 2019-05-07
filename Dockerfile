FROM apache/nifi:1.8.0
ARG FLOWLIB_DIST=${FLOWLIB_DIST}

USER root
RUN apt-get update && \
    apt-get install -y git && \
    apt-get install -y python3 && \
    apt-get install -y python3-pip

ENV SCRIPTS_DIR=/opt/nifi/scripts
ADD entrypoint-wrapper.sh ${SCRIPTS_DIR}/entrypoint-wrapper.sh
RUN chown nifi:nifi ${SCRIPTS_DIR}/entrypoint-wrapper.sh && \
    chmod 750 ${SCRIPTS_DIR}/entrypoint-wrapper.sh && \
    pip3 install gitpython

USER nifi

# todo: ADD from https://github.com/releases
ADD dist/${FLOWLIB_DIST} /opt/flowlib
RUN pip3 install --user /opt/flowlib/
ENV PATH="/home/nifi/.local/bin:${PATH}"

USER root
RUN pip3 uninstall -y gitpython && \
    rm -rf /var/lib/apt/lists/*
USER nifi

ENTRYPOINT ["../scripts/entrypoint-wrapper.sh"]

ONBUILD COPY components/ /etc/flowlib/components/
ONBUILD COPY flow.yaml /etc/flowlib/flow.yaml
