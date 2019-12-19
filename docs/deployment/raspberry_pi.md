# Running On A Raspberry Pi

Dragonchain has ARM64 builds of its docker container to support running on ARM
devices such as the raspberry pi.

Although all of the Dragonchain code supports running on ARM, redisearch does
not run on ARM, so any chain with a redisearch will not be able to run on a
raspberry pi.

With that said, verification nodes (L2-5) do not require redisearch and are
deployed without a redisearch by default, so the existing helm chart fully
supports deploying onto a kubernetes cluster running on an ARM machine such as
as raspberry pi.

## Requirements

Currently, because Dragonchain requires kubernetes, and does not yet run on
something lighter weight for a single deployment (such as docker compose), a
kubernetes cluster is required to run Dragonchain.

Running a lightweight kubernetes distribution on a raspberry pi (such as
[k3s](https://k3s.io/) or [microk8s](https://microk8s.io/)) ends up using
around ~500MB of RAM, on top of the OS. This means that before Dragonchain is
deployed, around ~750MB of RAM is used just by linux/kubernetes.

Unfortunately, this means that Dragonchain will currently only run on a
raspberry pi with **2GB or more of total RAM**. Currently the only devices that
support this are the raspberry pi model 4 in either the 2 or 4GB variant.

Also note that you must install a 64 bit OS onto your raspberry pi. Raspbian
_**is not**_ currently a 64 bit operating system, so installing an alternative
such as
[ubuntu's 64bit raspberry pi distribution](https://ubuntu.com/download/raspberry-pi)
is required.

## Installing Dragonchain

All of the previous docs still apply to deploying a dragonchain on a raspberry
pi, with the exception that only L2+ chains are supported.

Additionally, when deploying the helm chart, some cpu resource limits should
be increased in order to compensate for the lower performance of the device's
CPU.

These suggested limits are provided, commented out, at the bottom of the
available `opensource-config.yaml` from the previous deployment docs.

Alternatively, simply add this flag to your `helm upgrade` or `helm install`
command when installing dragonchain:

```sh
--set cacheredis.resources.limits.cpu=1,persistentredis.resources.limits.cpu=1,webserver.resources.limits.cpu=1,transactionProcessor.resources.limits.cpu=1
```

Other than that change, no other changes should be required in order to have
Dragonchain running on a Raspberry pi.
