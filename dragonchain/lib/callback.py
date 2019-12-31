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

import requests

from dragonchain.lib.database import redis
from dragonchain.lib.dto import transaction_model
from dragonchain import logger

CALLBACK_REDIS_KEY = "dc:tx:callback"

_log = logger.get_logger()


def register_callback(txn_id: str, callback_url: str) -> None:
    """Registers a the calling-back of a specific url once processing of a txn is complete"""
    redis.hset_sync(CALLBACK_REDIS_KEY, txn_id, callback_url)


def fire_if_exists(txn_id: str, transaction_model: transaction_model.TransactionModel) -> None:
    """ Fires a callback with a given payload, then removes from redis"""
    _log.debug(f"Looking in redis for callback: {CALLBACK_REDIS_KEY} {txn_id}")
    url = redis.hget_sync(CALLBACK_REDIS_KEY, txn_id)
    _log.debug(f"Found {url}")
    if url is not None:
        try:
            _log.debug(f"POST -> {url}")
            with requests.Session() as s:
                s.mount(url, requests.adapters.HTTPAdapter(max_retries=0))
                r = s.post(url, json=transaction_model.export_as_full(), timeout=10)
                _log.debug(f"POST <- {r.status_code}:{url}")
        except Exception:
            _log.exception("POST <- ERROR. No-op")

        redis.hdel_sync(CALLBACK_REDIS_KEY, txn_id)
