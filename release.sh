#!/usr/bin/env bash -e
dir="$(dirname $0)"

TAG=$(python ./setup.py --version)
if echo $TAG | grep 'dev'; then
  TAG="latest"
else
  git push origin --tags
fi

# Remove dist/ if it exists
if [ -d $dir/dist ]; then
  rm -r $dir/dist
fi

# Build FlowLib
python setup.py sdist
DIST=$(ls $dir/dist)

# Login to ECR
$(aws ecr get-login --region us-east-1 --no-include-email --registry-ids 883886641571)

docker build $dir --build-arg FLOWLIB_DIST=$DIST --no-cache --tag b23-flowlib:$TAG
docker tag b23-flowlib:$TAG 883886641571.dkr.ecr.us-east-1.amazonaws.com/b23-flowlib:$TAG
docker push 883886641571.dkr.ecr.us-east-1.amazonaws.com/b23-flowlib:$TAG

echo "Done forget to upload the latest release to github: dist/$DIST"
