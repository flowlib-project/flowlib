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

echo "Don't forget to upload the latest release to github: dist/$DIST"
