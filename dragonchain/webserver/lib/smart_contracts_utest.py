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

from dragonchain import test_env  # noqa: F401
from dragonchain.lib.dto import smart_contract_model
from dragonchain import exceptions
from dragonchain.webserver.lib import smart_contracts


def get_sc_create_body():
    return {"version": "3", "txn_type": "test", "image": "myreg/myrepo:mytag", "cmd": "echo", "args": ["hello", "world"], "execution_order": "serial"}


def get_sc_create_body_with_custom_indexes():
    sc_body = get_sc_create_body()
    sc_body["custom_indexes"] = [{"path": "ba/na/na", "field_name": "banana", "type": "tag", "options": {}}]
    return sc_body


def get_sc_create_body_with_bad_cron():
    return {
        "version": "3",
        "txn_type": "test",
        "image": "myreg/myrepo:mytag",
        "cmd": "echo",
        "args": ["hello", "world"],
        "execution_order": "serial",
        "cron": "banana",
    }


def get_sc_update_body():
    return {"image": "myreg/myrepo:mytagv2", "version": "3"}


class TestCreateContract(unittest.TestCase):
    @patch("dragonchain.lib.dao.smart_contract_dao.add_smart_contract_index")
    @patch("dragonchain.webserver.lib.smart_contracts.transaction_type_dao.get_registered_transaction_type", side_effect=exceptions.NotFound)
    @patch("dragonchain.webserver.lib.smart_contracts.transaction_type_dao.register_smart_contract_transaction_type")
    @patch("dragonchain.lib.database.redisearch.get_document_count", return_value=0)
    @patch("dragonchain.job_processor.begin_task")
    def test_create_contract(self, patch_job_proc, mock_get_count, mock_register_sc_type, mock_get_registered, mock_add_index):
        smart_contracts.create_contract_v1(get_sc_create_body())

        mock_get_count.assert_called_once()
        mock_register_sc_type.assert_called_once()
        patch_job_proc.assert_called_once()
        mock_get_registered.assert_called_once()
        mock_add_index.assert_called_once()

    @patch("dragonchain.lib.dao.smart_contract_dao.add_smart_contract_index")
    @patch("dragonchain.webserver.lib.smart_contracts.job_processor.begin_task")
    @patch("dragonchain.webserver.lib.smart_contracts.transaction_type_dao.get_registered_transaction_type", side_effect=exceptions.NotFound)
    @patch("dragonchain.webserver.lib.smart_contracts.transaction_type_dao.register_smart_contract_transaction_type", side_effect=Exception)
    @patch("dragonchain.lib.database.redisearch.get_document_count", return_value=0)
    def test_create_contract_raises_on_uncaught_error(self, mock_get_count, mock_register_type, mock_get_type, mock_task, mock_add_index):
        self.assertRaises(Exception, smart_contracts.create_contract_v1, get_sc_create_body())

        mock_task.assert_called()
        mock_add_index.assert_called_once()
        mock_get_type.assert_called_once()
        mock_register_type.assert_called_once()

    @patch("dragonchain.lib.database.redisearch.get_document_count", return_value=0)
    def test_create_contract_validates_cron_string(self, mock_get_docs):
        self.assertRaises(exceptions.DragonchainException, smart_contracts.create_contract_v1, get_sc_create_body_with_bad_cron())

        mock_get_docs.assert_called_once()

    @patch("dragonchain.lib.dao.smart_contract_dao.add_smart_contract_index")
    @patch("dragonchain.webserver.lib.smart_contracts.transaction_type_dao.get_registered_transaction_type", side_effect=exceptions.NotFound)
    @patch("dragonchain.webserver.lib.smart_contracts.transaction_type_dao.register_smart_contract_transaction_type")
    @patch("dragonchain.lib.database.redisearch.get_document_count", return_value=0)
    @patch("dragonchain.job_processor.begin_task")
    def test_create_contract_with_custom_indexes(self, patch_job_proc, mock_get_count, mock_register_sc_type, mock_get_registered, mock_add_index):
        smart_contracts.create_contract_v1(get_sc_create_body_with_custom_indexes())

        mock_get_count.assert_called_once()
        mock_register_sc_type.assert_called_once()
        patch_job_proc.assert_called_once()
        mock_get_registered.assert_called_once()
        mock_add_index.assert_called_once()


