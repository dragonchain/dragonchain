# Contract Job Processor

Relevant To: Level 1 chains with smart contracts

## Overview

The contract job processor is responsible for launching the contract builder
in its kubernetes cluster when necessary.

### Entrypoint

In order to run the job processor, `sh entrypoints/job_processor.sh` should be
used as the command of the built docker container.

## Architecture

The contract job processor blocks on the `mq:contract-task` redis queue. On
receiving an item, it triggers a kubernetes job in the `dragonchain` namespace
to build a smart contract.

This logic is separated into its own container because it requires permissions
to create kubernetes jobs. Using a different pod allows permissions to be
isolated on a per-pod basis when deployed.

Because of this, the job processor needs to be launched with a service account
which has permissions to create, get, and delete jobs. An example RBAC for this
role follows:

```yaml
kind: Role
apiVersion: rbac.authorization.k8s.io/v1
metadata:
  namespace: dragonchain
  name: <desired_role_name>
rules:
  - apiGroups: ["batch"]
    resources: ["jobs", "jobs/status"]
    verbs: ["create", "get", "delete"]
```

Bind this role to a service account and automount its token when deploying the
contract job processor microservice. If the permissions are not correct, the
job processor will not be able to run.
