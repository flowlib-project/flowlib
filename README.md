# B23 FlowLib #

### Developer Getting Started ###

```bash
virtualenv env --python=$(which python3)
source env/bin/activate
pip install -e ./
```


### Resources ###

[flowlib/](./flowlib/README.md) - A python module and cli tool for deploying NiFi flows from YAML

[lib/](./lib/README.md) - A library of commonly used FlowLib components

[k8s/](./k8s/README.md) - kustomize resource definitions for creating NiFi deployments in different environments
