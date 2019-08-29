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

from dragonchain import exceptions
from dragonchain.lib.dto import transaction_type_model
from dragonchain.webserver.lib import transaction_types


class TestRegisterTransactionModel(unittest.TestCase):
    @patch("dragonchain.webserver.lib.transaction_types.transaction_type_dao.get_registered_transaction_type", return_value={})
    def test_register_txn_type_name_conflict(self, dao_register_txn_type_mock):
        txn_type_struct = {"version": "2", "txn_type": "random"}
        self.assertRaises(exceptions.TransactionTypeConflict, transaction_types.register_transaction_type_v1, txn_type_struct)

    @patch("dragonchain.webserver.lib.transaction_types.transaction_type_dao.create_new_transaction_type")
    @patch("dragonchain.webserver.lib.transaction_types.transaction_type_dao.get_registered_transaction_type", side_effect=exceptions.NotFound)
    def test_register_txn_type_succeeds(self, mock_get_registered_type, mock_queue):
        txn_type_struct = {"version": "2", "txn_type": "random"}
        transaction_types.register_transaction_type_v1(txn_type_struct)
        mock_get_registered_type.assert_called_once()
        mock_queue.assert_called_once()


class TestDeleteTransactionType(unittest.TestCase):
    @patch(
        "dragonchain.webserver.lib.transaction_types.transaction_type_dao.get_registered_transaction_type",
        return_value=transaction_type_model.TransactionTypeModel(contract_id="my-id"),
    )
    @patch("dragonchain.lib.dao.smart_contract_dao.contract_does_exist")
    def test_delete_if_txn_type_has_contract_id(self, dao_get_registered_txn_type_mock, mock_contract_does_exist):
        self.assertRaises(exceptions.ActionForbidden, transaction_types.delete_transaction_type_v1, "exists_but_contract")
        mock_contract_does_exist.assert_called_once()

    @patch("dragonchain.webserver.lib.transaction_types.transaction_type_dao.remove_existing_transaction_type")
    @patch(
        "dragonchain.webserver.lib.transaction_types.transaction_type_dao.get_registered_transaction_type",
        return_value=transaction_type_model.TransactionTypeModel(txn_type="random", contract_id=""),
    )
    def test_delete_txn_type_succeeds(self, mock_get_registered_type, dao_remove_txn_type_mock):
        transaction_types.delete_transaction_type_v1("random")
        mock_get_registered_type.assert_called_once_with("random")


class TestTransactionTypeList(unittest.TestCase):
    @patch("dragonchain.lib.interfaces.storage.list_objects", return_value=["items"])
    @patch("dragonchain.lib.interfaces.storage.get_json_from_object")
    def test_list_registered_txn_types_succeeds(self, storage_get_as_json_mock, get_list_mock):
        transaction_types.list_registered_transaction_types_v1()
        get_list_mock.assert_called()
        self.assertEqual(storage_get_as_json_mock.call_count, 1)
