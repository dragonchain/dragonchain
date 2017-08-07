Dragonchain Smart Contracts
===

Smart Contracts in Dragonchain allow custom business rules to be privately deployed to your node's blockchain, 
similar to stored procedures in a traditional database. Unlike stored procedures however, Dragonchain Smart Contracts 
are signed, provide higher level features for integrating with blockchain data and are datastore agnostic. 

Since Dragonchain is a hybrid permissioned / public ledger, it's assumed that smart contracts are written and signed by 
trusted parties. This loosens requirements that would apply to a public blockchain since your smart contracts only run 
on trusted nodes. As such, Dragonchain doesn't require a proprietary VM and associated custom languages for executing smart 
contracts avoiding the notion of _gas_ and _cost per instruction_ altogether. This is suitable for business-critical 
applications since operational costs are fixed and independent of currency speculation while still providing a 
cryptographically secured immutable database environment.

Polyglot smart contracts are on the roadmap, the current implementation is Python based.

Smart Contract (SC) Types
===

- Transaction SC (TSC) - Primary business logic, runs on applicable transactions during phase 1
- Subscription SC (SSC) - Processes blocks received from peers via subscriptions
- Library SC (LSC) - Reusable or utility smart contracts deployed as libraries -- _(not yet implemented)_
- Broadcast Receipt SC (BSC) - Processes consensus verification information from higher phase nodes
- Cron/Scheduled SC (CSC) - Smart contract that will be executed on a schedule -- _(not yet implemented)_

Transaction SC
===

The TSC allows implementation of custom business logic to process and *approve* or *deny* transactions that your node receives. It provides the final verification and guarantee that a transaction is accurate and valid according to your own business rules before being accepted into the current block and broadcast to the network. 

Smart Contracts are deployed by submitting a transaction to your node. The following payload schema is used by Dragonchain for representing TSCs:

```
{
 "smart_contract": {
   "implementation": "trusted",
   "tsc": "def func(self, transaction): return True"
 },
 "version": 1
}
```

A handler called "func" must be defined in your smart contract. It will be invoked for each pre-phase 1 transaction encountered in a given block period. 
If your function returns false or throws an exception the transaction will be rejected. 

*Note:* While the SC implementation is shown here, it should be base64 encoded in practice.

Potential uses cases:
 
 - Validating the schema of a custom business payload
 - Authenticating the signature chain of a transaction

### Schema Validation Example

Since Dragonchain allows transactions to contain custom JSON payloads it provides a lot of flexibility when
integrating. However, since transaction data is immutable it would be prudent to validate your custom payloads for 
data integrity.

A hypothetical custom payload could be tracking the location of a physical asset. The full transaction to represent
a location record could be the following:

```
{
  "header": {
    "create_ts": 1475180987,
    "business_unit": "a3e13076-8683-11e6-97a9-3c970e3bee11",
    "family_of_business": "Test Business Family",
    "line_of_business": "My Business",
    "owner": "Test Node",
    "transaction_type": "LOCATION_RECORD",
    "entity": "c78f4526-8683-11e6-b1c6-3c970e3bee11" //the id of the asset being tracked
  },
  "payload": {
    "lat": 25.0,
    "long": -71.0,
    "timestamp": 1502073772
  }
}
```

The following TSC logic validates that a given payload contains "lat" and "long" as floating numbers 
that don't exceed bounds:

```
def func(self, transaction): 
    payload = transaction["payload"]
    if "lat" not in payload or "long" not in payload or "timestamp" not in payload:
        return False

    lat = float(payload["lat"])
    long = float(payload["long"])
    return lat >= -90 and lat <= 90 and long >= -180 and long <= 180
```

To provision this TSC, the body of the script must be base64 encoded. The provisioning transaction may look 
like the following:

```
{
  "header": {
    "create_ts": 1475180987,
    "business_unit": "a3e13076-8683-11e6-97a9-3c970e3bee11",
    "family_of_business": "Test Business Family",
    "line_of_business": "My Business",
    "owner": "Test Node",
    "transaction_type": "TT_PROVISION_TSC",
    "actor": "c26dd972-8683-11e6-977b-3c970e3bee11",
    "entity": "c78f4526-8683-11e6-b1c6-3c970e3bee11"
  },
  "payload": {
    "smart_contract": {
      "transaction_type": "LOCATION_RECORD",
      "implementation": "trusted",
      "tsc": "ZGVmIGZ1bmMoc2VsZiwgdHJhbnNhY3Rpb24pOiANCiAgICBwYXlsb2FkID0gdHJhbnNhY3Rpb25bInBheWxvYWQiXQ0KICAgIGlmICJsYXQiIG5vdCBpbiBwYXlsb2FkIG9yICJsb25nIiBub3QgaW4gcGF5bG9hZCBvciAidGltZXN0YW1wIiBub3QgaW4gcGF5bG9hZDoNCiAgICAgICAgcmV0dXJuIEZhbHNlDQoNCiAgICBsYXQgPSBmbG9hdChwYXlsb2FkWyJsYXQiXSkNCiAgICBsb25nID0gZmxvYXQocGF5bG9hZFsibG9uZyJdKQ0KICAgIHJldHVybiBsYXQgPj0gLTkwIGFuZCBsYXQgPD0gOTAgYW5kIGxvbmcgPj0gLTE4MCBhbmQgbG9uZyA8PSAxODA="
    },
    "version": 1
  }
}
```

After submitting this transaction to the transaction service, future LOCATION_RECORD transactions will be validated by 
the custom TSC.

### Signature Authentication Example

All transactions submitted to Dragonchain contain a signature block. Even if the transaction you submitted doesn't
contain a signature the transaction service will always sign the payload before it enters the database. The signatures
nest one on top of another, creating a verifiable chain that the payload received by your node matches the signatures.

While Dragonchain automatically performs such verifications, simply verifying the public keys and signatures of a 
transaction doesn't necessarily mean it originated from a trustworthy source.

In the case of our previous example, we may want to ensure that only trusted public keys are submitting location 
records. 

```
def func(self, txn):
    sig = txn["signature"]
    #traverse signature hierarchy to root
    while "child_signature" in sig:
        sig = sig["child_signature"]
    #verify the public key is the expected value
    return sig["public_key"] == "TRUSTED_PUBLIC_KEY"

```

With this we can now assert that records in the blockchain are not only immutable, but were also trustworthy at the
time they were accepted.

It is an exercise left up to the reader to handle key-rotations. Since smart contracts are versioned one could 
simply update the smart contract with the most up-to-date key. A more advanced implementation could store trusted
public keys as a custom transaction type to be queried later as needed.

Summary
===

Future guides will be published on how and when to use the other types of smart contracts. On the roadmap is an internal
API for smart contracts to query existing or create new transactions.