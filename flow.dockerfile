FROM 883886641571.dkr.ecr.us-east-1.amazonaws.com/b23-flowlib:latest
ARG FLOW
COPY flowlib-components/ /etc/flowlib/components/
COPY ${FLOW} /etc/flowlib/flow.yaml
ENTRYPOINT [ "flowlib", "--flow-yaml /etc/flowlib/flow.yaml" ]
