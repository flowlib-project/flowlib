## Getting Started ##

Use `./nifi.sh` to start a local nifi instance on `http://127.0.0.1/nifi`.

Edit `flow.yaml` or its referenced `components/`

You can test a flow with: `flowlib --flow-yaml ./flow.yaml --validate`

In a new Terminal, deploy to the running NiFi instance with:

`flowlib --force --flow-yaml ./flow.yaml`
