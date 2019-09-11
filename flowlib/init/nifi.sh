#!/usr/bin/env bash -e
pushd $(dirname $0)
dir=$(pwd)

# parse flow.version and flow.name from stdout
echo "Validating $dir/flow.yaml"
flow_info=$(flowlib --validate --flow-yaml ./flow.yaml 2> /dev/null | awk -F: '{print $2}')
flow_name=$(echo $flow_info | awk '{print $1}')
flow_version=$(echo $flow_info | awk '{print $2}')
flow_image="b23.io/$flow_name:$flow_version"

# Login to ECR
$(aws ecr get-login --region us-east-1 --no-include-email --registry-ids 883886641571)

# Build flow image
docker build . -t $flow_image

# Create kubernetes deployment and service
kubectl apply -f - << EOF
apiVersion: v1
kind: Service
metadata:
  name: nifi-dev
  labels:
    app: nifi-dev
spec:
  ports:
    - protocol: TCP
      targetPort: 8080
      port: 8080
  selector:
    app: nifi-dev
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nifi-dev
spec:
  selector:
    matchLabels:
      app: nifi-dev
  template:
    metadata:
      labels:
        app: nifi-dev
    spec:
      containers:
      - name: nifi
        image: $image
        imagePullPolicy: Never
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

# Cleanup on ctrl-c or kill
trap "echo Exit.. Undeploying nifi-dev; \
  kubectl delete svc nifi-dev; \
  kubectl delete deployments.apps nifi-dev; \
  popd > /dev/null" KILL TERM HUP INT;

echo "Waiting for local NiFi deployment..." && sleep 3
kubectl port-forward svc/nifi-dev 8080:8080
