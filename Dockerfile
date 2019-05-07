FROM apache/nifi:1.8.0
ARG FLOWLIB_DIST=${FLOWLIB_DIST}

USER root
RUN apt-get update && \
    apt-get install -y git && \
    apt-get install -y python3 && \
    apt-get install -y python3-pip

ENV SCRIPTS_DIR=/opt/nifi/scripts
COPY entrypoint-wrapper.sh ${SCRIPTS_DIR}/entrypoint-wrapper.sh
COPY dist/${FLOWLIB_DIST} /tmp/${FLOWLIB_DIST}
RUN chown nifi:nifi /tmp/${FLOWLIB_DIST} && \
    chown nifi:nifi ${SCRIPTS_DIR}/entrypoint-wrapper.sh && \
    chmod 750 ${SCRIPTS_DIR}/entrypoint-wrapper.sh && \
    rm -rf /var/lib/apt/lists/*

USER nifi
RUN pip3 install --user /tmp/${FLOWLIB_DIST} && \
    rm /tmp/${FLOWLIB_DIST}

ENV PATH="/home/nifi/.local/bin:${PATH}"
ENTRYPOINT ["../scripts/entrypoint-wrapper.sh"]

ONBUILD COPY components/ /etc/flowlib/components/
ONBUILD COPY flow.yaml /etc/flowlib/flow.yaml
