# Migrating From v3 to v4

Dragonchain follows [Semantic Versioning](https://semver.org), which means that
v4 introduced backwards-incompatible changes. If you are running a v3
Dragonchain, then the following are some considerations before upgrading.

## Redisearch Indexing Replacement

The main change with the v4 update is that ElasticSearch has been discarded and
replaced with redisearch as an indexing solution. This allows the footprint of
a Dragonchain to be significantly reduced, although breaking changes are
required.

This means a few things, primarily that query endpoints and custom indexing are
now completely different.

### Updated SDKs Required For Querying

Because there are breaking API changes with this new indexing system, in order
to use any type of querying with the Dragonchain, updated SDKs will need to be
used. These updated SDKs are already available, simply ensure that you have
installed version 4.0.0 or later for the SDKs in order to work with a v4
upgraded Dragonchain. Each relevant SDK will also have corresponding docs on
upgrade considerations for exact API changes required for their particular SDK.

Note that this also means that existing smart contracts which use the query
functions of a Dragonchain SDK version <4.0.0 will be broken, and need to be
updated to the newest SDK as well in order to continue working.

### Existing Indexing Migrations

With v4, ElasticSearch and all of its indexes are deleted, so indexes will need
to be regenerated for redisearch. Fortunately, Dragonchain will do this
dynamically on webserver boot. It will detect if migrations have ran before,
and if not, will scan through all of your existing blockchain data, re-indexing
everything from scratch.

This means that the first boot of the webserver for an upgraded v4 chain may
take a long time. In order to ensure that kubernetes does not try to reboot the
webserver with a liveliness probe for being 'unresponsive' while migrations are
running, set `webserverLiveliness` to `false` in the `opensource-config.yaml`
values file.

This value should be reset to `true` once the initial boot/migrations of from
the webserver is complete.

Also note that when upgrading, the persistent volume for ElasticSearch may not
be automatically deleted. You can manually delete the old ElasticSearch
persistent volume from kubernetes and its corresponding data to clear up space
after upgrading if desired.

#### Manually Triggering a Reindex

If you want to re-index all your blockchain data in the future for any reason,
you can do so by running the following command in the redisearch pod and
subsequently restarting the webserver:

```sh
# Make sure to run this on the redisearch and NOT the persistent redis, or else you will permantently break the chain
redis-cli flushall
```

All the notes above still applying when manually triggering a re-index like this.

### Custom Indexing Changes

As redisearch uses a different schema for indexing, any custom indexes that
exist in a v3 dragonchain are completely incompatible with v4 Dragonchains and
will be deleted upon upgrading.

Also note that indexes for transactions will now be deleted when their
transaction type (or smart contract) is removed, rather than persisting like
before. The transactions still exist, and can be retrieved directly if you have
their transaction ids, but transactions from deleted transaction types will not
be queryable. This saves on resources and allows a transaction type's name to
be freed up and not influence future queries after being removed.

### Querying Notes

v4 Dragonchains support querying both transactions and blocks (querying smart
contracts has been removed and replaced with a simple list which returns all
smart contracts).

It's worth noting that by default, all blocks have the following
redisearch fields which can be used when querying:

- `block_id` - Sortable numeric field
- `timestamp` - Sortable numeric field
- `prev_id` - Sortable numeric field

Note `prev_id` is the number of the previous block id in the blockchain.
This is useful if you want to step through the blockchain one block at a time
on an L1 chain, as their block ids are not necessarily incremented by the same
amount.

Transaction querying now requires you to specify the particular transaction
type to query, rather than querying every single transaction simultaneously.
Similar to blocks, all transactions have the following redisearch fields which
can be queried by default:

- `timestamp` - Sortable numeric field
- `block_id` - Sortable numeric field
- `tag` - Text field
- `invoker` - Tag field (Only exists on transactions created by smart contract output) (as of 4.1.0)

In addition to these fields, any fields specified as custom index fields
when creating the transaction type (or smart contract), can also be used when
querying.

## Dragon Net Communication

Note that communication with Dragon Net remains unchanged, so v3 Dragonchains
can still communicate with v4 Dragonchains, therefore updating to v4 is not
required. Please keep in mind that v3 will no longer receive any updates, so
it is highly recommended to upgrade.
