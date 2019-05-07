#!/usr/bin/env bash -e
DIRTY=""
[[ -z $(git status -s) ]] || DIRTY="dirty"

TAG=$(python -c "import os, importlib; \
  print(importlib.import_module('flowlib.version', os.path.join('flowlib', 'version.py')).version)")

if [ "$DIRTY" == "dirty" ]; then
  TAG="latest"
else
  git tag -a v$TAG -m "B23 FlowLib release: $TAG"
  git push origin --tags
fi

# Remove dist/ if it exists
if [ -f ./dist ]; then
  rm -r $dir/dist
fi

# Build FlowLib
rm flowlib/git_version
python setup.py sdist
DIST=$(ls ./dist)

# Upload dist/b23-flowlib-$VERSION.tar.gz

# Login to ECR
$(aws ecr get-login --no-include-email --region us-east-1)

docker build --build-arg FLOWLIB_DIST=$DIST --no-cache $(dirname $0) -t b23-flowlib:$TAG
docker tag b23-flowlib:$TAG 883886641571.dkr.ecr.us-east-1.amazonaws.com/b23-flowlib:$TAG
docker push 883886641571.dkr.ecr.us-east-1.amazonaws.com/b23-flowlib:$TAG
