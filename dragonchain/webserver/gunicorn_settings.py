# Copyright 2020 Dragonchain, Inc.
# Licensed under the Apache License, Version 2.0 (the "Apache License")
# with the following modification; you may not use this file except in
# compliance with the Apache License and the following modification to it:
# Section 6. Trademarks. is deleted and replaced with:
#      6. Trademarks. This License does not grant permission to use the trade
#         names, trademarks, service marks, or product names of the Licensor
#         and its affiliates, except as required to comply with Section 4(c) of
#         the License and to reproduce the content of the NOTICE file.
# You may obtain a copy of the Apache License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the Apache License with the above modification is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied. See the Apache License for the specific
# language governing permissions and limitations under the Apache License.

import os

# Docs: https://docs.gunicorn.org/en/stable/settings.html

bind = f"0.0.0.0:{os.environ['WEB_PORT']}"
reuse_port = True
backlog = 4000
worker_class = "gevent"
workers = 3
keepalive = 90  # Make sure this is higher than the load balancer/ingress controller tcp keepalive timeout
sendfile = False
accesslog = "-"
loglevel = "info"
if os.environ.get("TLS_SUPPORT") == "true":
    certfile = "/etc/cert/tls.crt"
    keyfile = "/etc/cert/tls.key"

# The following are tweaks to prevent DOS attacks
# If these restrictions become a problem, they can be changed
limit_request_line = 4090  # How long the request 'path' can be (including in-line request params)
limit_request_fields = 30  # How many HTTP header fields in a request
limit_request_field_size = 4090  # Size of an HTTP request header field
