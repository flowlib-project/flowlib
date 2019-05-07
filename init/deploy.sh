#!/usr/bin/env bash -e
pushd $(dirname $0)
dir=$(pwd)

# parse flow.version and flow.name from stdout
echo "Validating $dir/flow.yaml"
flow_info=$(flowlib --validate --flow-yaml ./flow.yaml 2> /dev/null| awk -F: '{print $2}')
flow_name=$(echo $flow_info | awk '{print $1}')
flow_version=$(echo $flow_info | awk '{print $2}')
flow_image="b23-dataflows/$flow_name:$flow_version"

docker build . -t $flow_image

kubectl apply -f - << EOF
apiVersion: v1
kind: Service
metadata:
  name: $flow_name
  labels:
    app: $flow_name
spec:
  ports:
    - protocol: TCP
      targetPort: 8080
      port: 8080
  selector:
    app: $flow_name
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: $flow_name
spec:
  selector:
    matchLabels:
      app: $flow_name
  template:
    metadata:
      labels:
        app: $flow_name
    spec:
      containers:
      - name: flow
        image: $flow_image
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

trap "echo Exit.. Undeploying $flow_name; \
  kubectl -n b23-data-platform delete svc $flow_name; \
  kubectl -n b23-data-platform delete deployments.apps $flow_name; \
  popd" KILL TERM HUP INT EXIT;

echo "Waiting for $flow_name deployment..." && sleep 3
kubectl port-forward svc/$flow_name 8080:8080