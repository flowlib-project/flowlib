# nifi yaml #

### Local ###

First, run `./data/local-setup.sh`, then `kubectl apply -k ./k8s/local`

Nifi UI should be available at: `http://localhost:8080/nifi/`

### Cloud ###

Run either `kubectl apply -k ./k8s/cloud/aws` or `kubectl apply -k ./k8s/cloud/gcp`


## Todo ##

- Fix cloud storage classes
- [Fix cloud node affinity patching](https://github.com/kubernetes-sigs/kustomize/issues/937)
- Fix liveness/readiness probes
