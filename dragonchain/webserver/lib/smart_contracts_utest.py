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
from dragonchain.lib.dto import smart_contract_model
from dragonchain import exceptions
from dragonchain.webserver.lib import smart_contracts


def get_sc_create_body():
    return {"version": "3", "txn_type": "test", "image": "myreg/myrepo:mytag", "cmd": "echo", "args": ["hello", "world"], "execution_order": "serial"}


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
    @patch("dragonchain.webserver.lib.smart_contracts.transaction_type_dao.register_smart_contract_transaction_type")
    @patch("dragonchain.webserver.lib.smart_contracts.elasticsearch.get_count", return_value=0)
    @patch("dragonchain.job_processor.begin_task")
    def test_create_contract(self, patch_job_proc, mock_get_count, mock_register_sc_type):
        smart_contracts.create_contract_v1(get_sc_create_body())

        mock_register_sc_type.assert_called_once()
        patch_job_proc.assert_called_once()

    @patch("dragonchain.webserver.lib.smart_contracts.transaction_type_dao.register_smart_contract_transaction_type")
    @patch("dragonchain.webserver.lib.smart_contracts.transaction_type_dao.remove_existing_transaction_type")
    @patch("dragonchain.webserver.lib.smart_contracts.elasticsearch.get_count", return_value=0)
    @patch("dragonchain.job_processor.begin_task", side_effect=RuntimeError)
    def test_create_contract_deletes_txn_type_and_raises_on_job_start_failure(
        self, patch_job_proc, mock_get_count, mock_delete_type, mock_register_type
    ):
        self.assertRaises(RuntimeError, smart_contracts.create_contract_v1, get_sc_create_body())

        mock_delete_type.assert_called_once()
        mock_register_type.assert_called_once()
        patch_job_proc.assert_called_once()

    @patch("dragonchain.webserver.lib.smart_contracts.transaction_type_dao.register_smart_contract_transaction_type", side_effect=Exception)
    @patch("dragonchain.webserver.lib.smart_contracts.elasticsearch.get_count", return_value=0)
    def test_create_contract_raises_on_uncaught_error(self, mock_get_count, mock_register_type):
        self.assertRaises(Exception, smart_contracts.create_contract_v1, get_sc_create_body())

        mock_register_type.assert_called_once()

    @patch("dragonchain.webserver.lib.smart_contracts.elasticsearch.get_count", return_value=0)
    def test_create_contract_validates_cron_string(self, mock_get_count):
        self.assertRaises(exceptions.DragonchainException, smart_contracts.create_contract_v1, get_sc_create_body_with_bad_cron())

        mock_get_count.assert_called_once()


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


class TestQueryContracts(unittest.TestCase):
    @patch("dragonchain.webserver.lib.smart_contracts.elasticsearch.search", return_value={"whatever": "searchResponse"})
    def test_calls_search_when_query_string_params_pased(self, mock_search):
        smart_contracts.query_contracts_v1({"whatever": None})
        mock_search.assert_called_once()

    @patch("dragonchain.webserver.lib.smart_contracts.elasticsearch.search", return_value={"whatever": "searchResponse"})
    def test_calls_search_with_q_is_passed(self, mock_search):
        smart_contracts.query_contracts_v1({"q": "banana=true"})
        mock_search.assert_called_with(folder="SMARTCONTRACT", limit=None, offset=None, q="banana=true", sort=None)

    @patch("dragonchain.webserver.lib.smart_contracts.elasticsearch.search", return_value={"whatever": "searchResponse"})
    def test_calls_search_with_default_q_when_missing(self, mock_search):
        smart_contracts.query_contracts_v1({})
        mock_search.assert_called_with(folder="SMARTCONTRACT", q="*")

    @patch("dragonchain.webserver.lib.smart_contracts.elasticsearch.search", return_value={"whatever": "searchResponse"})
    def test_calls_search_with_sort_is_passed(self, mock_search):
        smart_contracts.query_contracts_v1({"sort": "desc"})
        mock_search.assert_called_with(folder="SMARTCONTRACT", limit=None, offset=None, q="*", sort="desc")
