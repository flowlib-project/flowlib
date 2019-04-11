#!/usr/bin/env bash
mkdir -p /tmp/docker
mkdir -p $(dirname "$0")/zookeeper/{pv1,pv2,pv3}
mkdir -p $(dirname "$0")/nifi/{pv1,pv2,pv3}/{flowfile_repository,database_repository,content_repository,provenance_repository}
(sudo rm -f /tmp/docker/nifi; cd $(dirname "$0")/nifi && sudo ln -s $(pwd) /tmp/docker/nifi)
(sudo rm -f /tmp/docker/zookeeper; cd $(dirname "$0")/zookeeper && sudo ln -s $(pwd) /tmp/docker/zookeeper)
