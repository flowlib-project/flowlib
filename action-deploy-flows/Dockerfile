FROM openjdk:8

ARG NIFI_VERSION

ENV NIFI_BASE_DIR=/opt/nifi
ENV NIFI_TOOLKIT_HOME ${NIFI_BASE_DIR}/nifi-toolkit-current

ENV BASE_URL=https://archive.apache.org/dist
ENV NIFI_TOOLKIT_BINARY_PATH=/nifi/${NIFI_VERSION}/nifi-toolkit-${NIFI_VERSION}-bin.tar.gz

RUN curl -fSL ${BASE_URL}/${NIFI_TOOLKIT_BINARY_PATH} -o /tmp/nifi-toolkit-${NIFI_VERSION}-bin.tar.gz \
            && echo "$(curl ${BASE_URL}/${NIFI_TOOLKIT_BINARY_PATH}.sha256) */tmp/nifi-toolkit-${NIFI_VERSION}-bin.tar.gz" | shasum -a 256 -c -

RUN apt-get update -y \
    && apt-get install -y python3 pip \
    && apt-get -q clean all \
    && mkdir ${NIFI_BASE_DIR} \
    && tar xzvf /tmp/nifi-toolkit-${NIFI_VERSION}-bin.tar.gz -C ${NIFI_BASE_DIR} \
    && rm /tmp/nifi-*-bin.tar.gz \
    && ln -s ${NIFI_BASE_DIR}/nifi-toolkit-${NIFI_VERSION} ${NIFI_TOOLKIT_HOME}

COPY dist/b23-flowlib-*.tar.gz /opt/flowlib/
RUN pip install /opt/flowlib/b23-flowlib-*.tar.gz

WORKDIR ${NIFI_TOOLKIT_HOME}

#USER root

ADD entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
