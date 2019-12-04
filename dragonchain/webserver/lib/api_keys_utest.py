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
from dragonchain import exceptions
from dragonchain.webserver.lib import api_keys


class TestApiKeyLib(unittest.TestCase):
    @patch(
        "dragonchain.webserver.lib.api_keys.api_key_dao.list_api_keys", return_value=[MagicMock(key_id="blah", registration_time=1234, nickname="")]
    )
    def test_get_api_key_list_calls_dao_correctly(self, mock_list_keys):
        response = api_keys.get_api_key_list_v1()["keys"]
        self.assertEqual(len(response), 1)
        self.assertEqual(response[0]["id"], "blah")
        self.assertEqual(response[0]["registration_time"], 1234)
        mock_list_keys.assert_called_once_with(include_interchain=False, include_system=False)

    @patch("dragonchain.webserver.lib.api_keys.api_key_model.new_from_scratch")
    @patch("dragonchain.webserver.lib.api_keys.api_key_dao.save_api_key")
    def test_create_api_key_calls_register_with_default_params(self, mock_save_key, mock_new_from_scratch):
        response = api_keys.create_api_key_v1()
        mock_new_from_scratch.assert_called_once_with(smart_contract=False, nickname="")
        mock_save_key.assert_called_once_with(mock_new_from_scratch.return_value)
        self.assertEqual(response["id"], mock_new_from_scratch.return_value.key_id)

    @patch("dragonchain.webserver.lib.api_keys.api_key_model.new_from_scratch")
    @patch("dragonchain.webserver.lib.api_keys.api_key_dao.save_api_key")
    def test_create_api_key_calls_register_with_correct_params(self, mock_save_key, mock_new_from_scratch):
        response = api_keys.create_api_key_v1(nickname="banana", permissions_document={"wind": "gone"})
        mock_new_from_scratch.assert_called_once_with(smart_contract=False, nickname="banana")
        mock_model = mock_new_from_scratch.return_value
        self.assertEqual(mock_model.permissions_document, {"wind": "gone"})
        mock_save_key.assert_called_once_with(mock_model)
        self.assertEqual(response["id"], mock_new_from_scratch.return_value.key_id)

    def test_delete_api_key_does_not_delete_sc_keys(self):
        self.assertRaises(exceptions.ActionForbidden, api_keys.delete_api_key_v1, "SC_key")

    @patch("dragonchain.webserver.lib.api_keys.secrets.get_dc_secret", return_value="root_id")
    def test_delete_api_key_does_not_delete_root_key(self, mock_get_secret):
        self.assertRaises(exceptions.ActionForbidden, api_keys.delete_api_key_v1, "root_id")

    @patch("dragonchain.webserver.lib.api_keys.secrets.get_dc_secret", return_value="root_id")
    @patch("dragonchain.webserver.lib.api_keys.api_key_dao.delete_api_key")
    def test_delete_api_key_calls_appropriately(self, mock_delete_api_key, mock_get_secret):
        api_keys.delete_api_key_v1("1")
        mock_delete_api_key.assert_called_once_with(key_id="1", interchain=False)

    def test_get_api_key_raises_not_found_when_sc_key(self):
        self.assertRaises(exceptions.NotFound, api_keys.get_api_key_v1, "SC_key")

    def test_get_api_key_raises_not_found_when_interchain_key(self):
        self.assertRaises(exceptions.NotFound, api_keys.get_api_key_v1, "INTERCHAIN/ic_key")

    def test_get_api_key_raises_not_found_when_web_key(self):
        self.assertRaises(exceptions.NotFound, api_keys.get_api_key_v1, "WEB_key")

    @patch("dragonchain.webserver.lib.api_keys.api_key_dao.get_api_key")
    def test_get_api_key_calls_appropriately(self, mock_get_key):
        response = api_keys.get_api_key_v1("id")
        mock_get_key.assert_called_once_with("id", interchain=False)
        self.assertEqual(response["id"], mock_get_key.return_value.key_id)
        self.assertEqual(response["registration_time"], mock_get_key.return_value.registration_time)

    def test_update_api_key_raises_forbidden_when_key_id_starts_with_reserved_sequence(self):
        self.assertRaises(exceptions.ActionForbidden, api_keys.update_api_key_v1, "SC_thing")
        self.assertRaises(exceptions.ActionForbidden, api_keys.update_api_key_v1, "WEB_thing")
        self.assertRaises(exceptions.ActionForbidden, api_keys.update_api_key_v1, "INTERCHAIN/whatever")

    @patch("dragonchain.webserver.lib.api_keys.api_key_dao.get_api_key")
    @patch("dragonchain.webserver.lib.api_keys.api_key_dao.save_api_key")
    def test_update_api_key_saves_with_defaults(self, mock_save_key, mock_get_key):
        api_keys.update_api_key_v1("some_id")
        mock_get_key.assert_called_once_with("some_id", interchain=False)
        mock_save_key.assert_called_once_with(mock_get_key.return_value)

    @patch("dragonchain.webserver.lib.api_keys.api_key_dao.get_api_key")
    @patch("dragonchain.webserver.lib.api_keys.api_key_dao.save_api_key")
    def test_update_api_key_saves_with_parameters(self, mock_save_key, mock_get_key):
        api_keys.update_api_key_v1("some_id", "nickname", {"definitely": "a permissions doc"})
        mock_get_key.assert_called_once_with("some_id", interchain=False)
        mock_retrieved_key = mock_get_key.return_value
        self.assertEqual(mock_retrieved_key.nickname, "nickname")
        self.assertEqual(mock_retrieved_key.permissions_document, {"definitely": "a permissions doc"})
        mock_save_key.assert_called_once_with(mock_retrieved_key)
