# Webserver

Relevant To: All chains

## Overview

The webserver's job is to handle all incoming HTTP requests, whether it be from
another chain in Dragon Net, or an end-user.

It provides RESTful endpoints with access to various resources and
functionality. It also provides the ability for chains to communicate with each
other.

All endpoints except `/health` are authenticated. The `health` endpoint can
be used to determine if the webserver is running appropriately.

The webserver does not use its own TLS implementation. Instead, TLS for the
webserver should be handled by another component in front of the webserver
doing TLS termination, such as a kubernetes ingress controller or a load
balancer.

### Entrypoint

In order to run the webserver, `sh entrypoints/webserver.sh` should be used as
the command of the built docker container.

## Architecture

The webserver is built using Flask as the web framework, fronted with gunicorn
as the [WSGI](https://www.python.org/dev/peps/pep-3333/).

Routes are conditionally applied to the webserver on boot as defined by the
files in the routes folder, which are separated by logical resource groups.

Before boot, `webserver/start.py` will run. This acts as a pre-bootup script
for tasks that must occur before the chain is ready to use.

Decorators are used as a middleware defined on a per-route basis. They provide
authorization and permissioning to webserver routes.

Authorization is implemented as an HMAC-signed request consisting of the HTTP
verb, the full route (including query params), dragonchain id in a header,
timestamp in a header, content-type in a header (optional), and the actual
body of the request (if applicable). Implementation can be found in
`authorization.py`. Example client code is implemented in the SDKs.

All Dragon Net communication occurs via the webserver with routes defined
in `dragonnet.py` within the routes folder. Dragon Net uses the same
authentication schema, but requires HMAC keys associated with a chain's
public ID to be registered first.

Code only used by the webserver is placed into `webserver/lib`, so it doesn't
have to be imported by the other components unnecessarily at runtime.
