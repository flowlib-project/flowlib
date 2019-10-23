#!/usr/bin/env bash -e
dir="$(dirname $0)"

# if no arg, increment patch version
if [ -z "$1" ]; then
  semver=$(python ${dir}/setup.py --version | sed -n -E 's/^([0-9]+\.[0-9]+\.[0-9]+).*$/\1/p')
  major=$(echo $semver | sed -n -E 's/^([0-9]+)\.([0-9]+)\.([0-9]+).*/\1/p')
  minor=$(echo $semver | sed -n -E 's/^([0-9]+)\.([0-9]+)\.([0-9]+).*/\2/p')
  patch=$(echo $semver | sed -n -E 's/^([0-9]+)\.([0-9]+)\.([0-9]+).*/\3/p')
  REL="${major}.${minor}.$((patch+1))"
else
  REL="${1}"
fi

### TODO: run tests ###

# Tag release
git tag -a v${REL} -m "B23 FlowLib: $(date)"

# Remove dist/ if it exists
if [ -d $dir/dist ]; then
  rm -r $dir/dist
fi

# Build FlowLib
python ${dir}/setup.py sdist
DIST="$(ls $dir/dist)"

echo ""
echo "Don't forget to upload dist/${DIST} to github: https://github.com/B23admin/b23-flowlib/releases/edit/v${REL}"
