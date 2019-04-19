# NiFi Kubernetes deployment options #

### Local ###

```bash
$ kubectl apply -k ./k8s/local
```

The NiFi UI is available at: `http://localhost:8080/nifi/`


### Cloud ###

```bash
$ kubectl apply -k ./k8s/cloud/aws
# or
$ kubectl apply -k ./k8s/cloud/gcp
```


## Todo ##

- Fix cloud storage classes
- [Fix cloud node affinity patching](https://github.com/kubernetes-sigs/kustomize/issues/937)
