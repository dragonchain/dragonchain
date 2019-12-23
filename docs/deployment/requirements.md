# Deployment Requirements

**Please Note**: The Dragonchain deployment process, as well as these docs
are still undergoing changes. We expect Dragonchain to be easier to deploy in
the future for smaller installations, as well as more possible options to
deploy (i.e. docker compose) that don't require a full kubernetes installation.

## Kubernetes Cluster

The dragonchain platform runs exclusively on kubernetes. As such,
a kubernetes cluster is a requirement. The easiest way to accomplish
this locally is to use
[minikube](https://kubernetes.io/docs/setup/learning-environment/minikube/).

Setting up a kubernetes cluster is outside of the scope of this documentation.
However there are some things that you should keep in mind when setting up your
cluster with the intent to run dragonchain(s).

### Requirements

- In order to have persistent storage support, a kubernetes persistent volume
  type must be available with access mode `ReadWriteOnce`. This storage must be
  able to move between nodes if the cluster consists of multiple nodes.
  See the relevant [kubernetes docs](https://kubernetes.io/docs/concepts/storage/persistent-volumes/#access-modes)
  for more information on persistent volumes and access modes.

- [Helm](https://helm.sh/) should be installed on the kubernetes cluster, as
  it is used to manage dragonchain deployments.

- Access into the cluster from the greater internet is required for
  participation in Dragon Net. Ensure that if your cluster is behind a NAT
  layer, the relevant ports to your running chain(s) are forwarded
  appropriately.

- ~600MB of RAM is required for L2+ chains to run (~900MB if redisearch is
  enabled), and ~1.25GB of RAM is required for L1 chains (or a bit more if
  openfaas/docker registry is running on the same machine). This means that the
  kubernetes node running the chain (or the VM in the case of minikube) should
  have at least ~1.5-2GB of RAM total for an L2+ chain, or ~3GB for an L1 (with
  openfaas/docker also running). This is because there is also overhead with
  linux and kubernetes itself.

### Recommended

- It is strongly encouraged to have a TLS certificate so that your chain can
  have TLS (HTTPS) support. Without this, your chain may be vulnerable to
  attacks. Running without a valid TLS certificate should be for non-production
  use only, and TLS _may_ be enforced by Dragon Net in the future. You can
  obtain a free TLS certificate for a domain you own
  [from letsencrypt](https://letsencrypt.org/).

- It is _HIGHLY_ recommended to have RBAC enabled on the kubernetes cluster.
  See the relevant [kubernetes docs](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)
  for more info.

- It is also strongly advised to have a networking plugin capable of handling
  [NetworkPolicies](https://kubernetes.io/docs/concepts/services-networking/network-policies/).
  We recommend
  [calico](https://docs.projectcalico.org/v3.8/getting-started/kubernetes/installation/)
  by default for most use-cases, although it's not the only possible solution.

- Encryption at rest for kubernetes secrets is strongly advised. Without this,
  private keys will be stored unencrypted. See the relevant
  [kubernetes docs](https://kubernetes.io/docs/tasks/administer-cluster/encrypt-data/)
  for more info.

## OpenFaaS

An [OpenFaaS](https://www.openfaas.com/) deployment is required for L1 chains
to be able to create and run smart contracts as containers. The deployment can
be configured to your specifications as long as the api server is exposed.

Since a kubernetes cluster already exists, it may be easiest to deploy
the [kuberenetes version](https://github.com/openfaas/faas-netes) of OpenFaaS.
However, as many actions on OpenFaaS are unauthenticated, proper network
segregation may be necessary.

## Docker Registry

A private docker registry is required to push and pull smart contract images.

Using the official
[docker registry](https://github.com/helm/charts/tree/master/stable/docker-registry)
helm chart is a quick and (relatively) simple way to get a working registry.
Make sure that it is exposed to both the OpenFaaS deployment and deployed
chain(s). We recommend not exposing the registry to the internet without
authorization.

Keep in mind the official docker registry is not the only solution. Any
docker registry will work if it is accessible to OpenFaaS and the chain(s).

## Dragon Net

It is recommended to run with Dragon Net support for networking features
(specifically being able to send/receive verifications) to work properly.

See the [next section](/deployment/dragonnet) for more details.
