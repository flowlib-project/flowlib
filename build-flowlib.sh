#!/usr/bin/env bash -e

# TODO: Get tag from git tag else tag as latest
#DIRTY=""
#[[ -z $(git status -s) ]] || DIRTY="dirty"

TAG="$1"
if [ -z "$TAG" ]; then
  TAG="latest"
fi

# Login to ECR
$(aws ecr get-login --no-include-email --region us-east-1)

docker build --no-cache $(dirname $0) -f $(dirname $0)/flowlib.dockerfile -t b23-flowlib:$TAG
docker tag b23-flowlib:$TAG 883886641571.dkr.ecr.us-east-1.amazonaws.com/b23-flowlib:$TAG
docker push 883886641571.dkr.ecr.us-east-1.amazonaws.com/b23-flowlib:$TAG
