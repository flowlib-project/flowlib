FROM 883886641571.dkr.ecr.us-east-1.amazonaws.com/b23-flowlib:latest
ARG FLOW
COPY flowlib-components/ /etc/flowlib/components/
COPY ${FLOW} /etc/flowlib/flow.yaml

USER root

ADD flow-entrypoint-wrapper.sh ${SCRIPTS_DIR}/flow-entrypoint-wrapper.sh
RUN chown nifi:nifi ${SCRIPTS_DIR}/flow-entrypoint-wrapper.sh
RUN chmod 750 ${SCRIPTS_DIR}/flow-entrypoint-wrapper.sh

USER nifi
ENTRYPOINT ["../scripts/flow-entrypoint-wrapper.sh"]
