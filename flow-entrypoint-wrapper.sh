#!/bin/sh -e
printf "Executing Flow entrypoint-wrapper.sh...\n"
flowlib --flow-yaml /etc/flowlib/flow.yaml > /tmp/flowlib-deploy.log &
exec ${SCRIPTS_DIR}/nifi-entrypoint-wrapper.sh "$@"
