# Permissioning

Dragonchain has a built-in permissioning system, allowing specific api keys to
be either allowed or denied for certain dragonchain operations via the
Dragonchain api.

When using these permissions, policy documents on api keys which determine
which operations are allowed and forbidden.

## Setting Permissions

In order to set permissions, create or update an api key with a permissions
document (schema explained below).

By default, an api key with no explicitly set permissions will have access to
every endpoint, except the ability to create/update/delete api keys.

Keep in mind that the ability to create or update api keys is effectively a
root-level permission, because keys can be created or modified with elevated
permissions via those endpoints.

### Root API Key

The root api key (in the kubernetes secret when deploying the chain) will
always have permission to use any Dragonchain api endpoint (aside from
endpoints for Dragon Net operations, which are reserved for
dragonchain-to-dragonchain communication).

The root api key cannot be deleted.

## Permissions Document

The permissions document codifies all permissions explicitly allowed or denied
on a given api-key.

The document is a JSON object containing the document version (currently only
`"1"`), a `"default_allow"` boolean, which determines if the permissions should
be treated as a whitelist or a blacklist by default, and a `"permissions"`
object which defines further permissions.

The `"permissions"` object contains 3 parts (in order from most generic to most
specific):

1. The global object which can contain `"allow_create"`, `"allow_read"`,
   `"allow_update"`, `"allow_delete"` booleans, as well as api resource
   objects.
1. API resource objects which can contain `"allow_create"`, `"allow_read"`,
   `"allow_update"`, `"allow_delete"` booleans, as well as specific api
   endpoint permission objects.
1. API endpoint permission objects, which can contain a special schema for
   allowing or denying a particular api operation on a per-endpoint basis.

In a permissions document, the **_most specific_** (aka most deeply nested)
defined permission is the permission that is followed. This means that if an
endpoint permission object is defined, then that _and only that_ permission is
used to determine if the api key is allowed to perform an operation on that
endpoint. This happens because an endpoint permission object is the most deeply
nested item in a permissions document.

### Important Privilege Escalation Note

Since creating/modifying/deleting permissions via an api keys is a permissioned
action, it is important to explicitly deny api key operations if
create/update/delete permissions were implicitly given elsewhere.

Failure to do so can result in creating an api key, which itself can create a
more-permissioned key, thus leading to privilege escalation.

See the examples at the bottom of this page for more details/examples.

### API Endpoint Schemas

Each api endpoint can be individually turned on or off with an endpoint
permissions object. Most endpoints use a default schema which is simply an
object with the boolean `"allowed"` which turns that particular endpoint on or
off.

See the table (or custom endpoint list) below to check for custom permissions
on a per-endpoint basis.

### API Resources and Permission Names

The following are the available api resources exposed via the Dragonchain
RESTful API:

- `api_keys` : Operations related to dragonchain api keys
- `blocks` : Operations related to blocks on the chain
- `interchains` : Operations related to interchain (eth, btc, etc) operations
  (L1/5 Only)
- `misc` : Miscellaneous Operations (currently only getting status)
- `contracts` : Operations related to dragonchain smart contracts (L1 Only)
- `transaction_types` : Operations related to transaction types (L1 Only)
- `transactions` : Operations related to individual chain transactions (L1
  Only)
- `verifications` : Operations related to Dragon Net verifications (L1 Only)

The following are all the available api endpoints for permissioning, along with
their operation type, and whether or not their endpoint permission object has a
custom schema:

| API Resource        | Endpoint Name                          | Operation Type | Endpoint Schema |
| ------------------- | -------------------------------------- | -------------- | --------------- |
| `api_keys`          | `create_api_key`                       | `create`       | default         |
| `api_keys`          | `get_api_key`                          | `read`         | default         |
| `api_keys`          | `list_api_keys`                        | `read`         | default         |
| `api_keys`          | `delete_api_key`                       | `delete`       | default         |
| `api_keys`          | `update_api_key`                       | `update`       | default         |
| `blocks`            | `get_block`                            | `read`         | default         |
| `blocks`            | `query_blocks`                         | `read`         | default         |
| `interchains`       | `create_interchain`                    | `create`       | default         |
| `interchains`       | `update_interchain`                    | `update`       | default         |
| `interchains`       | `create_interchain_transaction`        | `create`       | default         |
| `interchains`       | `publish_interchain_transaction`       | `create`       | default         |
| `interchains`       | `list_interchains`                     | `read`         | default         |
| `interchains`       | `get_interchain`                       | `read`         | default         |
| `interchains`       | `delete_interchain`                    | `delete`       | default         |
| `interchains`       | `get_default_interchain`               | `read`         | default         |
| `interchains`       | `set_default_interchain`               | `create`       | default         |
| `interchains`       | `get_interchain_legacy`                | `read`         | default         |
| `interchains`       | `create_interchain_transaction_legacy` | `create`       | default         |
| `misc`              | `get_status`                           | `read`         | default         |
| `contracts`         | `get_contract`                         | `read`         | default         |
| `contracts`         | `get_contract_logs`                    | `read`         | default         |
| `contracts`         | `list_contracts`                       | `read`         | default         |
| `contracts`         | `create_contract`                      | `create`       | default         |
| `contracts`         | `update_contract`                      | `update`       | default         |
| `contracts`         | `delete_contract`                      | `delete`       | default         |
| `contracts`         | `get_contract_object`                  | `read`         | default         |
| `contracts`         | `list_contract_objects`                | `read`         | default         |
| `transaction_types` | `create_transaction_type`              | `create`       | default         |
| `transaction_types` | `delete_transaction_type`              | `delete`       | default         |
| `transaction_types` | `list_transaction_types`               | `read`         | default         |
| `transaction_types` | `get_transaction_type`                 | `read`         | default         |
| `transactions`      | `create_transaction`                   | `create`       | custom          |
| `transactions`      | `query_transactions`                   | `read`         | default         |
| `transactions`      | `get_transaction`                      | `read`         | default         |
| `verifications`     | `get_verifications`                    | `read`         | default         |
| `verifications`     | `get_pending_verifications`            | `read`         | default         |

