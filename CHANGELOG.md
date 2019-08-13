# Changelog

## Latest

- **Feature:**
  - Switch to using files for reading secrets for dynamic secret update support

## 3.4.46

- **Bug:**
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

- **Bug:**
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
- **Bug Fixes**
  - No longer send HTML on certain 500 responses, only JSON
  - Remove any possible existing entrypoints from built smart contract containers
