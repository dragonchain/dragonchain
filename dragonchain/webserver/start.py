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

import os
import json

from dragonchain.lib.dao import transaction_type_dao
from dragonchain.lib.interfaces import secrets
from dragonchain.lib.interfaces import storage
from dragonchain.lib.database import redis
from dragonchain.lib.database import elasticsearch
from dragonchain.lib import error_reporter
from dragonchain import logger
from dragonchain import exceptions


STAGE = os.environ["STAGE"]

_log = logger.get_logger()
error_allowed = True  # Switch to false if you want to test the start up script functionality in an ephemeral environment
# This if statement is for safety in staging/production environments
if STAGE == "dev" or STAGE == "prod":
    error_allowed = False


def start() -> None:
    """
    Ran by the webserver before it boots
    """
    try:
        # New chains are often given HMAC keys when created. If found, we write them to storage.
        key_id = secrets.get_dc_secret("hmac-id")
        json_key = json.dumps({"id": key_id, "key": secrets.get_dc_secret("hmac-key"), "root": True, "registration_time": 0}, separators=(",", ":"))
        _log.info("HMAC keys were given to this chain on-boot. Writing them to storage.")
        storage.put(f"KEYS/{key_id}", json_key.encode("utf-8"))
    except exceptions.NotFound:
        _log.info("No HMAC keys were given to this chain on-boot. Skipping cretential storage write.")

    _log.info("Rehydrating the redis transaction list cache")
    try:
        transaction_type_dao.rehydrate_transaction_types()
    except Exception:
        if not error_allowed:
            raise

    _log.info("Finish build successful")


if __name__ == "__main__":
    # Wait for ES and Redis to connect before starting initialization
    elasticsearch._set_elastic_search_client_if_necessary()
    redis._set_redis_client_if_necessary()
    try:
        start()
    except Exception as e:
        error_reporter.report_exception(e, "Uncaught error in webserver start")
        raise
