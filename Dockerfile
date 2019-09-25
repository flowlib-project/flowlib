FROM maven:3.6-jdk-8 AS NAR_BUILDER
COPY flowlib-metrics/flowlib.metrics.nifi /tmp/flowlib.metrics.nifi
WORKDIR /tmp/flowlib.metrics.nifi
RUN mvn clean install

FROM apache/nifi:1.9.2

COPY --from=NAR_BUILDER /tmp/flowlib.metrics.nifi/nifi-flowlib.metrics.nifi-nar/target/*.nar $NIFI_HOME/lib/.

USER root
ADD nifi-docker/start.sh ${NIFI_BASE_DIR}/scripts/start.sh
RUN chown nifi:nifi ${NIFI_BASE_DIR}/scripts/start.sh && \
    apt-get update && \
    apt-get install -y python3 python3-pip && \
    rm -rf /var/lib/apt/lists/*

USER nifi
ENV PATH="/home/nifi/.local/bin:${PATH}"
