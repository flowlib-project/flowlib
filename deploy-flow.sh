#!/usr/bin/env bash -e
FLOW="$1"
if [ -z "$FLOW" ]; then
  echo "[Error] missing required positional argument: /path/to/flow.yaml"
  exit 1;
fi
FLOW_NAME=$(basename $(dirname $FLOW))

# Validate the flow.yaml
flowlib  --flow-yaml ${FLOW} --component-dir "$(dirname $0)/flowlib-components" --validate

# TODO: Parse version from flow.yaml
TAG="$2"
if [ -z "$TAG" ]; then
  TAG="latest"
fi

# Login to ECR
$(aws ecr get-login --no-include-email --region us-east-1)

# Create image repo if it doesnt exist
if ! aws ecr describe-repositories | grep repositoryName | grep b23-dataflows/$FLOW_NAME; then
  aws ecr create-repository --repository-name b23-dataflows/$FLOW_NAME
fi

docker build $(dirname $0) \
  -f $(dirname $0)/flow.dockerfile \
  -t b23-dataflows/$FLOW_NAME:$TAG \
  --build-arg FLOW=$FLOW

FLOW_IMAGE="883886641571.dkr.ecr.us-east-1.amazonaws.com/b23-dataflows/$FLOW_NAME:$TAG"
docker tag b23-dataflows/$FLOW_NAME:$TAG $FLOW_IMAGE
docker push $FLOW_IMAGE

kubectl apply -f - << EOF
apiVersion: v1
kind: Service
metadata:
  namespace: b23-data-platform
  name: $FLOW_NAME
  labels:
    app: $FLOW_NAME
spec:
  ports:
    - protocol: TCP
      targetPort: 8080
      port: 8080
  selector:
    app: $FLOW_NAME
---
apiVersion: apps/v1
kind: Deployment
metadata:
  namespace: b23-data-platform
  name: $FLOW_NAME
spec:
  selector:
    matchLabels:
      app: $FLOW_NAME
  template:
    metadata:
      labels:
        app: $FLOW_NAME
    spec:
      imagePullSecrets:
      - name: aws-ecr-registry
      containers:
      - name: flow
        image: $FLOW_IMAGE
        imagePullPolicy: Always
        env:
        - name: NIFI_WEB_HTTP_HOST
          valueFrom:
            fieldRef:
              fieldPath: status.podIP
        readinessProbe:
          exec:
            command:
            - bash
            - "-c"
            - "curl http://127.0.0.1:8080/nifi"
          initialDelaySeconds: 120
          periodSeconds: 15
        livenessProbe:
          tcpSocket:
            port: 8080
          initialDelaySeconds: 120
        ports:
        - name: flow-http
          containerPort: 8080
EOF

trap "echo Exit.. Undeploying $FLOW_NAME; \
  kubectl -n b23-data-platform delete svc $FLOW_NAME; \
  kubectl -n b23-data-platform delete deployments.apps $FLOW_NAME" KILL TERM HUP INT EXIT;

echo "Waiting for $FLOW_NAME deployment..." && sleep 3
kubectl port-forward svc/$FLOW_NAME 8080:8080
