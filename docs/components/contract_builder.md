# Contract Builder

Relevant To: Level 1 chains with smart contracts

## Overview

The contract builder's responsibility is to pull a customer's smart contract,
make it compatible with OpenFaaS, and deploy the new container to OpenFaaS as
a smart contract.

The contract builder creates, updates, and deletes contracts from OpenFaaS.

### Entrypoint

In order to run the contract builder, `sh entrypoints/contract_job.sh` should
be used as the command of the built docker container.

## Architecture

The contract builder is an ephemeral container (only runs when needed) that has
its actions defined by its `EVENT` environment variable. On boot, it loads this
variable as json into a model which can perform three types of actions:

- Create a new smart contract
- Update an existing smart contract
- Delete an existing smart contract

In order to build docker containers, the contract builder needs access to the
docker daemon. Exposing this permission is potentially dangerous, so it is
separated into its own ephemeral pod on kubernetes.

With the introduction of a userspace container building tool such as
[img](https://github.com/genuinetools/img), this container would not need
elevated permissions and its functionality could be combined with the Contract
Job Processor.

In order to make a customer's smart contract container compatible with
OpenFaaS, it uses a templated Dockerfile which copies in the OpenFaaS
fwatchdog and clears existing entrypoints before setting the user/group for
the container to 1000:1000.

## Flow

The contract builder loads the `EVENT` environment variable into memory as
json, using this to initialize a ContractJob.

This ContractJob then runs and determines which
[CRUD](https://en.wikipedia.org/wiki/Create,_read,_update_and_delete) operation
to perform.

If creating, the microservice builds the contract image and pushes to the
private docker repository accessible to OpenFaaS. It sets the relevant
environment variables, generates new api keys for the smart contract, deploys
necessary secrets to OpenFaaS, and then deploys the function itself to
OpenFaaS.

After this, the microservice schedules recurring execution with the scheduler
if necessary and ledgers a transaction to the Dragonchain with information
about the deployed smart contract.

If updating, the microservice performs the same steps as creating, except only
as necessary. For example, if the update does not contain a new image, it will
not re-build the smart contract.

If deleting, the microservice unschedules the recurring contract invocations if
necessary, then deletes related OpenFaaS secrets and functions, removes the
built contract from the private repository, and clears its data (both heap and
metadata). Finally, the contract builder will ledger the deletion similar to
create and update.
