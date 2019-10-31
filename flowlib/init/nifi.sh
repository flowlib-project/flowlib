#!/usr/bin/env bash -e

# Login to ECR
$(aws ecr get-login --region us-east-1 --no-include-email --registry-ids 883886641571)

# Build flow image
docker build . -t b23.io/nifi-dev:latest

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
    - name: nifi
      protocol: TCP
      targetPort: 8080
      port: 8080
    - name: zookeeper
      protocol: TCP
      targetPort: 2181
      port: 2181
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
        image: b23.io/nifi-dev:latest
        imagePullPolicy: Never
        env:
        - name: NIFI_EMBEDDED_ZK_START
          value: "true"
        - name: NIFI_ELECTION_MAX_WAIT
          value: "10 sec"
        - name: NIFI_ELECTION_MAX_CANDIDATES
          value: "1"
        - name: NIFI_CLUSTER_IS_NODE
          value: "true"
        - name: NIFI_CLUSTER_NODE_PROTOCOL_PORT
          value: "11443"
        - name: NIFI_CLUSTER_ADDRESS
          valueFrom:
            fieldRef:
              fieldPath: status.podIP
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
# trap "echo Exit.. Undeploying nifi-dev; \
#  kubectl delete svc nifi-dev; \
#  kubectl delete deployments.apps nifi-dev" KILL TERM HUP INT;

# echo "Waiting for local NiFi deployment..." && sleep 3
# kubectl port-forward svc/nifi-dev 8080:8080
# kubectl port-forward svc/nifi-dev 2181:2181
