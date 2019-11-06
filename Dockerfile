FROM maven:3.6-jdk-8 AS NAR_BUILDER
WORKDIR /tmp/flowlib.metrics.nifi

# Tell docker to cache maven dependencies
COPY flowlib-metrics/flowlib.metrics.nifi/nifi-flowlib.metrics.nifi-processors/pom.xml nifi-flowlib.metrics.nifi-processors/pom.xml
COPY flowlib-metrics/flowlib.metrics.nifi/pom.xml pom.xml
RUN mvn -f nifi-flowlib.metrics.nifi-processors/pom.xml dependency:go-offline

# Copy src modules and build
COPY flowlib-metrics/flowlib.metrics.nifi/nifi-flowlib.metrics.nifi-processors/src nifi-flowlib.metrics.nifi-processors/src
COPY flowlib-metrics/flowlib.metrics.nifi/nifi-flowlib.metrics.nifi-nar/pom.xml nifi-flowlib.metrics.nifi-nar/pom.xml
RUN mvn clean install

FROM apache/nifi:1.10.0

USER root
ADD nifi-docker/start.sh ${NIFI_BASE_DIR}/scripts/start.sh
RUN chown nifi:nifi ${NIFI_BASE_DIR}/scripts/start.sh && \
    apt-get update && \
    apt-get install -y python3 python3-pip && \
    rm -rf /var/lib/apt/lists/*

USER nifi
COPY --from=NAR_BUILDER /tmp/flowlib.metrics.nifi/nifi-flowlib.metrics.nifi-nar/target/*.nar $NIFI_HOME/lib/.
ENV PATH="/home/nifi/.local/bin:${PATH}"
