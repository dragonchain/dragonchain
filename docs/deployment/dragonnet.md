# Registering With Dragon Net

In order for your chain to participate in Dragon Net, a token is
required.

This token can be received for free with a Dragonchain account from the
[Dragonchain Console](https://console.dragonchain.com/).

After logging into an account, there is a button to get a token and id
for a chain of a desired level. Copy this information somewhere safe as it
will be needed when deploying the specified chain later.

## Running Without Dragon Net Support

It is possible to run an L1 chain without participating in Dragon Net. This
means that the chain will not receive any verifications or checkpoint with
public blockchains. To disable this feature, set 'BROADCAST' to false when
deploying the chain, and set the Internal ID and Registration Token to
anything.

For chains other than level 1, it does not make sense to run without Dragon
Net support. Higher level chains run code to verify L1 transactions and require
Dragon Net to function.

## Running With A Custom Dragon Net

Running a custom Dragon Net to establish a private network is not currently
supported at the moment. This feature is planned to be available in the future.
