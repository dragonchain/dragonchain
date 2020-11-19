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

import unittest
from unittest.mock import patch, MagicMock

import botocore

from dragonchain import test_env  # noqa: F401
from dragonchain import exceptions
from dragonchain.lib.interfaces.aws import s3


class TestS3Interface(unittest.TestCase):
    @patch("dragonchain.lib.interfaces.aws.s3.s3.get_object")
    def test_get_calls_with_correct_params(self, mock_get_object):
        s3.get("test", "thing")
        mock_get_object.assert_called_once_with(Bucket="test", Key="thing")

    @patch("dragonchain.lib.interfaces.aws.s3.s3.get_object", side_effect=s3.s3.exceptions.NoSuchKey({}, {}))
    def test_get_throws_notfound_on_nosuckkey(self, mock_get_object):
        self.assertRaises(exceptions.NotFound, s3.get, "a", "b")

    @patch("dragonchain.lib.interfaces.aws.s3.s3.put_object", return_value={"ResponseMetadata": {"HTTPStatusCode": 200}})
    def test_put_calls_with_correct_params(self, mock_put_object):
        s3.put("test", "thing", b"hi")
        mock_put_object.assert_called_once_with(Bucket="test", Key="thing", Body=b"hi")

    @patch("dragonchain.lib.interfaces.aws.s3.s3.put_object", return_value={"ResponseMetadata": {"HTTPStatusCode": 400}})
    def test_put_raises_when_not_200(self, mock_put_object):
        self.assertRaises(RuntimeError, s3.put, "test", "thing", b"hi")

    @patch("dragonchain.lib.interfaces.aws.s3.s3.delete_object", return_value={"ResponseMetadata": {"HTTPStatusCode": 204}})
    def test_delete_calls_with_correct_params(self, mock_delete_object):
        s3.delete("test", "thing")
        mock_delete_object.assert_called_once_with(Bucket="test", Key="thing")

    @patch("dragonchain.lib.interfaces.aws.s3.s3.delete_object", return_value={"ResponseMetadata": {"HTTPStatusCode": 400}})
    def test_delete_raises_when_not_204(self, mock_delete_object):
        self.assertRaises(RuntimeError, s3.delete, "test", "thing")

    def test_delete_directory_does_nothing(self):
        s3.delete_directory("loc", "ok")

    @patch("dragonchain.lib.interfaces.aws.s3.s3.select_object_content", return_value={"Payload": [{"Records": {"Payload": b'{"txn":"thing"}'}}]})
    def test_select_calls_with_correct_params(self, mock_select_object_content):
        s3.select_transaction("loc", "block", "txn")
        mock_select_object_content.assert_called_once_with(
            Bucket="loc",
            Key="TRANSACTION/block",
            Expression="select s.txn, s.stripped_payload from s3object s where s.txn_id = 'txn' limit 1",
            ExpressionType="SQL",
            InputSerialization={"JSON": {"Type": "DOCUMENT"}},
            OutputSerialization={"JSON": {"RecordDelimiter": "\n"}},
        )

    @patch("dragonchain.lib.interfaces.aws.s3.s3.select_object_content", return_value={"Payload": [{"Records": {"Payload": b'{"txn":"thing"}'}}]})
    def test_select_gets_nested_data_properly(self, mock_select_object_content):
        self.assertEqual(s3.select_transaction("loc", "block", "txn"), "thing")

    @patch("dragonchain.lib.interfaces.aws.s3.s3.select_object_content", return_value={"Payload": [{}]})
    def test_select_raises_not_found_with_empty_records(self, mock_select_object_content):
        self.assertRaises(exceptions.NotFound, s3.select_transaction, "loc", "block", "txn")

    @patch("dragonchain.lib.interfaces.aws.s3.s3.select_object_content", side_effect=s3.s3.exceptions.NoSuchKey({}, {}))
    def test_select_transaction_raises_not_found_with_no_block(self, mock_select_content):
        self.assertRaises(exceptions.NotFound, s3.select_transaction, "a", "b", "c")

    @patch("dragonchain.lib.interfaces.aws.s3.s3.get_paginator")
    def test_list_objects_calls_with_correct_params(self, mock_paginator):
        mock_paginate = MagicMock()
        mock_paginate.paginate = MagicMock(return_value=[{}])
        mock_paginator.return_value = mock_paginate
        s3.list_objects("loc", "pre")
        mock_paginator.assert_called_once_with("list_objects_v2")
        mock_paginate.paginate.assert_called_once_with(Bucket="loc", Prefix="pre")

    @patch("dragonchain.lib.interfaces.aws.s3.s3.get_paginator")
    def test_list_objects_calls_returns_valid_keys(self, mock_paginator):
        mock_paginate = MagicMock()
        mock_paginate.paginate = MagicMock(return_value=[{"Contents": [{"Key": "val1"}, {"Key": "val2"}]}])
        mock_paginator.return_value = mock_paginate
        self.assertEqual(s3.list_objects("loc", "pre"), ["val1", "val2"])

    @patch("dragonchain.lib.interfaces.aws.s3.s3.get_paginator")
    def test_list_objects_filters_folders(self, mock_paginator):
        mock_paginate = MagicMock()
        mock_paginate.paginate = MagicMock(return_value=[{"Contents": [{"Key": "val1/"}, {"Key": "val2/"}]}])
        mock_paginator.return_value = mock_paginate
        self.assertEqual(s3.list_objects("loc", "pre"), [])

    @patch("dragonchain.lib.interfaces.aws.s3.s3.list_objects")
    def test_does_superkey_exist_calls_with_correct_params(self, mock_list):
        s3.does_superkey_exist("loc", "key")
        mock_list.assert_called_once_with(Bucket="loc", Prefix="key", MaxKeys=1)

    @patch("dragonchain.lib.interfaces.aws.s3.s3.list_objects", return_value={"Contents": "thing"})
    def test_does_superkey_exist_returns_true_with_contents(self, mock_list):
        self.assertTrue(s3.does_superkey_exist("loc", "key"))

    @patch("dragonchain.lib.interfaces.aws.s3.s3.list_objects", return_value={})
    def test_does_superkey_exist_returns_false_without_contents(self, mock_list):
        self.assertFalse(s3.does_superkey_exist("loc", "key"))

    @patch("dragonchain.lib.interfaces.aws.s3.s3.head_object")
    def test_does_object_exist_calls_with_correct_params(self, mock_head):
        s3.does_object_exist("loc", "key")
        mock_head.assert_called_once_with(Bucket="loc", Key="key")

    @patch("dragonchain.lib.interfaces.aws.s3.s3.head_object")
    def test_does_object_exist_returns_true_when_existing(self, mock_head):
        self.assertTrue(s3.does_object_exist("loc", "key"))

    @patch("dragonchain.lib.interfaces.aws.s3.s3.head_object", side_effect=botocore.exceptions.ClientError({}, {}))
    def test_does_object_exist_returns_false_when_head_error(self, mock_head):
        self.assertFalse(s3.does_object_exist("loc", "key"))
