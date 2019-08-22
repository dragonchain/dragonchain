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

import unittest
from unittest.mock import patch, MagicMock

from dragonchain import test_env  # noqa: F401
from dragonchain.lib.dao import transaction_type_dao
from dragonchain.lib.dto import transaction_type_model
from dragonchain import exceptions


class TestTransactionTypeDAO(unittest.TestCase):
    def test_module_has_correct_folder_correctly(self):
        self.assertEqual(transaction_type_dao.FOLDER, "TRANSACTION_TYPES/TYPES")

    @patch(
        "dragonchain.lib.dao.transaction_type_dao.storage.get_json_from_object",
        return_value={"version": "1", "txn_type": "random", "custom_indexes": [], "contract_id": None},
    )
    def test_get_registered_transaction_type_succeeds(self, storage_get_mock):
        instance = transaction_type_dao.get_registered_transaction_type("test_type")
        storage_get_mock.assert_called_once_with("TRANSACTION_TYPES/TYPES/test_type")
        self.assertIsInstance(instance, transaction_type_model.TransactionTypeModel)

    @patch("dragonchain.lib.dao.transaction_type_dao.storage.get", side_effect=exceptions.NotFound)
    def test_get_registered_transactions_raises_not_found(self, storage_get_mock):
        self.assertRaises(exceptions.NotFound, transaction_type_dao.get_registered_transaction_type, "test_type")

    @patch("dragonchain.lib.database.redis.lpush_sync")
    @patch("dragonchain.lib.database.redisearch.force_create_transaction_index")
    @patch("dragonchain.lib.dao.transaction_type_dao.storage.put_object_as_json")
    def test_create_registered_txn_type_succeeds(self, storage_put_mock, rsearch_create_mock, mock_lpush):
        instance = transaction_type_model.new_from_user_input({"version": "2", "txn_type": "test_type", "custom_indexes": []})
        transaction_type_dao.create_new_transaction_type(instance)
        storage_put_mock.assert_called_once_with("TRANSACTION_TYPES/TYPES/test_type", instance.export_as_at_rest())
        rsearch_create_mock.assert_called_once_with("test_type", [])
        mock_lpush.assert_called_once_with("mq:txn_type_creation_queue", "test_type")

    @patch("dragonchain.lib.database.redisearch.delete_index")
    @patch("dragonchain.lib.dao.transaction_type_dao.storage.delete", return_value=True)
    def test_delete_registered_txn_type_succeeds(self, storage_delete_mock, rsearch_delete_mock):
        transaction_type_dao.remove_existing_transaction_type("randomTxn")
        storage_delete_mock.assert_called_with("TRANSACTION_TYPES/TYPES/randomTxn")
        rsearch_delete_mock.assert_called_once_with("randomTxn")

    @patch(
        "dragonchain.lib.dao.transaction_type_dao.get_registered_transaction_type",
        return_value=MagicMock(txn_type="blah", export_as_at_rest=MagicMock(return_value={})),
    )
    @patch("dragonchain.lib.database.redis.pipeline_sync", return_value=MagicMock(execute=MagicMock(return_value=[[b"txn_id"], 4])))
    @patch("dragonchain.lib.dao.transaction_type_dao.storage.put_object_as_json")
    def test_activate_transaction_types_if_necessary(self, store_mock, redis_mock, mock_get_txn_type):
        transaction_type_dao.activate_transaction_types_if_necessary("1000")
        redis_mock.assert_called_once()
        store_mock.assert_called_once_with("TRANSACTION_TYPES/TYPES/blah", {})
        mock_get_txn_type.assert_called_once_with("txn_id")
