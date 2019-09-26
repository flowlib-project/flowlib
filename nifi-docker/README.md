This image builds off of the base Nifi image [here](https://github.com/apache/nifi/tree/rel/nifi-1.9.2/nifi-docker/dockerhub) but overwrites the entrypoint script `sh/start.sh` with the one in this repo.

- Adds lo and eth0 network interfaces in nifi.properties for `kubectl port-forward` compatibility
- Allows setting `nifi.flow.configuration.file` via the `${FLOW_XML_PATH}` env var so that it can be set at runtime

# dev

```bash
docker build . -t b23.io/nifi-base:latest
```


# prod

```bash
NIFI_VER=1.9.2
$(aws ecr get-login --region us-east-1 --no-include-email --registry-ids 883886641571)
docker build . -t b23.io/nifi-base:$NIFI_VER
docker tag b23.io/nifi-base:$NIFI_VER 883886641571.dkr.ecr.us-east-1.amazonaws.com/nifi-base:$NIFI_VER
docker push 883886641571.dkr.ecr.us-east-1.amazonaws.com/nifi-base:$NIFI_VER
```
