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

import json
from typing import List

import boto3
import botocore

from dragonchain import exceptions

s3 = boto3.client("s3")


def get(location: str, key: str) -> bytes:
    """Returns an object from S3
    Args:
        location: The S3 bucket to use
        key: The S3 key to get
    Returns:
        data as bytes
    Raises:
        exceptions.NotFound exception if key is not found in S3
    """
    try:
        return s3.get_object(Bucket=location, Key=key)["Body"].read()
    except s3.exceptions.NoSuchKey:
        raise exceptions.NotFound


def put(location: str, key: str, value: bytes) -> None:
    """Puts an object in S3
    Args:
        location: The S3 bucket to use
        key: The key of the object being written in S3
        value: The value of the bytes object being written in S3
    Raises:
        RuntimeError exception if write fails
    """
    if s3.put_object(Bucket=location, Key=key, Body=value)["ResponseMetadata"]["HTTPStatusCode"] != 200:
        raise RuntimeError("S3 put failed to give 200 response")


def delete(location: str, key: str) -> None:
    """Deletes an object in S3 with cache write-thru
    Args:
        location: The S3 bucket to use
        key: The key of the object being deleted in S3
    Raises:
        RuntimeError exception if delete fails
    """
    if s3.delete_object(Bucket=location, Key=key)["ResponseMetadata"]["HTTPStatusCode"] != 204:
        raise RuntimeError("S3 delete failed to give 204 response")


def delete_directory(location: str, directory_key: str) -> None:
    """
    This method isn't relevant in S3 because directories are deleted
    once all keys under a 'directory' are gone. You don't have to delete
    individual empty folders.
    """
    pass


def select_transaction(location: str, block_id: str, txn_id: str) -> dict:
    """select_transaction helper function
    Args:
        location: The S3 bucket to use
        block_id: The ID of the block being searched
        txn_id: The ID of the transaction being searched for
    Returns:
        the transaction JSON object if found in query
    Raises:
        exceptions.NotFound exception when block id is not found
    """
    try:
        obj = s3.select_object_content(
            Bucket=location,
            Key=f"TRANSACTION/{block_id}",
            Expression=f"select s.txn from s3object s where s.txn_id = '{txn_id}' limit 1",  # nosec (this s3 select query is safe)
            ExpressionType="SQL",
            InputSerialization={"JSON": {"Type": "DOCUMENT"}},
            OutputSerialization={"JSON": {"RecordDelimiter": "\n"}},
        )
    except s3.exceptions.NoSuchKey:
        raise exceptions.NotFound
    # As implemented currently, will only return one result
    txn_data = ""
    for event in obj.get("Payload"):
        if event.get("Records"):
            txn_data = f'{txn_data}{event["Records"]["Payload"].decode("utf-8")}'
    if txn_data:
        return json.loads(txn_data)["txn"]
    raise exceptions.NotFound


def list_objects(location: str, prefix: str) -> List[str]:
    """List S3 keys under a common prefix
    Args:
        location: The S3 bucket to use
        prefix: The prefix key to scan
    Returns:
        list of string keys on success
    """
    paginator = s3.get_paginator("list_objects_v2")
    page_iterator = paginator.paginate(Bucket=location, Prefix=prefix)
    keys: List[str] = []
    for page in page_iterator:
        if page.get("Contents"):
            keys += [x["Key"] for x in page["Contents"]]
    for x in reversed(range(len(keys))):  # Must used reversed traditional range because we are removing elements
        if keys[x].endswith("/"):  # Don't include folders in list
            del keys[x]
    return keys


def does_superkey_exist(location: str, key: str) -> bool:
    response = s3.list_objects(Bucket=location, Prefix=key, MaxKeys=1)
    return bool(response.get("Contents"))


def does_object_exist(location: str, key: str) -> bool:
    """Tests whether or not an object key exists
    Args:
        location: The S3 bucket to use
        key: The key to check
    Returns:
        True if the object exists, False otherwise
    """
    try:
        s3.head_object(Bucket=location, Key=key)
        return True
    except botocore.exceptions.ClientError:
        return False
