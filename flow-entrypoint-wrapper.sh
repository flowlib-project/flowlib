#!/bin/sh -e
printf "Executing flow-entrypoint-wrapper.sh...\n"
flowlib --flow-yaml /etc/flowlib/flow.yaml > /tmp/flowlib-deploy.log 2>&1 &
exec ${SCRIPTS_DIR}/nifi-entrypoint-wrapper.sh "$@"
