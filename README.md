# B23 FlowLib #

### FlowLib User Getting Started ###

```shell
# Download the latest release archive from: https://github.com/B23admin/b23-flowlib/releases/latest
pip install b23-flowlib-$VERSION.tar.gz
flowlib --scaffold=./new-project-dir
```

View the docs in `./new-project-dir/README.md` to get started


### FlowLib Developer Getting Started ###

```shell
git clone git@github.com:B23admin/b23-flowlib.git && cd b23-flowlib
virtualenv env --python=$(which python3)
source env/bin/activate
pip install requirements-dev.txt
pip install -e ./
```

### Release ###

```shell
RELEASE=0.1.0
git tag -a v$RELEASE -m "B23 FlowLib release: v$RELEASE"
./release.sh
```

### Resources ###

[flowlib/](./flowlib/README.md) - A python module and cli tool for deploying NiFi flows from YAML

[k8s/](./k8s/README.md) - kustomize resource definitions for bootstrapping local clusters and integrating with BDP
