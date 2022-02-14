#!/usr/bin/env bash
set -e

release_version=${1}
nifi_release_version=${2:-1.14.0}

regex="[0-9]+.[0-9]+.[0-9]+"

if ! [ -z "$release_version" ]; then
    if ! [[ $release_version =~ $regex ]]; then
        echo "Obtaining latest tagged version: $version"
        rm dist/*
        gh release download v1.1.0 --dir dist/ --archive=tar.gz
    fi
else
    echo "Building local tar"
    rm dist/*
    python3 setup.py sdist
fi

docker build . -t b23.io/flowlib-base:latest --build-arg NIFI_VERSION=$nifi_release_version
