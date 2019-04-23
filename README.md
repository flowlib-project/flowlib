# B23 FlowLib #

### Developer Getting Started ###

```bash
virtualenv env --python=python3
source env/bin/activate
pip install -e ./
```

```bash
$ flowlib --help
usage: flowlib [-h] [--flow-yaml [FLOW_YAML]] [--nifi-address NIFI_ADDRESS]
               [--nifi-port NIFI_PORT]

Deploy a NiFi flow from YAML

optional arguments:
  -h, --help            show this help message and exit
  --flow-yaml [FLOW_YAML]
                        YAML file defining a NiFi flow
  --nifi-address NIFI_ADDRESS
                        Address of the NiFi API
  --nifi-port NIFI_PORT
                        HTTP port for the NiFi API
```

### Resources ###

[flowlib/](./flowlib/README.md) - A python module and cli tool for deploying NiFi flows from YAML

[lib/](./lib/README.md) - A library of commonly used FlowLib components

[k8s/](./k8s/README.md) - kustomize resource definitions for creating NiFi deployments in different environments
