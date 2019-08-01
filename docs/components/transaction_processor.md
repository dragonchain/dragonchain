# Transaction Processor

Relevant To: All chains

## Overview

The transaction processor is the part of the chain which processes queued
transactions into blocks and fixates them on the blockchain.

For level 1 chains, this happens on a fixed period every 5 seconds. For chains
level 2-4, it is event based and runs whenever there are new transactions with
which to make blocks. Level 5 will check every minute, but will only create a
block and broadcast to public networks on a specific interval. This is because
broadcasting to some public networks can be prohibitively expensive.

### Entrypoint

In order to run the contract invoker, `sh entrypoints/transaction_processor.sh`
should be used as the command of the built docker container.

## Architecture

The transaction processor is scheduled via
[APScheduler](https://pypi.org/project/APScheduler/) to allow the transaction
processor to be re-executed on an interval. However, if a block is currently
being processed, a new block will not start processing. This is because chains
must have the previous block hash in order to create the next block (hence
'blockchain').

The transaction processor uses the queue from `queue.py` which manages state
with redis for what will be included in an upcoming block. This is equivalent
to a 'mempool' on other blockchains. This state is managed under the redis
keys `dc:tx:incoming` for unprocessed items, and `dc:tx:processing` for items
that are currently being processed (and can be recovered and re-processed in
the case of an error/crash).

## Flow

The general loop of the transaction processor goes as follows:

- Check and renew Dragon Net registration if necessary
- Retrieve all items from the queue (transactions on L1 chains, or blocks for
  verification level (2-5) nodes)
- A block is created by placing items into block. If it is a verification node,
  then verification occurs here
- The block is signed and stored. For L1 chains, it is added to the broadcast
  queue.
  For verification nodes, the block is sent to the requesting L1 chain(s) as
  receipt
- The items are cleared off the queue and the process exits

For L5 nodes, this is slightly altered. Where normally a block would be
created immediately, L5s store transactions until their `BROADCAST_INTERVAL`
has expired, then creates a block containing the all transactions since the
last broadcast. This block's hash is then broadcast to a public network.

After broadcasting to a public network, L5 nodes will wait until the
transaction has been confirmed before sending the receipt to L1 chains whose
blocks are contained within the L5 block.
