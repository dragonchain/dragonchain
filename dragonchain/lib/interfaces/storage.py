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
import time
from typing import Optional, List, Any, TYPE_CHECKING

from dragonchain import logger
from dragonchain import exceptions
from dragonchain.lib.database import redis

if TYPE_CHECKING:
    from dragonchain.lib.types import JSONType

_log = logger.get_logger()

LEVEL = os.environ["LEVEL"]
STAGE = os.environ["STAGE"]
STORAGE_TYPE = os.environ["STORAGE_TYPE"].lower()
STORAGE_LOCATION = os.environ["STORAGE_LOCATION"]
CACHE_LIMIT = 52428800  # Will not cache individual objects larger than this size (in bytes) (hardcoded to 50MB for now. Can change if needed)


if STORAGE_TYPE == "s3":
    import dragonchain.lib.interfaces.aws.s3 as storage
elif STORAGE_TYPE == "disk":
    import dragonchain.lib.interfaces.local.disk as storage  # noqa: T484 alternative import is expected
else:
    raise NotImplementedError(f"Storage type '{STORAGE_TYPE}' is unsupported")


def get(key: str, cache_expire: Optional[int] = None, should_cache: bool = True) -> bytes:
    """Returns an object from storage
    Args:
        key: The key to get from storage
        cache_expire: The amount of time (in seconds) until the key expires if cache miss
        should_cache: Whether or not to fetch/save to/from cache
    Returns:
        data as bytes
    Raises:
        exceptions.NotFound exception if key is not found in storage
        exceptions.StorageError on any unexpected error interacting with storage
    """
    try:
        obj = None
        if should_cache:
            obj = redis.cache_get(key)
        if not obj:
            obj = storage.get(STORAGE_LOCATION, key)
            if should_cache and len(obj) < CACHE_LIMIT:
                redis.cache_put(key, obj, cache_expire)
        return obj
    except exceptions.NotFound:
        raise
    except Exception:
        _log.exception("Uncaught exception while performing storage get")
        raise exceptions.StorageError("Uncaught exception while performing storage get")


def put(key: str, value: bytes, cache_expire: Optional[int] = None, should_cache: bool = True) -> None:
    """Puts an object into storage with optional cache write-thru
    Args:
        key: The key of the object being written in S3
        value: The value of the bytes object being written in S3
        cache_expire: The amount of time (in seconds) until the key expires in the cache
    Raises:
        exceptions.StorageError on any unexpected error interacting with storage
    """
    try:
        storage.put(STORAGE_LOCATION, key, value)
        if should_cache and len(value) < CACHE_LIMIT:
            redis.cache_put(key, value, cache_expire)
    except Exception:
        _log.exception("Uncaught exception while performing storage put")
        raise exceptions.StorageError("Uncaught exception while performing storage put")


def delete(key: str) -> None:
    """Deletes an object in S3 with cache write-thru
    Args:
        key: The key of the object being deleted in S3
    Raises:
        exceptions.StorageError on any unexpected error interacting with storage
    """
    try:
        storage.delete(STORAGE_LOCATION, key)
        redis.cache_delete(key)
    except Exception:
        _log.exception("Uncaught exception while performing storage delete")
        raise exceptions.StorageError("Uncaught exception while performing storage delete")


def delete_directory(directory_key: str) -> None:
    """Deletes a "directory" key (aka super key)
    Recursively lists all objects within a directory and deletes them, as well as the folders, if relevant
    Args:
        directory_key: The key of the directory to delete
    Raises:
        exceptions.StorageError on any unexpected error interacting with storage
    """
    try:
        keys = list_objects(directory_key)
        for key in keys:
            delete(key)
        storage.delete_directory(STORAGE_LOCATION, directory_key)
    except Exception:
        _log.exception("Uncaught exception while performing storage delete_directory")
        raise exceptions.StorageError("Uncaught exception while performing storage delete_directory")


def select_transaction(block_id: str, txn_id: str, cache_expire: Optional[int] = None) -> dict:
    """Returns an transaction in a block from S3 through the LRU cache
        block_id: The ID of the block being queried
        txn_id: The ID of the transaction in the block
        cache_expire: The amount of time (in seconds) until the key expires if cache miss
    Returns:
        transaction JSON object
    Raises:
        exceptions.NotFound exception when block id not found
        exceptions.StorageError on any unexpected error interacting with storage
    """
    try:
        obj: Any = None
        key = f"{block_id}/{txn_id}"
        obj = redis.cache_get(key)
        if obj:
            return json.loads(obj)
        obj = storage.select_transaction(STORAGE_LOCATION, block_id, txn_id)
        cache_val = json.dumps(obj, separators=(",", ":")).encode("utf-8")
        if len(cache_val) < CACHE_LIMIT:
            redis.cache_put(key, cache_val, cache_expire)
        return obj
    except exceptions.NotFound:
        raise
    except Exception:
        _log.exception("Uncaught exception while performing storage select_transaction")
        raise exceptions.StorageError("Uncaught exception while performing storage select_transaction")


def put_object_as_json(key: str, value: "JSONType", cache_expire: Optional[int] = None, should_cache: bool = True) -> None:
    """Puts a JSON serializable python object as JSON in storage with cache write-thru
    Args:
        key: The key of the object being written in storage
        value: The json-serializable object being written to storage
        cache_expire: The amount of time (in seconds) until the key expires in the cache
    """
    put(key, json.dumps(value, separators=(",", ":")).encode("utf-8"), cache_expire, should_cache)


def get_json_from_object(key: str, cache_expire: Optional[int] = None, should_cache: bool = True) -> Any:
    """Gets a JSON-parsable object from storage as a python object with caching
    Args:
        key: The key of the object being read from storage
        value: The JSON object being read from storage
        cache_expire: The amount of time (in seconds) until the key expires in the cache
    Returns:
        Parsed json object on success
    """
    return json.loads(get(key, cache_expire, should_cache))


def list_objects(prefix: str) -> List[str]:
    """List object keys under a common prefix
    Args:
        prefix The prefix key to scan
    Returns:
        list of string keys on success
    Raises:
        exceptions.StorageError on any unexpected error interacting with storage
    """
    try:
        return storage.list_objects(STORAGE_LOCATION, prefix)
    except Exception:
        _log.exception("Uncaught exception while performing storage list_objects")
        raise exceptions.StorageError("Uncaught exception while performing storage list_objects")


def does_superkey_exist(key: str) -> bool:
    """Tests whether or not a superkey ('directory') exists
    Args:
        key: The 'directory' key to check
    Returns:
        True if the object exists, False otherwise
    Raises:
        exceptions.StorageError on any unexpected error interacting with storage
    """
    try:
        return storage.does_superkey_exist(STORAGE_LOCATION, key)
    except Exception:
        _log.exception("Uncaught exception while performing storage does_superkey_exist")
        raise exceptions.StorageError("Uncaught exception while performing storage does_superkey_exist")


def does_object_exist(key: str) -> bool:
    """Tests whether or not an object key exists
    Args:
        key: The object key to check
    Returns:
        True if the object exists, False otherwise
    Raises:
        exceptions.StorageError on any unexpected error interacting with storage
    """
    try:
        return storage.does_object_exist(STORAGE_LOCATION, key)
    except Exception:
        _log.exception("Uncaught exception while performing storage does_object_exist")
        raise exceptions.StorageError("Uncaught exception while performing storage does_object_exist")


def save_error_message(message: str) -> None:
    """Can save an error, such as a stack traceback or any other string to storage
    Args:
        message: The error message to save
    """
    put(f"error_{time.time()}.log", message.encode("utf8"), should_cache=False)