class TestUpdateContract(unittest.TestCase):
    @patch("dragonchain.job_processor.begin_task")
    @patch("dragonchain.webserver.lib.smart_contracts.smart_contract_dao.get_contract_by_id", return_value=MagicMock(status={"state": "active"}))
    def test_update_contract(self, patch_get_by_id, patch_job_proc):
        smart_contracts.update_contract_v1("test", get_sc_update_body())

        patch_get_by_id.assert_called_once()
        patch_job_proc.assert_called_once()

    @patch("dragonchain.job_processor.begin_task", side_effect=RuntimeError)
    @patch("dragonchain.webserver.lib.smart_contracts.smart_contract_dao.get_contract_by_id", return_value=MagicMock(status={"state": "active"}))
    def test_update_contract_raises_and_resets_state_on_job_start_failure(self, patch_get_by_id, patch_job_proc):
        self.assertRaises(RuntimeError, smart_contracts.update_contract_v1, "test", get_sc_update_body())

        patch_get_by_id.return_value.set_state.assert_called_with(
            state=smart_contract_model.ContractState.ACTIVE, msg="Contract update failed: could not start update."
        )
        patch_get_by_id.return_value.save.assert_called()
        patch_get_by_id.assert_called_once()
        patch_job_proc.assert_called_once()

    @patch("dragonchain.webserver.lib.smart_contracts.smart_contract_dao.get_contract_by_id", side_effect=Exception)
    def test_update_contract_raises_ise_on_uncaught_error(self, patch_get_by_id):
        self.assertRaises(Exception, smart_contracts.update_contract_v1, "test", get_sc_update_body())
        patch_get_by_id.assert_called_once()


class TestDeleteContract(unittest.TestCase):
    @patch("dragonchain.job_processor.begin_task")
    @patch("dragonchain.webserver.lib.smart_contracts.smart_contract_dao.get_contract_by_id", return_value=MagicMock(status={"state": "active"}))
    def test_delete_contract(self, patch_get_by_id, patch_job_proc):
        smart_contracts.delete_contract_v1("test")

        patch_get_by_id.assert_called_once()
        patch_job_proc.assert_called_once()

    @patch("dragonchain.job_processor.begin_task", side_effect=RuntimeError)
    @patch("dragonchain.webserver.lib.smart_contracts.smart_contract_dao.get_contract_by_id", return_value=MagicMock(status={"state": "active"}))
    def test_delete_contract_raises_and_resets_state_on_job_start_failure(self, patch_get_by_id, patch_job_proc):
        self.assertRaises(RuntimeError, smart_contracts.delete_contract_v1, "test")

        patch_get_by_id.return_value.set_state.assert_called_with(
            state=smart_contract_model.ContractState.ACTIVE, msg="Contract delete failed: could not start deletion"
        )
        patch_get_by_id.return_value.save.assert_called()
        patch_get_by_id.assert_called_once()
        patch_job_proc.assert_called_once()

    @patch("dragonchain.webserver.lib.smart_contracts.smart_contract_dao.get_contract_by_id", side_effect=Exception)
    def test_delete_contract_raises_ise_on_uncaught_error(self, patch_get_by_id):
        self.assertRaises(Exception, smart_contracts.delete_contract_v1, "test")
        patch_get_by_id.assert_called_once()


class TestGetContractLogs(unittest.TestCase):
    @patch("dragonchain.webserver.lib.smart_contracts.get_by_id_v1")
    @patch("dragonchain.webserver.lib.smart_contracts.smart_contract_dao.get_contract_logs")
    def test_get_logs_calls_library_function(self, mock_get_logs, mock_get_contract):
        smart_contracts.get_logs_v1("test")
        mock_get_contract.assert_called_once_with("test")
        mock_get_logs.assert_called_once_with("test", None, None)

    @patch("dragonchain.webserver.lib.smart_contracts.get_by_id_v1")
    @patch("dragonchain.webserver.lib.smart_contracts.smart_contract_dao.get_contract_logs")
    def test_get_logs_calls_library_function_with_params(self, mock_get_logs, mock_get_contract):
        smart_contracts.get_logs_v1("test", "mytimestamp", 100)
        mock_get_contract.assert_called_once_with("test")
        mock_get_logs.assert_called_once_with("test", "mytimestamp", 100)

    @patch("dragonchain.webserver.lib.smart_contracts.get_by_id_v1", side_effect=exceptions.NotFound)
    @patch("dragonchain.webserver.lib.smart_contracts.smart_contract_dao.get_contract_logs")
    def test_get_logs_throws_not_found(self, mock_get_logs, mock_get_contract):
        self.assertRaises(exceptions.NotFound, smart_contracts.get_logs_v1, "test", "mytimestamp", 100)
        mock_get_contract.assert_called_once_with("test")
        mock_get_logs.assert_not_called()


class TestGetContract(unittest.TestCase):
    @patch("dragonchain.webserver.lib.smart_contracts.smart_contract_dao.get_contract_id_by_txn_type", return_value="test")
    def test_get_smart_contract_by_txn_type(self, mock_get_contract):
        ret_val = smart_contracts.get_id_by_txn_type_v1("banana")
        self.assertEqual(ret_val, "test")

    @patch("dragonchain.webserver.lib.smart_contracts.smart_contract_dao.get_contract_id_by_txn_type", side_effect=exceptions.NotFound)
    def test_get_smart_contract_by_txn_type_fails(self, mock_get_contract):
        self.assertRaises(exceptions.NotFound, smart_contracts.get_id_by_txn_type_v1, "banana")
        mock_get_contract.assert_called_once_with("banana")
