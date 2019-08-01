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
from unittest.mock import patch

from dragonchain.lib.dao import transaction_type_dao
from dragonchain.lib.dto import transaction_type_model
from dragonchain import exceptions


class TestTransactionTypeDAO(unittest.TestCase):
    def test_module_has_correct_folder_correctly(self):
        self.assertEqual(transaction_type_dao.FOLDER, "TRANSACTION_TYPES")

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

    @patch("dragonchain.lib.dao.transaction_type_dao.redis.sadd_sync")
    @patch("dragonchain.lib.dao.transaction_type_dao.storage.put_object_as_json")
    def test_store_registered_txn_type_succeeds(self, storage_put_mock, redis_sadd_mock):
        instance = transaction_type_model.new_from_user_input({"version": "1", "txn_type": "test_type", "custom_indexes": []})
        transaction_type_dao.store_registered_transaction_type(instance)
        storage_put_mock.assert_called_once_with("TRANSACTION_TYPES/TYPES/test_type", instance.export_as_at_rest())
        redis_sadd_mock.assert_called_once_with("type_list_key", "test_type")

    @patch("dragonchain.lib.dao.transaction_type_dao.redis.srem_sync")
    @patch("dragonchain.lib.dao.transaction_type_dao.storage.delete", return_value=True)
    def test_delete_registered_txn_type_succeeds(self, storage_delete_mock, srem_mock):
        transaction_type_dao.remove_existing_transaction_type("randomTxn")
        srem_mock.assert_called_once_with("type_list_key", "randomTxn")
        storage_delete_mock.assert_called_with("TRANSACTION_TYPES/TYPES/randomTxn")
