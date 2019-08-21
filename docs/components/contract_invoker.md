# Contract Invoker

Relevant To: Level 1 chains with smart contracts

## Overview

The contract invoker's job is to manage the queue of smart contract invocation
requests and handle/wrap the output of the smart contracts appropriately.

This includes invoking serial contracts in a serial manner (1 at a time in an
ordered queue) and invoking parallel contracts as soon as the request is
received.

### Entrypoint

In order to run the contract invoker, `sh entrypoints/contract_invoker.sh`
should be used as the command of the built docker container.

## Architecture

There are two different methods to invoke contracts. A serial contract is given
a unique thread with a python Queue for communication with the main thread. All
parallel contracts are invoked from an event loop on the main thread.

## Flow

Upon receiving a new transaction, the webserver will check the txn_type to
determine if it is a smart contract invocation request. If it is, the
webserver pushes the invocation request to the `mq:contract-invoke` queue.

The contract invoker blocks on this redis queue and pushes requests onto the
`mq:contract-processing` hash for recovery in case of a crash. This hash is
checked and recovered at boot of the contract invoker.

The contract invoker determines if the request is for a serial or parallel
contract. If serial, it sends the request to the appropriate serial thread
(and starts the thread if it doesn't already exist). If parallel, it queues a
task onto the event loop.

The smart contract is then executed by making the appropriate http request to
OpenFaaS for the relevant contract and handling the result.

If the response contains a valid json object, the data is stored in the smart
contract's heap keyed by returned json object's keys. If the response is not
valid json, the data is stored in the smart contract's heap under the
`rawResponse` key.

Finally, the invoker creates a new transaction with the response of the smart
contract (and the invoker set as the transaction id which caused the
invocation) and queues it onto the chain, then removes the invocation request
from `mq:contract-processing`.
