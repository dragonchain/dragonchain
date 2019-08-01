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

from dragonchain import test_env  # noqa: F401
from dragonchain import exceptions
from dragonchain.webserver.lib import api_keys


class TestApiKeyDAO(unittest.TestCase):
    @patch(
        "dragonchain.webserver.lib.api_keys.storage.get_json_from_object",
        return_value={"id": "blah", "registration_time": 1234, "key": "my_auth_key"},
    )
    @patch("dragonchain.webserver.lib.api_keys.storage.list_objects", return_value=["KEYS/SC_blah", "KEYS/INTERCHAIN/interchain-key", "KEYS/blah"])
    def test_get_api_key_list_removes_sc_keys(self, mock_list_objects, mock_get_object):
        response = api_keys.get_api_key_list_v1()["keys"]
        self.assertEqual(len(response), 1)
        self.assertEqual(response[0]["id"], "blah")
        self.assertEqual(response[0]["registration_time"], 1234)
        mock_get_object.assert_called_once()

    @patch("dragonchain.webserver.lib.api_keys.authorization.register_new_auth_key")
    def test_generate_api_key_calls_register_with_correct_params(self, mock_register_new_key):
        api_keys.create_api_key_v1(nickname="banana")
        mock_register_new_key.assert_called_once()

    def test_delete_api_key_does_not_delete_sc_keys(self):
        self.assertRaises(exceptions.ActionForbidden, api_keys.delete_api_key_v1, "SC_key")

    @patch("dragonchain.webserver.lib.api_keys.secrets.get_dc_secret", return_value="root_id")
    def test_delete_api_key_does_not_delete_root_key(self, mock_get_secret):
        self.assertRaises(exceptions.ActionForbidden, api_keys.delete_api_key_v1, "root_id")

    @patch("dragonchain.webserver.lib.api_keys.secrets.get_dc_secret", return_value="thing")
    @patch("dragonchain.webserver.lib.api_keys.authorization.remove_auth_key", return_value=False)
    def test_delete_api_raises_runtime_on_delete_failure(self, mock_remove_key, mock_get_secret):
        self.assertRaises(RuntimeError, api_keys.delete_api_key_v1, "whatever")

    @patch("dragonchain.webserver.lib.api_keys.secrets.get_dc_secret", return_value="thing")
    @patch("dragonchain.webserver.lib.api_keys.authorization.remove_auth_key", return_value=True)
    def test_calls_remove_auth_key_upon_key_removal(self, mock_remove_auth_key, mock_get_secret):
        api_keys.delete_api_key_v1("1")
        mock_remove_auth_key.assert_called_once_with(auth_key_id="1", interchain=False)

    def test_get_api_key_raises_not_found_when_sc_key(self):
        self.assertRaises(exceptions.NotFound, api_keys.get_api_key_v1, "SC_key")

    def test_get_api_key_raises_not_found_when_interchain_key(self):
        self.assertRaises(exceptions.NotFound, api_keys.get_api_key_v1, "INTERCHAIN/ic_key")

    def test_get_api_key_raises_not_found_when_web_key(self):
        self.assertRaises(exceptions.NotFound, api_keys.get_api_key_v1, "WEB_key")

    @patch(
        "dragonchain.webserver.lib.api_keys.storage.get_json_from_object",
        return_value={"id": "id", "key": "privateApiKey", "registration_time": 1100000},
    )
    def test_get_api_key_returns_registration_time(self, mock_get_object):
        response = api_keys.get_api_key_v1("id")
        mock_get_object.assert_called_once_with("KEYS/id")
        self.assertEqual(response["id"], "id")
        self.assertEqual(response["registration_time"], 1100000)
