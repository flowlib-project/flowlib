#!/usr/bin/env bash
datadir=$(dirname "$0")
mkdir -p /tmp/docker
rm -rf $datadir/zookeeper && mkdir -p $datadir/zookeeper/{pv1,pv2,pv3}
rm -rf $datadir/nifi && mkdir -p $datadir/nifi/{pv1,pv2,pv3}/{flowfile_repository,database_repository,content_repository,provenance_repository}
(sudo rm -f /tmp/docker/nifi; cd $datadir/nifi && sudo ln -s $(pwd) /tmp/docker/nifi)
(sudo rm -f /tmp/docker/zookeeper; cd $datadir/zookeeper && sudo ln -s $(pwd) /tmp/docker/zookeeper)
