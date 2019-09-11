FROM apache/nifi:1.9.2

USER root
ADD start.sh ${NIFI_BASE_DIR}/scripts/start.sh
RUN chown nifi:nifi ${NIFI_BASE_DIR}/scripts/start.sh && \
    apt-get update && \
    apt-get install -y python3 python3-pip && \
    rm -rf /var/lib/apt/lists/*

USER nifi
ENV PATH="/home/nifi/.local/bin:${PATH}"
