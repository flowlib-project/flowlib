#!/usr/bin/env bash -e
FLOW="$1"
if [ -z "$FLOW" ]; then
  echo "[Error] missing required positional argument: /path/to/flow.yaml"
  exit 1;
fi
FLOW_NAME=$(basename $(dirname $FLOW))

# Validate the flow.yaml
flowlib  --flow-yaml ${FLOW} --component-dir "$(dirname $0)/flowlib-components" --validate

# TODO: Parse version from flow.yaml
TAG="$2"
if [ -z "$TAG" ]; then
  TAG="latest"
fi

# Login to ECR
$(aws ecr get-login --no-include-email --region us-east-1)

# Create image repo if it doesnt exist
if ! aws ecr describe-repositories | grep repositoryName | grep b23-dataflows/$FLOW_NAME; then
  aws ecr create-repository --repository-name b23-dataflows/$FLOW_NAME
fi

docker build $(dirname $0) \
  -f $(dirname $0)/flow.dockerfile \
  -t b23-dataflows/$FLOW_NAME:$TAG \
  --build-arg FLOW=$FLOW

docker tag b23-dataflows/$FLOW_NAME:$TAG 883886641571.dkr.ecr.us-east-1.amazonaws.com/b23-dataflows/$FLOW_NAME:$TAG
docker push 883886641571.dkr.ecr.us-east-1.amazonaws.com/b23-dataflows/$FLOW_NAME:$TAG
