## Getting Started ##

Use `./deploy.sh` to run the sample project.

View the deployed flow on `http://127.0.0.1/nifi`

In a new Terminal, view flowlib deployment logs with:

`kubectl exec $(kubectl get pods -o jsonpath='{.items[0].metadata.name}') -- tail -f /tmp/flowlib-deploy.log`

Press ctrl-c to cleanup the deployment and service that were created by `deploy.sh`

Edit `flow.yaml` or its referenced `components/` and then re-run `deploy.sh` to view your changes

You can test a flow with: `flowlib --flow-yaml ./flow.yaml --validate`

Or you can deploy directly to a running NiFi instance with:

`flowlib --flow-yaml ./flow.yaml --nifi-endpoint http://127.0.0.1:8080/nifi-api`
