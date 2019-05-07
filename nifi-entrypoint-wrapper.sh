#!/bin/sh -e
printf "Executing nifi-entrypoint-wrapper.sh...\n"

# For liveness/readiness probes and so flowlib can deploy to 127.0.0.1:8080/nifi-api
# and kubectl port-forward svc/nifi 8080:8080
printf "\n\n# network interfaces for kubectl proxy #\n" >> ${NIFI_HOME}/conf/nifi.properties
printf "nifi.web.http.network.interface.lo=lo\n" >> ${NIFI_HOME}/conf/nifi.properties
printf "nifi.web.http.network.interface.eth0=eth0\n" >> ${NIFI_HOME}/conf/nifi.properties
printf "Continuing to standard NiFi startup script...\n"
exec ${SCRIPTS_DIR}/start.sh "$@"
