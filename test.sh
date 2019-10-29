#!/usr/bin/env bash
set -exuo pipefail

REL="${REL-latest}"
trap "{ docker ps -qaf Name=flowlib-${REL}-integration-test | xargs docker rm -f; }" EXIT

# start nifi container
docker run -d --name flowlib-${REL}-integration-test \
  --env NIFI_CLUSTER_NODE_PROTOCOL_PORT="11443" \
  --env NIFI_EMBEDDED_ZK_START="true" \
  --env NIFI_ELECTION_MAX_WAIT="10 sec" \
  --env NIFI_ELECTION_MAX_CANDIDATES="1" \
  --env NIFI_CLUSTER_IS_NODE="true" \
  -p 8080:8080 -p 2181:2181 \
  b23.io/nifi-dev:latest

# run unit tests while we wait for it to start
python -m unittest discover

# wait for nifi rest api to start
for i in $(seq 1 10) :; do
    if docker exec flowlib-${REL}-integration-test bash -c "ss -ntl | grep 8080"; then
        break
    fi
    sleep 10
done

# run integration tests
python ./tests/itest.py

# stop nifi container
docker stop flowlib-${REL}-integration-test
