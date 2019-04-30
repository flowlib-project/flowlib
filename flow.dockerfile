FROM 883886641571.dkr.ecr.us-east-1.amazonaws.com/b23-flowlib:latest
COPY flowlib-components/* /etc/flowlib/components/
COPY ${FLOW_DIR}/* /etc/flowlib/
