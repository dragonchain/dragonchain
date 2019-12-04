# Webserver Authentication

Dragonchain utilizes a custom HMAC-validated schema in order to authenticate
HTTP requests to the api webserver.

## Crafting An Authenticated Request

Please note the following are for dragonchain auth version `1`, which is the
only supported version at this time.

### Required Elements

In order to create an authenticated HTTP request to Dragonchain, the following
elements are needed:

- Capitalized HTTP verb of the request (i.e. `GET, POST, PUT, DELETE, PATCH`)
- Full path of the request, including query parameters (i.e.
  `/v1/path?some=value`)
- Public dragonchain id of the request (to be provided in an HTTP header:
  `dragonchain`)
- ISO 8601 UTC timestamp of the request (to be provided in an HTTP header:
  `timestamp`)
- The `Content-Type` header of the request (if it exists)
- The actual bytes of the body of the HTTP request (if it exists)
- The auth key id that you are using to perform the HMAC operations
- The auth key itself that is used as the secret in the HMAC operation
- The name of the supported HMAC hashing algorithm you are using (currently
  `SHA256`, `BLAKE2b512`, or `SHA3-256`)
- The version of the HMAC authentication scheme that you are using (currently
  only `1`)

### Generating the HMAC "signature"

In order to generate the actual HMAC "signature" that is to be sent in the
`Authorization` HTTP header, first assemble the message that you are going to
perform the HMAC operation on.

In order to do this, first take the bytes that will make up your HTTP request
body, and perform a hash on this data (using your desired supported hashing
method which must match the HMAC hash method). Take the result of this hash and
base64 encode it into a simple ascii string.

Note that this step is still _required_ even if your HTTP request does not have
a body. If this is the case, simply perform the above hash digest with no
bytes. For example, if you are using SHA256, then these operations should
result in using `47DEQpj8HBSa+/TImW+5JCeuQeRkm5NMpJWZG3hSuFU=` as the hashed
and base64-encoded (empty) body for every `GET` request (or any other request
without a body).

Now take the following elements and assemble them into a single string
delimited with newlines (`/n`) in this order:

```text
Uppercase HTTP Verb
Full Request Path
Public Dragonchain ID
ISO 8601 Timestamp
Content-Type header (empty string if it doesn't exist)
Base64-encoded hashed HTTP Body (created as described above)
```

Now UTF-8 encode this string, and perform an HMAC operation on the resulting
encoded bytes, using your auth key as the HMAC secret. Remember that the hash
method you used to hash the HTTP body must match the hash method used for this
HMAC operation.

Take the result of this HMAC operation and base64 encode it to get the
resulting "signature" that will be used in the final HTTP request.

### Assembling the HTTP Request

In order to assemble the authenticated HTTP request to send to Dragonchain,
make sure that the following data is set on the request:

#### Headers

- `timestamp`: Must be set to the ISO 8601 timestamp that was used when
  generating the HMAC signature.

  If this timestamp is too far off the current time, you will get an
  authorization error claiming that the timestamp is too skewed to be
  authenticated.

- `dragonchain`: Must be set to the public dragonchain ID that was used when
  generating the HMAC signature.

  If this ID does not match the ID of the chain that you are calling, then an
  authorization error will occur.

- `Content-Type`: Must be set to the value that was used when generating the
  HMAC signature. This header can be omitted entirely if an empty string was
  used for the content type in the HMAC generation.

- `Authorization`: Must be set to the authentication scheme used
  (`DC<version>-HMAC-<algorithm>`), followed by a space and a colon(`:`)
  separated string of `auth_key_id_used:hmac_signature`

  For example, if SHA256 was used as the hash/hmac algorithm, and an auth key
  with the id `ABCDEF123456` was used, then this full header may look like:
  `DC1-HMAC-SHA256 ABCDEF123456:hpbpaheNqGkJlT2OrUNiRtKAXLLs7e4nBKS/xkYNmpI=`

#### Body

Ensure that the HTTP body that you send are the same exact bytes used when
hashing the body for the HMAC signature. If there is a mis-match, authorization
will not work because the HMAC will not match.

#### Path

Ensure that the path of your http request (everything _after_ the fully
qualified domain name and protocol) starting from the initial `/`, and
**including** any query parameters, is exactly what was used when creating the
HMAC signature. If there is a mis-match, the request cannot be authenticated.