### Custom Endpoint Permissions

The following are all of the endpoints with a custom permission schema for more
fine-grained permissioning control on that endpoint

#### `create_transaction`

This endpoint affects both the regular and bulk create transaction endpoints.
The custom endpoint permissions object for this permission allows an api key
to be allowed or denied permission to create a transaction based on the
transaction type of the transaction(s) that the api call is creating.

##### Schema

The schema for this custom endpoint permission object has the boolean
`"allowed"`, which similar to all other schemas, simply indicates if this
endpoint is enabled or disabled by default.

Additionally, there is the `"transaction_types"` object which defines which
transactions types are allowed (or denied), regardless of all other
permissions (including `"allowed"`).

The `"transaction_types"` object is a simple map of strings to booleans where
the string key is the name of the transaction type, and the boolean is whether
or not to allow the creation of a transaction with that type.

The following example allows all transactions to be created, _except_ for
transactions with the transaction type `honey`. Note that the `"butter": true`
is technically redundant since it implicitly already has permissions to create
any other transaction due to the `"allowed": true`

```text
...
{
  "allowed": true,
  "transaction_types": {
    "honey": false,
    "butter": true
  }
}
...
```

The following example allows _only_ transactions with the type `banana` to be
created.

```text
...
{
  "allowed": false,
  "transaction_types": {
    "banana": true
  }
}
...
```

If `"allowed"` is not defined, then its value is derived from its parent, which
is whether or not it is allowed to perform a `create` operation on the
`transaction` resource.

### Examples

The following are some examples of a full permissions document object,
explaining what the permissions document is allowing/denying.

---

This is a permissions document that allows all operations on all actions by
default, but globally disables any `delete` abilities, while explicitly
allowing `delete` on interchain operations and explicitly denying creating any
interchain transaction. Additionally, because `"default_allow": true` was set,
it also ensures that creating or updating api keys is not allowed (as to avoid
privilege escalation)

Note that the `"allow_delete": false` in the `api_keys` resource is technically
redundant, because deletions were already denied at the global level.
Regardless, this is still a valid schema.

```json
{
  "version": "1",
  "default_allow": true,
  "permissions": {
    "allow_delete": false,
    "interchains": {
      "allow_delete": true,
      "create_interchain_transaction": {
        "allowed": false
      }
    },
    "api_keys": {
      "allow_create": false,
      "allow_update": false,
      "allow_delete": false
    }
  }
}
```

---

This is a permissions document which disables all actions by default, but
globally allows any `read` operations. Additionally, it allows the creation of
transaction types, and explicitly denies reading any smart contract logs.

```json
{
  "version": "1",
  "default_allow": false,
  "permissions": {
    "allow_read": true,
    "transaction_types": {
      "allow_create": true
    },
    "contracts": {
      "get_contract_logs": {
        "allowed": false
      }
    }
  }
}
```

---

This is a permissions document that allows all operations on all actions by
default, but only allows creating transactions with the transaction type:
`banana`. Additionally, it also has disabled creating/updating/deleting api
keys in order to avoid privilege escalation.

```json
{
  "version": "1",
  "default_allow": true,
  "permissions": {
    "transactions": {
      "create_transaction": {
        "allowed": false,
        "transaction_types": {
          "banana": true
        }
      }
    },
    "api_keys": {
      "allow_create": false,
      "allow_update": false,
      "allow_delete": false
    }
  }
}
```

---

This is a permissions document that allows all operations on all actions by
default. The only difference between this and a root key is that a root key
cannot be deleted.

Note that `"permissions"` with an empty object is still required, even though
no further permissions were defined.

```json
{
  "version": "1",
  "default_allow": true,
  "permissions": {}
}
```
