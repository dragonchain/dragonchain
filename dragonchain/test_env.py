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

os.environ["STAGE"] = "test"
os.environ["HASH"] = "blake2b"
os.environ["RATE_LIMIT"] = "0"
os.environ["AWS_DEFAULT_REGION"] = "test"
os.environ["ENCRYPTION"] = "secp256k1"
os.environ["DRAGONCHAIN_VERSION"] = ""
os.environ["STORAGE_TYPE"] = "s3"
os.environ["STORAGE_LOCATION"] = ""
os.environ["SECRET_LOCATION"] = ""  # nosec
os.environ["DRAGONCHAIN_EMAIL"] = ""
os.environ["DRAGONCHAIN_NAME"] = ""
os.environ["DRAGONCHAIN_ENDPOINT"] = "http://fake.org"
os.environ["INTERNAL_ID"] = ""
os.environ["REDIS_ENDPOINT"] = ""
os.environ["REDISEARCH_ENDPOINT"] = ""
os.environ["REDIS_PORT"] = "1"
os.environ["LRU_REDIS_ENDPOINT"] = ""
os.environ["PROOF_SCHEME"] = "trust"
os.environ["LEVEL"] = "1"
os.environ["LOG_LEVEL"] = "OFF"
os.environ["TOPIC_ARN"] = ""
os.environ["FAAS_GATEWAY"] = ""
os.environ["REGISTRY"] = ""
os.environ["NAMESPACE"] = ""
os.environ["DEPLOYMENT_NAME"] = ""
os.environ["EVENT"] = ""
os.environ["FAAS_REGISTRY"] = ""
os.environ["TESTING"] = "true"
os.environ["BROADCAST"] = ""
os.environ["BROADCAST_INTERVAL"] = "2"
os.environ["REPORTING_TYPE"] = "custom"
os.environ["DATABASE_TYPE"] = "disk"
os.environ["REGISTRY_USERNAME"] = "someone"
os.environ["SERVICE"] = "testing"
os.environ["DRAGONCHAIN_IMAGE"] = "testing-image"
