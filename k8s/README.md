# NiFi Kubernetes deployment options #

### Local ###

```bash
# Bootstrap cluster
$ kubectl apply -k ./k8s/app/bootstrap

# Launch nifi
$ kubectl apply -k ./k8s/local
```

The NiFi UI is available at: `http://localhost:8080/nifi/`

To use NiFi and FlowLib through BDP, add the local cluster through the BDP UI:

```bash
# Get Cluster Endpoint.
# Note that if the endpoint is localhost you'll need to change it to 127.0.0.1, otherwise cert verification fails
$ kubectl config view --minify --raw -o jsonpath='{.clusters[0].cluster.server}'

# Get Service Account Token data and CA Cert data
$ kubectl -o json -n b23-data-platform get secrets | jq '.items[] | select(.metadata.name | startswith("b23-")) | {token: .data.token | @base64d, ca_cert: .data."ca.crt" }'
```

### Cloud ###

```bash
$ kubectl apply -k ./k8s/cloud/aws
# or
$ kubectl apply -k ./k8s/cloud/gcp
```


## Todo ##

- Fix cloud storage classes
- [Fix cloud node affinity patching](https://github.com/kubernetes-sigs/kustomize/issues/937)
