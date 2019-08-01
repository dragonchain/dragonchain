# Deploying A Dragonchain

In order to deploy a Dragonchain, helm is required.

## Create Chain Secrets

Each chain has a list of secrets that it requires.
These secrets need to be generated and saved to kubernetes before a chain
can be deployed.

Chain secrets can be generated and deployed with the following commands:

(Note you will need xxd (often packaged with vim) and openssl for these
commands to work; If you are not running linux, you can easily do this in a
docker container such as `ubuntu:latest` and simply ensure that you run
`apt update && apt install -y openssl xxd` in order to have the requirements
to generate the private keys)

```sh
BASE_64_PRIVATE_KEY=$(openssl ecparam -genkey -name secp256k1 | openssl ec -outform DER | tail -c +8 | head -c 32 | xxd -p -c 32 | xxd -r -p | base64)
HMAC_ID=$(cat /dev/urandom | tr -dc 'A-Z' | fold -w 12 | head -n 1)
HMAC_KEY=$(cat /dev/urandom | tr -dc 'A-Za-z0-9' | fold -w 43 | head -n 1)
ETH_MAINNET_PRIVATE_KEY=$(openssl ecparam -genkey -name secp256k1 | openssl ec -outform DER | tail -c +8 | head -c 32 | xxd -p -c 32 | xxd -r -p | base64)
ETH_ROPSTEN_PRIVATE_KEY=$(openssl ecparam -genkey -name secp256k1 | openssl ec -outform DER | tail -c +8 | head -c 32 | xxd -p -c 32 | xxd -r -p | base64)
ETC_MAINNET_PRIVATE_KEY=$(openssl ecparam -genkey -name secp256k1 | openssl ec -outform DER | tail -c +8 | head -c 32 | xxd -p -c 32 | xxd -r -p | base64)
ETC_MORDEN_PRIVATE_KEY=$(openssl ecparam -genkey -name secp256k1 | openssl ec -outform DER | tail -c +8 | head -c 32 | xxd -p -c 32 | xxd -r -p | base64)
BTC_MAINNET_PRIVATE_KEY=$(openssl ecparam -genkey -name secp256k1 | openssl ec -outform DER | tail -c +8 | head -c 32 | xxd -p -c 32 | xxd -r -p | base64)
BTC_TESTNET3_PRIVATE_KEY=$(openssl ecparam -genkey -name secp256k1 | openssl ec -outform DER | tail -c +8 | head -c 32 | xxd -p -c 32 | xxd -r -p | base64)
SECRETS_AS_JSON="{\"private-key\":\"$BASE_64_PRIVATE_KEY\",\"hmac-id\":\"$HMAC_ID\",\"hmac-key\":\"$HMAC_KEY\",\"registry-password\":\"\",\"eth-ropsten-private-key\":\"$ETH_ROPSTEN_PRIVATE_KEY\",\"eth-mainnet-private-key\":\"$ETH_MAINNET_PRIVATE_KEY\",\"etc-morden-private-key\":\"$ETC_MORDEN_PRIVATE_KEY\",\"etc-mainnet-private-key\":\"$ETC_MAINNET_PRIVATE_KEY\",\"btc-testnet3-private-key\":\"$BTC_TESTNET3_PRIVATE_KEY\",\"btc-mainnet-private-key\":\"$BTC_MAINNET_PRIVATE_KEY\"}"
kubectl create secret generic -n dragonchain "d-INTERNAL_ID-secrets" --from-literal=SecretString="$SECRETS_AS_JSON"
# Note INTERNAL_ID from the secret name should be replaced with the value of .global.environment.INTERNAL_ID from the helm chart values (opensource-config.yaml)
```

## Helm Chart

**Please Note**: The helm chart is subject to significant changes.
A helm chart is provided here, but will have better support in the
future.

Both the helm chart and a template for the necessary values can be downloaded
[HERE](links).

### Deploying Helm Chart

Before deploying the helm chart, a few variables need to be set in the
`opensource-config.yaml` file. This file is mostly self-documenting, so see the
comments for which values must be overidden.

Once the values are set, install the helm chart with:

```sh
helm install dragonchain-k8s-0.9.0.tgz -f opensource-config.yaml --name my-dragonchain --namespace dragonchain
```

## Checking Deployment

If the helm chart deployed successfully, there should now be pods for your
new chain in the `dragonchain` kubernetes namespace. You can check by running
`kubectl get pods -n dragonchain`.

### Get The Chain ID

In order to get the chain's ID required for use in the SDK(s), run the
following command:

(Replace <POD_NAME_HERE> with one of the core image chain pods. Eg:
`d-e2603f14-1a3d-4a47-9dce-ab0eba579850-tx-processor-5f49d9k5vpn`)

```sh
kubectl exec -n dragonchain <POD_NAME_HERE> -- python3 -c "from dragonchain.lib.keys import get_public_id; print(get_public_id())"
```

### Using The SDK

With the chain deployed, the SDK(s) (or CLI tool) can be configured with the
`HMAC_ID` and `HMAC_KEY` from earlier (when creating the secrets), as well as
the chain ID from above, and finally an endpoint into your webserver's
kubernetes service.

This endpoint can be proxied without any sort of ingress by using the
`kubectl proxy` command with the webserver pod for port 8080, and using
`http://localhost:8080` for the chain endpoint.

When using all these pieces of information with the SDK or CLI, they should be
able to interact with the Dragonchain as intended.

### Checking Dragon Net Configuration

If the transaction processor for your chain does not go into state
`CrashLoopBackoff`, your Dragon Net configuration is working. The transaction
processor handles registering with Dragon Net, so it will continue to fail if
registration fails. Check the pod's logs (`kubectl logs`) for further details.
