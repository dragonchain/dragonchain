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
from typing import List

from dragonchain import exceptions


def process_key(key: str) -> str:
    """
    This function is for creating safe keys
    Currently this only replaces '..', should be expanded to be (or use) a full sanitizer in the future
    """
    key = key.replace("..", "__")  # Don't allow keys to traverse back a directory
    return key


def get(location: str, key: str) -> bytes:
    key = process_key(key)
    try:
        file = open(os.path.join(location, key), "rb")
    except FileNotFoundError:
        raise exceptions.NotFound
    contents = file.read()
    file.close()
    return contents


def put(location: str, key: str, value: bytes) -> None:
    key = process_key(key)
    path = os.path.join(location, key)
    try:
        file = open(path, "wb")
    except (NotADirectoryError, FileNotFoundError):
        # If directory doesn't exist, we need to create it
        os.makedirs(os.path.dirname(path))
        file = open(path, "wb")
    file.write(value)
    file.close()


def delete(location: str, key: str) -> None:
    key = process_key(key)
    os.remove(os.path.join(location, key))


def delete_directory(location: str, directory_key: str) -> None:
    """
    Recursively delete all directories under (and including) directory_key
    Will ONLY delete a directory if it's empty (or only comtains empty folders)
    Will raise an exception if deleting a directory containing any files
    """
    directory_key = process_key(directory_key)
    for root, dirnames, _ in os.walk(directory_key, topdown=False):
        for dirname in dirnames:
            os.rmdir(os.path.join(root, dirname))
    os.rmdir(directory_key)


def select_transaction(location: str, block_id: str, txn_id: str) -> dict:
    block_id = process_key(block_id)
    # Unfortunately, we can't cache this get due to recursive imports
    # If it is possible, this should be revisited
    obj = get(location, os.path.join("TRANSACTION", block_id)).decode("utf8")
    transactions = obj.split("\n")
    for transaction in transactions:
        try:
            loaded_txn = json.loads(transaction)
            if loaded_txn["txn_id"] == txn_id:
                return loaded_txn["txn"]
        except Exception:
            pass
    raise exceptions.NotFound


def list_objects(location: str, prefix: str) -> List[str]:
    prefix = process_key(prefix)
    directory = os.path.dirname(prefix)
    base = os.path.join(location, directory)
    prefixed_keys = []
    for root, _, files in os.walk(base):
        for name in files:
            key = os.path.relpath(os.path.join(root, name), location)
            if key.startswith(prefix):
                prefixed_keys.append(key)
    return prefixed_keys


def does_superkey_exist(location: str, key: str) -> bool:
    key = process_key(key)
    return os.path.isdir(os.path.join(location, key))


def does_object_exist(location: str, key: str) -> bool:
    key = process_key(key)
    return os.path.isfile(os.path.join(location, key))
