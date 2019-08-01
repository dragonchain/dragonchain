# Broadcast Processor

Relevant To: Level 1 chains

## Overview

The broadcast processor is responsible for retrieving verifications for
completed L1 blocks. The microservice uses Dragon Net to find validating nodes
that match criteria and request verifications from them.

The service's responsibilities include managing discovered Dragon Net chains
and re-broadcasting blocks if verifiations aren't returned in time.

Turning off or removing the broadcast processor removes the chain from Dragon
Net (although the `BROADCAST` environment variable should also be set to False
so that unnecessary state isn't loaded when creating blocks).

### Entrypoint

In order to run the broadcast processor,
`sh entrypoints/broadcast_processor.sh` should be used as the command of the
built docker container.

## Architecture

The broadcast processor takes advantage of
[redis zranges](https://redis.io/commands/zrange) where the score is a unix
timestamp in order to enable operating as an efficient pseudo-scheduler.

As long as the broadcast processor isn't currently sending broadcasts, it will
check this zrange every second to see if any blocks need to be broadcast.

Blocks are added to the `broadcast:in-flight` redis zrange with a score of the
unix timestamp when they should be next checked for broadcasting. Upon creation
or promotion of a block, this score is updated to 0 to indicate that the block
has not been broadcast at its current level yet.

The broadcast processor works linearly and will only try to get verifications
for a single level (2-5) at a time. Because the broadcast processor has retry
logic, it will ask for verifications from new chains if existing validating
nodes are unresponsive. This makes it possible to recieve more verifications
than desired. If this occurs, receipts for verifications after the required
amount will be refused.

When the broadcast processor performs a broadcast, it provides a deadline for
when the verification must be returned. The validating node can use this
deadline to discard validation requests that have already expired.

The broadcast processor keeps track of the state of verifications for a chain
with redis keys prefixed with `broadcast:block:`. Namely, it tracks the block's
current 'state' (the level it is broadcasting verifications to) and a set
containing the chain ids from which it has already recieved verifications.
This allows the broadcast processor to retry broadcasting blocks when
necessary.

When a receipt for a verification is recieved from a higher level, the block's
state is updated to either promote or finalize the block. Once a chain has
recieved all required verifications for a block, its state is removed from the
broadcasting system.

## Flow

When the broadcast processor boots, it starts an event loop, and starts
checking for blocks to broadcast every second. First it gets blocks that
currently need to be checked by scheduled timestamp. After pulling this list
of blocks, it checks each block's level and finds which chains it has recieved
verifications from (if any).

If the block had been sent to chains which did not respond before the deadline,
the broadcast processor will find new validating nodes to replace unresponsive
ones.

Once the broadcast processor has determined which nodes to broadcast to, it
will generate futures on the event loop for the http request to other chains.

Each block is re-scheduled to be checked again at some future point.

Once all http requests are completed, the loop continues and any new blocks
scheduled to be checked are evaluated.
