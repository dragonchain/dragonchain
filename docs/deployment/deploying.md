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
# First create the dragonchain namespace
echo '{"kind":"Namespace","apiVersion":"v1","metadata":{"name":"dragonchain","labels":{"name":"dragonchain"}}}' | kubectl create -f -
export LC_CTYPE=C  # Needed on MacOS when using tr with /dev/urandom
BASE_64_PRIVATE_KEY=$(openssl ecparam -genkey -name secp256k1 | openssl ec -outform DER | tail -c +8 | head -c 32 | xxd -p -c 32 | xxd -r -p | base64)
HMAC_ID=$(tr -dc 'A-Z' < /dev/urandom | fold -w 12 | head -n 1)
HMAC_KEY=$(tr -dc 'A-Za-z0-9' < /dev/urandom | fold -w 43 | head -n 1)
echo "Root HMAC key details: ID: $HMAC_ID | KEY: $HMAC_KEY"
SECRETS_AS_JSON="{\"private-key\":\"$BASE_64_PRIVATE_KEY\",\"hmac-id\":\"$HMAC_ID\",\"hmac-key\":\"$HMAC_KEY\",\"registry-password\":\"\"}"
kubectl create secret generic -n dragonchain "d-INTERNAL_ID-secrets" --from-literal=SecretString="$SECRETS_AS_JSON"
# Note INTERNAL_ID from the secret name should be replaced with the value of .global.environment.INTERNAL_ID from the helm chart values (opensource-config.yaml)
```

## Add Your TLS Certificate

This step is technically optional, but _HIGHLY_ recommended. Without this step,
your chain will not support HTTPS, which may be enforced in the future.

With the certificate that you wish to use with your chain, run the following
command:

```sh
kubectl create secret tls -n dragonchain "d-INTERNAL_ID-cert" --cert=PathToLocalCertFile --key=PathToLocalKeyFile
# Note INTERNAL_ID from the secret name should be replaced with the value of .global.environment.INTERNAL_ID from the helm chart values (opensource-config.yaml)
```

Note that the cert file should be a PEM encoded public key certificate, and the
key file should be a PEM encoded private key for the certificate. The
certificate should be the full certificate chain, or the configuration will not
work. If using [letsencrypt](https://letsencrypt.org/), the certificate file is
`fullchain.pem`, and the key file is `privkey.pem`.

This will upload your certificate to your kubernetes cluster, which can be used
by the chain. Once doing this, simply remember to set
`.global.environment.TLS_SUPPORT` to "true" when configuring
`opensource-config.yaml` in the next steps.

## Helm Chart

**Please Note**: The helm chart is subject to significant changes.

A documented template for the necessary configurable helm chart values can be
downloaded [HERE](links).

### Deploying Helm Chart

Before deploying the helm chart, a few variables need to be set in the
`opensource-config.yaml` file. This file is mostly self-documenting, so see the
comments for which values must be overridden (most of the important settings
are in the first section).

Once the values are set, install the helm chart with:

```sh
helm repo add dragonchain https://dragonchain-charts.s3.amazonaws.com
helm repo update
helm upgrade --install my-dragonchain --values opensource-config.yaml --namespace dragonchain dragonchain/dragonchain-k8s --version 1.0.1
```

If you need to change any values AFTER the helm chart has already been
installed, simply change the relevant values in `opensource-config.yaml` and
run the above command again.

You may also need to manually delete pods (which causes them to restart) after
upgrading if you changed any environment values. This is because these values
aren't changed while in an existing pod that is running, and helm will not
restart them for you.

## Checking Deployment

If the helm chart deployed successfully, there should now be pods for your
new chain in the `dragonchain` kubernetes namespace. You can check by running
`kubectl get pods -n dragonchain`.

### Get The Chain ID

In order to get the chain's ID required for use in the SDK(s) or cli, run the
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

If you have configured the chain to be accessible to Dragon Net, then you can
use its public `DRAGONCHAIN_ENDPOINT` value as the endpoint for your chain
without tunneling anything through kubernetes. See the section below for more
details on exposing your chain to the internet.

When using all these pieces of information with the SDK or CLI, they should be
able to interact with the Dragonchain as intended.

### Checking Dragon Net Configuration

In order for your chain to be working with Dragon Net, a few things need to be
confirmed. You chain must be correctly registered with the matchmaking service,
as well as be publicly exposed to the internet over the correct port. You can
check all of this at once by running the following with your public chain id
from earlier:

```sh
curl https://matchmaking.api.dragonchain.com/registration/verify/PUBLIC_CHAIN_ID_HERE
```

If this returns with a successful response, then the chain is registered and
connectable. As long as the chain's pods aren't crashing, the chain should be
working with Dragon Net.

If this returns anything except successful, then the chain is not properly
registered or exposed, and an error message with more details should be
presented in the response.

If the call reported that the chain registration could not be found, then the
chain has failed to register with matchmaking, and you should consult
transaction processor logs for more details.

Most other errors relate to being able to access the chain from the greater
internet via the URL that the chain registered with Dragon Net. First try to
follow the advice from the error provided by the call above. If it's still not
working, the following steps can also be taken for further debugging:

Run the following from a computer that is connected to the internet, but not
running the chain (requires `curl` and `jq`):

```sh
curl "$(curl https://matchmaking.api.dragonchain.com/registration/PUBLIC_CHAIN_ID_HERE -s | jq -r .url)"/health
```

Here is a list with some of the things that could be wrong depending on the
various failure outputs of the command above:

| Error                                          | Problem                                                                                                                                                                                                            |
| ---------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `Could not resolve host: null`                 | Chain is not registered correctly with matchmaking. Confirm that the transaction processor pod is not crashing, and the `DRAGONCHAIN_ENDPOINT` variable is set correctly in `opensource-config.yaml`               |
| `Could not resolve host: ...`                  | Chain's endpoint is not set correctly. Ensure that the `DRAGONCHAIN_ENDPOINT` variable is set correctly in `opensource-config.yaml` and that the DNS name in that endpoint resolves to where your chain is running |
| `Failed to connect to ...: Connection refused` | The chain is not properly exposed to the internet. See below for more details                                                                                                                                      |

#### Ensuring Chain is Reachable From The Internet

In order to use Dragon Net, your chain must be properly exposed to the
internet. By default, the opensource config values will configure the chain
to be exposed as a nodeport service on port 30000 (although this can be
changed as desired).

This means that the kubernetes cluster must be exposed to the internet on port
30000, and the `DRAGONCHAIN_ENDPOINT` value in the `opensource-config.yaml`
must be set to point to this location. This can either be a configured DNS
record, or a raw ip address. I.e. `http://1.2.3.4:30000` or
`http://abc.com:30000` if you've configured the DNS record abc.com to point to
the correct ip address of your cluster.

If you are using minikube, 2 things have to happen to be able to hit this
nodeport service from the greater internet:

1. If behind a NAT, port 30000 will have to be port-forwarded to the computer
   running minikube. Port forwarding is outside of the scope of this
   documentation, however various guides can be found online depending on your
   particular router.

1. If using minikube in a VM (which is the default unless you're running
   minikube on linux with `--vm-driver=none`), then your host computer must
   forward traffic it receives on port 30000 to the minikube VM. The process
   for setting this up is different depending on the vm driver that you are
   using. If you are using the default virtualbox vm driver, you can follow
   [these steps](https://cwienczek.com/2017/09/reaching-minikube-from-other-devices/).

In order to check that your chain is exposed correctly, simply run the curl
command from the section above.
