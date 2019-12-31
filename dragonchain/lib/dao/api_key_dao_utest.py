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
from unittest.mock import patch, call, MagicMock

from dragonchain import test_env  # noqa: F401
from dragonchain.lib.dao import api_key_dao
from dragonchain import exceptions


class TestApiKeyDAO(unittest.TestCase):
    @patch(
        "dragonchain.lib.dao.api_key_dao.storage.get_json_from_object",
        return_value={
            "key_id": "blah",
            "registration_time": 1234,
            "key": "my_auth_key",
            "version": "1",
            "permissions_document": {"version": "1", "default_allow": True, "permissions": {}},
            "interchain": False,
            "root": False,
            "nickname": "",
        },
    )
    @patch("dragonchain.lib.dao.api_key_dao.storage.list_objects", return_value=["KEYS/INTERCHAIN/blah", "KEYS/blah"])
    def test_list_api_keys_removes_interchain_keys(self, mock_list_objects, mock_get_object):
        response = api_key_dao.list_api_keys(include_interchain=False)
        self.assertEqual(len(response), 1)
        self.assertEqual(response[0].key_id, "blah")
        self.assertEqual(response[0].registration_time, 1234)
        mock_get_object.assert_called_once()

    @patch(
        "dragonchain.lib.dao.api_key_dao.storage.get_json_from_object",
        return_value={
            "key_id": "blah",
            "registration_time": 1234,
            "key": "my_auth_key",
            "version": "1",
            "permissions_document": {"version": "1", "default_allow": True, "permissions": {}},
            "interchain": True,
            "root": False,
            "nickname": "",
        },
    )
    @patch("dragonchain.lib.dao.api_key_dao.storage.list_objects", return_value=["KEYS/INTERCHAIN/blah"])
    def test_list_api_keys_include_interchain_keys(self, mock_list_objects, mock_get_object):
        response = api_key_dao.list_api_keys(include_interchain=True)
        self.assertEqual(len(response), 1)
        self.assertEqual(response[0].key_id, "blah")
        self.assertEqual(response[0].registration_time, 1234)
        mock_get_object.assert_called_once()

    @patch("dragonchain.lib.dao.api_key_dao.storage.put_object_as_json")
    def test_save_api_key_calls_storage_correctly(self, mock_save):
        fake_api_key = MagicMock()
        fake_api_key.export_as_at_rest.return_value = {"thing": "yup"}
        fake_api_key.interchain = False
        fake_api_key.key_id = "someid"
        api_key_dao.save_api_key(fake_api_key)
        fake_api_key.export_as_at_rest.assert_called_once()
        mock_save.assert_called_once_with("KEYS/someid", fake_api_key.export_as_at_rest.return_value)

    @patch(
        "dragonchain.lib.dao.api_key_dao.storage.get_json_from_object",
        return_value={
            "key_id": "blah",
            "registration_time": 1234,
            "key": "my_auth_key",
            "version": "1",
            "permissions_document": {"version": "1", "default_allow": True, "permissions": {}},
            "interchain": True,
            "root": False,
            "nickname": "",
        },
    )
    def test_get_api_key_gets_from_storage_correctly(self, mock_get_object):
        api_key_dao.get_api_key("some_id", interchain=True)
        mock_get_object.return_value = {  # Set interchain value now to false or else error will be thrown
            "key_id": "blah",
            "registration_time": 1234,
            "key": "my_auth_key",
            "version": "1",
            "permissions_document": {"version": "1", "default_allow": True, "permissions": {}},
            "interchain": False,
            "root": False,
            "nickname": "",
        }
        returned_key = api_key_dao.get_api_key("some_id", interchain=False)
        self.assertEqual(returned_key.key_id, "blah")
        mock_get_object.assert_has_calls([call("KEYS/INTERCHAIN/some_id"), call("KEYS/some_id")])

    @patch(
        "dragonchain.lib.dao.api_key_dao.storage.get_json_from_object",
        return_value={
            "key_id": "blah",
            "registration_time": 1234,
            "key": "my_auth_key",
            "version": "1",
            "permissions_document": {"version": "1", "default_allow": True, "permissions": {}},
            "interchain": False,
            "root": False,
            "nickname": "",
        },
    )
    def test_get_api_key_raises_error_when_mismatching_interchain(self, mock_get_object):
        self.assertRaises(RuntimeError, api_key_dao.get_api_key, "some_id", interchain=True)

    @patch("dragonchain.lib.dao.api_key_dao.storage.get_json_from_object")
    def test_get_api_key_raises_not_found_when_slash_in_key_id(self, mock_get_object):
        self.assertRaises(exceptions.NotFound, api_key_dao.get_api_key, "some/malicious/key", interchain=False)
        mock_get_object.assert_not_called()

    @patch("dragonchain.lib.dao.api_key_dao.storage.delete")
    def test_delete_api_key_deletes_from_storage_correctly(self, mock_delete):
        api_key_dao.delete_api_key("interchain", interchain=True)
        api_key_dao.delete_api_key("notinterchain", interchain=False)
        mock_delete.assert_has_calls([call("KEYS/INTERCHAIN/interchain"), call("KEYS/notinterchain")])

    def test_delete_api_key_throws_error_if_deleting_interchain_key_when_not_intended(self):
        self.assertRaises(RuntimeError, api_key_dao.delete_api_key, "INTERCHAIN/malicious", False)

    @patch("dragonchain.lib.dao.api_key_dao.storage.list_objects")
    @patch("dragonchain.lib.dao.api_key_dao.storage.get", return_value=b"1")
    def test_perform_api_key_migration_doesnt_do_anything_when_already_migrated(self, mock_get, mock_list):
        api_key_dao.perform_api_key_migration_v1_if_necessary()
        mock_get.assert_called_once_with("KEYS/MIGRATION_V1_COMPLETE")
        mock_list.assert_not_called()

    @patch("dragonchain.lib.dao.api_key_dao.api_key_model.new_from_legacy", return_value="banana")
    @patch("dragonchain.lib.dao.api_key_dao.save_api_key")
    @patch(
        "dragonchain.lib.dao.api_key_dao.storage.get_json_from_object",
        return_value={"id": "some_id", "key": "some_key", "registration_time": 1234, "nickname": "banana"},
    )
    @patch("dragonchain.lib.dao.api_key_dao.storage.put")
    @patch("dragonchain.lib.dao.api_key_dao.storage.list_objects", return_value=["KEYS/whatever"])
    @patch("dragonchain.lib.dao.api_key_dao.storage.get", side_effect=exceptions.NotFound)
    def test_perform_api_key_migration_migrates_regular_keys(
        self, mock_get, mock_list, mock_put, mock_get_object, mock_save_key, mock_new_from_legacy
    ):
        api_key_dao.perform_api_key_migration_v1_if_necessary()
        mock_new_from_legacy.assert_called_once_with(
            {"id": "some_id", "key": "some_key", "registration_time": 1234, "nickname": "banana"}, interchain_dcid=""
        )
        mock_save_key.assert_called_once_with("banana")

    @patch("dragonchain.lib.dao.api_key_dao.api_key_model.new_from_legacy", return_value="banana")
    @patch("dragonchain.lib.dao.api_key_dao.save_api_key")
    @patch("dragonchain.lib.dao.api_key_dao.storage.get_json_from_object", return_value={"key": "some_key", "registration_time": 1234})
    @patch("dragonchain.lib.dao.api_key_dao.storage.put")
    @patch("dragonchain.lib.dao.api_key_dao.storage.list_objects", return_value=["KEYS/INTERCHAIN/whatever"])
    @patch("dragonchain.lib.dao.api_key_dao.storage.get", side_effect=exceptions.NotFound)
    def test_perform_api_key_migration_migrates_interchain_keys(
        self, mock_get, mock_list, mock_put, mock_get_object, mock_save_key, mock_new_from_legacy
    ):
        api_key_dao.perform_api_key_migration_v1_if_necessary()
        mock_new_from_legacy.assert_called_once_with({"key": "some_key", "registration_time": 1234}, interchain_dcid="whatever")
        mock_save_key.assert_called_once_with("banana")

    @patch("dragonchain.lib.dao.api_key_dao.storage.put")
    @patch("dragonchain.lib.dao.api_key_dao.storage.list_objects", return_value=[])
    @patch("dragonchain.lib.dao.api_key_dao.storage.get", return_value=b"not1")
    def test_perform_api_key_migration_saves_migration_marker_when_complete(self, mock_storage_get, mock_storage_list, mock_storage_put):
        api_key_dao.perform_api_key_migration_v1_if_necessary()
        mock_storage_put.assert_called_once_with("KEYS/MIGRATION_V1_COMPLETE", b"1")
