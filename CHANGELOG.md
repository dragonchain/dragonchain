# Changelog

## 4.0.1

- **Bugs:**
  - Fix a bug where the smart contract list and actual underlying data can become out of sync and crash the contract invoker
- **Packaging:**
  - Adjust RAM usage of scheduler pod for L1s
  - Update Redis to 5.0.6 in the helm deployment
  - Remove unnecessarily configurable options from opensource-config.yaml

## 4.0.0

This update introduces a breaking change required by the switch from
ElasticSearch to redisearch. These changes primarily exist with custom
indexing, and how querying is preformed. Please read the
[relevant docs page](https://dragonchain-core-docs.dragonchain.com/latest/deployment/migrating_v4.html)
for more details on upgrading to v4.

- **Feature:**
  - Add new endpoint `GET /v1/contract/logs/<contract_id>` for getting logs of smart contracts
  - Remove elasticsearch integrations and replace with redisearch
  - Refactor all query endpoints, including changing query inputs (Breaking Change)
  - Changed route for `GET /v1/contract` from a query to a list (Breaking Change)
  - Add support to disable schedule when updating a smart contract
- **Documentation:**
  - Update documentation for redisearch
  - Add new page for migration considerations when upgrading from v3 to v4
  - Add RAM usage requirements
  - Add info about bug/security/project bounty programs
- **Development:**
  - Add logs when getting storage errors
  - Resolve all bandit errors and turn up bandit verbosity
  - Move/extract entire helm chart for better control
- **Packaging:**
  - Update helm chart version, adding redisearch while removing elasticsearch
  - Remove service links from mounting on pods in the helm chart
  - Expose redis and redisearch image locations in opensource-config.yaml
  - Add redisearch and remove elasticsearch from requirements.txt
  - Update boto3, bit, and aiohttp packages
  - Update fwatchdog to 0.18.0 for OpenFaaS smart contracts
- **CICD:**
  - Fixed an issue where the CICD wouldn't properly render changelog or contributing pages
  - Make helm chart be packaged on demand when creating docs
- **Bugs:**
  - Fixed an issue where transaction types whose contracts no longer exist couldn't be deleted
  - Fixed a bug with ethereum classic and ethereum classic testnet interchains which caused transactions to be signed improperly
  - Fixed a bug which caused built smart contract images to not be deleted from the image repository when deleting a smart contract

## 3.5.0

- **Feature:**
  - Switch to using files for reading secrets for dynamic secret update support
  - Use new schema for NETWORK (for L5 registration and blocks). Will now look like "{blockchain} {extra_data}"
    i.e. "bitcoin testnet3" or "ethereum network_id 2" rather than a pre-set list of enums as before.
    (This allows for things such as custom/private ethereum networks, etc)
  - Add support for creating/saving various interchain networks, including custom interchain nodes, keys, etc
    - Note this also means that a chain can have multiple addresses for the same type of network now (i.e. many ETH addresses)
  - Add routes for refactored interchain support:
    - `POST /v1/interchains/bitcoin` Create a bitcoin network for the dragonchain to use
    - `POST /v1/interchains/ethereum` Create an ethereum network for the dragonchain to use
    - `PATCH /v1/interchains/bitcoin/<id>` Update an already existing bitcoin network of dragonchain
    - `PATCH /v1/interchains/ethereum/<id>` Update an already existing ethereum network of dragonchain
    - `POST /v1/interchains/bitcoin/<id>/transaction` Create a bitcoin transaction using one of the chain's networks
    - `POST /v1/interchains/ethereum/<id>/transaction` Create a ethereum transaction using one of the chain's networks
    - `GET /v1/interchains/<blockchain>` Get a list of all registered Dragonchain interchains
    - `GET /v1/interchains/<blockchain>/<id>` Get a particular interchain network from the chain
    - `DELETE /v1/interchains/<blockchain>/<id>` Delete a particular interchain network from the chain
    - `POST /v1/interchains/default` (L5 only) Set a default network for level 5 chains to use
    - `GET /v1/interchains/default` (L5 only) Get the default network set on a level 5 chain
  - Move the following routes legacy support only (they will work for chains upgraded from an old version for backwards compatibility, but will 404 on new chains):
    - `GET /public-blockchain-address`
    - `GET /v1/public-blockchain-address`
    - `POST /public-blockchain-transaction`
    - `POST /v1/public-blockchain-transaction`
  - Reduced initial delay checks for the webserver so kubernetes will mark the webserver as ready quicker
  - Add direct TLS support for the Dragonchain webserver (for NodePort deployed services)
- **Bugs:**
  - Fixed some bugs with the helm chart which caused the incorrect dockerhub image to be pulled
- **Documentation:**
  - Add docs/update helm chart and values for added TLS support
  - Fixed/elaborated on some of the process for connecting to Dragon Net, including exposing a chain to the internet
  - Add an export which allows hmac key generation to work correctly on MacOS
  - Update Helm chart/values to remove unnecessarily exposed settings
  - Add creation of the dragonchain namespace before creating a secret on deployment
  - Update Golang SDK URL
  - Various spelling fixes
- **Development:**
  - Refactored interchain support for easier future integration with further interchains
- **Packaging:**
  - Updated boto3, kubernetes, redis, and web3 dependencies
  - Removed unnecessary dependencies, and added speedup extras for aiohttp
  - Update fwatchdog to 0.16.0 for OpenFaaS smart contracts

## 3.4.46

- **Bugs:**
  - Don't require registration to bitcoin node on webserver boot
  - Properly handle 401-403 responses from matchmaking
- **Documentation:**
  - Update documentation for slack channel
  - Update deployment docs for more clarity
  - Update and fix docs helm chart to better work with open source chains
  - Update README
- **Packaging:**
  - Update boto3, redis, and kubernetes dependencies
  - Update fwatchdog to 0.15.4 for OpenFaaS smart contracts

## 3.4.45

- **Bugs:**
  - Fix bug with job processor consuming too much memory due to threads

## 3.4.43

- **Feature:**
  - Add route versioning (old routes are still backwards compatible)
  - Removed the interim matchmaking hack for old claim check compatibility
  - Sped up schema validation for http requests significantly
  - Added nickname functionality for api keys
  - Added matchmaking registration token support
  - Index transaction upon acceptance so immediate transaction lookups don't produce 404s
  - Add endpoint (/v1/verifications/pending/<block_id>) to get pending verification chain ids
- **Documentation:**
  - Added documentation with [new docs site](https://dragonchain-core-docs.dragonchain.com/latest/)
  - Updated README
  - Added changelog
- **Development:**
  - Added and started enforcing stricter typing
  - Added codeowners required for PR reviews
  - Added issue templates for github
  - Added committed/shared VSCode settings for linting/formatting
  - Improved error handling
  - Move webserver endpoints into routes module
- **Packaging:**
  - Switched Dockerfile to be based on python alpine image
  - Ignored more unnecessary files for docker builds
  - Switched jsonshema dependency for fastjsonschema
  - Update fwatchdog to 0.15.2 for OpenFaaS smart contracts
- **CICD:**
  - Updated cicd for new AWS buildspec runtimes
- **Bugs:**
  - No longer send HTML on certain 500 responses, only JSON
  - Remove any possible existing entrypoints from built smart contract containers
