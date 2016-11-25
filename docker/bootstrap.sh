#!/usr/bin/env bash

# Allow path to keys to keys to be specified in case they're located on a mounted volume
# If they're unspecified, create unique keys for this container.

if [ -z "$PRIVATE_KEY" ]; then
    export PRIVATE_KEY=/opt/dragonchain/pki/sk.pem
fi

if [ -z "$PUBLIC_KEY" ]; then
    export PUBLIC_KEY=/opt/dragonchain/pki/pk.pem
fi

if [ ! -f $PRIVATE_KEY ]; then
    echo "Generating private key"
    mkdir -p /opt/dragonchain/pki
    openssl ecparam -name prime256v1 -genkey -out /opt/dragonchain/pki/sk.pem
fi

if [ ! -f $PUBLIC_KEY ]; then
    echo "Generating public key"
    mkdir -p /opt/dragonchain/pki
    openssl ec -in $PRIVATE_KEY -pubout -out /opt/dragonchain/pki/pk.pem
fi

cd blockchain
eval $1