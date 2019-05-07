## Getting Started ##

Check with another developer for access to the private ECR repository
and then login to the ECR registry with: `$(aws ecr get-login --no-include-email --region us-east-1)`

Use `./deploy.sh` to run the sample project.
View the deployed flow on `http://127.0.0.1/nifi`

Press ctrl-c to cleanup the deployment and service that were created by `deploy.sh`

Edit `flow.yaml` or its referenced `components/` and then re-deploy to view changes.
