# Copyright 2019 Dragonchain, Inc.
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

from dragonchain.lib.interfaces import secrets
from dragonchain.lib.interfaces import storage
from dragonchain.lib.database import redis
from dragonchain.lib.database import redisearch
from dragonchain.lib import error_reporter
from dragonchain import logger
from dragonchain import exceptions

_log = logger.get_logger()


def start() -> None:
    """
    Ran by the webserver before it boots
    """
    try:
        # Chains are given HMAC keys when created. If found, we write them to storage.
        key_id = secrets.get_dc_secret("hmac-id")
        _log.info("HMAC keys were given to this chain on-boot. Writing them to storage.")
        storage.put_object_as_json(f"KEYS/{key_id}", {"id": key_id, "key": secrets.get_dc_secret("hmac-key"), "root": True, "registration_time": 0})
    except exceptions.NotFound:
        _log.info("No HMAC keys were given to this chain on-boot. Skipping cretential storage write.")

    _log.info("Checking if redisearch indexes need to be regenerated")
    redisearch.generate_indexes_if_necessary()

    _log.info("Finish pre-boot successful")


if __name__ == "__main__":
    # Wait for Redis and Redisearch to connect before starting initialization
    redisearch._get_redisearch_index_client("test")
    redis._set_redis_client_if_necessary()
    redis._set_redis_client_lru_if_necessary()
    try:
        start()
    except Exception as e:
        error_reporter.report_exception(e, "Uncaught error in webserver start")
        raise
