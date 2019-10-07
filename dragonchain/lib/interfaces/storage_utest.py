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
import importlib
import unittest
from unittest.mock import MagicMock, patch

from dragonchain import test_env  # noqa: F401
from dragonchain import exceptions
from dragonchain.lib.interfaces import storage


class TestStorageInterfaceImport(unittest.TestCase):
    def tearDown(self):
        # Make sure we fix the import after the test continuing
        os.environ["STORAGE_TYPE"] = "s3"
        importlib.reload(storage)

    def test_storage_raises_not_implemented_with_bad_storage_type(self):
        os.environ["STORAGE_TYPE"] = "testing"
        self.assertRaises(NotImplementedError, importlib.reload, storage)


class TestStorageInterface(unittest.TestCase):
    def setUp(self):
        os.environ["STORAGE_TYPE"] = "s3"
        storage.STORAGE_LOCATION = "test"
        storage.storage = MagicMock()
        storage.redis.cache_get = MagicMock(return_value=None)
        storage.redis.cache_put = MagicMock(return_value=None)
        storage.redis.cache_delete = MagicMock(return_value=None)
        storage.redis.cache_condition = True

    def tearDown(self):
        importlib.reload(storage)
        importlib.reload(storage.redis)

    def test_get_calls_storage_get_with_params(self):
        storage.get("thing")
        storage.storage.get.assert_called_once_with("test", "thing")

    def test_get_raises_storage_error(self):
        storage.storage.get = MagicMock(side_effect=RuntimeError)
        self.assertRaises(exceptions.StorageError, storage.get, "thing")

    def test_get_calls_cache_with_correct_params(self):
        storage.storage.get = MagicMock(return_value=b"val")
        storage.redis.cache_get = MagicMock(return_value=None)
        storage.redis.cache_put = MagicMock(return_value=None)
        storage.get("thing")
        storage.redis.cache_get.assert_called_once_with("thing")
        storage.redis.cache_put.assert_called_once_with("thing", b"val", None)

    def test_get_raises_not_found(self):
        storage.storage.get = MagicMock(side_effect=exceptions.NotFound)
        self.assertRaises(exceptions.NotFound, storage.get, "thing")

    def test_put_calls_storage_put_with_params(self):
        storage.put("thing", b"val")
        storage.storage.put.assert_called_once_with("test", "thing", b"val")

    def test_put_raises_storage_error(self):
        storage.storage.put = MagicMock(side_effect=RuntimeError)
        self.assertRaises(exceptions.StorageError, storage.put, "thing", b"val")

    def test_put_calls_cache_with_correct_params(self):
        storage.put("thing", b"val")
        storage.redis.cache_put.assert_called_once_with("thing", b"val", None)

    def test_delete_calls_storage_delete_with_params(self):
        storage.delete("thing")
        storage.storage.delete.assert_called_once_with("test", "thing")

    def test_delete_raises_storage_error(self):
        storage.storage.delete = MagicMock(side_effect=RuntimeError)
        self.assertRaises(exceptions.StorageError, storage.delete, "thing")

    def test_delete_calls_cache_with_correct_params(self):
        storage.delete("thing")
        storage.redis.cache_delete.assert_called_once_with("thing")

    def test_list_objects_calls_storage_list_objects_with_params(self):
        storage.storage.list_objects = MagicMock()
        storage.list_objects("prefix")
        storage.storage.list_objects.assert_called_once_with("test", "prefix")

    def test_list_objects_throws_storage_error(self):
        storage.storage.list_objects = MagicMock(side_effect=RuntimeError)
        self.assertRaises(exceptions.StorageError, storage.list_objects, "thing")

    def test_does_superkey_exist_calls_storage_does_superkey_exist_with_params(self):
        storage.does_superkey_exist("prefix")
        storage.storage.does_superkey_exist.assert_called_once_with("test", "prefix")

    def test_does_superkey_exist_throws_storage_error(self):
        storage.storage.does_superkey_exist = MagicMock(side_effect=RuntimeError)
        self.assertRaises(exceptions.StorageError, storage.does_superkey_exist, "thing")

    def test_does_object_exist_calls_storage_does_object_exist_with_params(self):
        storage.does_object_exist("prefix")
        storage.storage.does_object_exist.assert_called_once_with("test", "prefix")

    def test_does_object_exist_throws_storage_error(self):
        storage.storage.does_object_exist = MagicMock(side_effect=RuntimeError)
        self.assertRaises(exceptions.StorageError, storage.does_object_exist, "thing")

    def test_put_object_as_json_calls_put_with_correct_params(self):
        storage.put = MagicMock()
        storage.put_object_as_json("key", {})
        storage.put.assert_called_once_with("key", b"{}", None, True)

    def test_get_json_from_object_calls_get_with_correct_params(self):
        storage.get = MagicMock(return_value=b"{}")
        storage.get_json_from_object("key")
        storage.get.assert_called_once_with("key", None, True)

    def test_get_json_from_object_returns_correct_json(self):
        storage.get = MagicMock(return_value=b"{}")
        self.assertEqual(storage.get_json_from_object("key"), {})
        storage.get_json_from_object("key")

    def test_delete_directory_calls_list_objects_with_correct_params(self):
        storage.list_objects = MagicMock(return_value=[])
        storage.delete_directory("thing")
        storage.list_objects.assert_called_once_with("thing")

    def test_delete_directory_calls_delete_with_correct_params(self):
        storage.list_objects = MagicMock(return_value=["obj"])
        storage.delete = MagicMock()
        storage.delete_directory("thing")
        storage.delete.assert_called_once_with("obj")

    def test_delete_directory_calls_delete_directory_with_correct_params(self):
        storage.list_objects = MagicMock(return_value=[])
        storage.delete_directory("thing")
        storage.storage.delete_directory.assert_called_once_with("test", "thing")

    def test_delete_directory_raises_storage_exception(self):
        storage.list_objects = MagicMock(side_effect=RuntimeError)
        self.assertRaises(exceptions.StorageError, storage.delete_directory, "thing")

    def test_select_transaction_calls_storage_select_transaction_with_params(self):
        storage.storage.select_transaction = MagicMock(return_value={})
        storage.select_transaction("block", "txn")
        storage.storage.select_transaction.assert_called_once_with("test", "block", "txn")

    def test_select_transaction_calls_cache_get_with_params(self):
        storage.storage.select_transaction = MagicMock(return_value={})
        storage.redis.cache_get = MagicMock(return_value="{}")
        storage.select_transaction("block", "txn")
        storage.redis.cache_get.assert_called_once_with("block/txn")

    def test_select_transaction_returns_correct_value_from_cache(self):
        storage.storage.select_transaction = MagicMock(return_value={})
        storage.redis.cache_get = MagicMock(return_value="{}")
        self.assertEqual(storage.select_transaction("block", "txn"), {})

    def test_select_transaction_returns_correct_value_from_storage(self):
        storage.storage.select_transaction = MagicMock(return_value={})
        self.assertEqual(storage.select_transaction("block", "txn"), {})

    def test_select_transaction_calls_cache_put_with_params(self):
        storage.storage.select_transaction = MagicMock(return_value={})
        storage.select_transaction("block", "txn")
        storage.redis.cache_put("block/txn", "{}", None)

    def test_select_transaction_raises_not_found(self):
        storage.storage.select_transaction = MagicMock(side_effect=exceptions.NotFound)
        self.assertRaises(exceptions.NotFound, storage.select_transaction, "block", "transaction")

    def test_select_transaction_raises_storage_error(self):
        storage.storage.select_transaction = MagicMock(side_effect=RuntimeError)
        self.assertRaises(exceptions.StorageError, storage.select_transaction, "block", "txn")

    @patch("time.time", return_value=123)
    def test_save_error_message(self, mock_time):
        storage.put = MagicMock()
        storage.save_error_message("some message")
        storage.put.assert_called_once_with(f"error_testing_123.log", b"some message", should_cache=False)
