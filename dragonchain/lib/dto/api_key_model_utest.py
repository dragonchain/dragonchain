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

from dragonchain.lib.dto import api_key_model


def create_generic_api_key_model() -> api_key_model.APIKeyModel:
    return api_key_model.APIKeyModel(
        key="whatever",
        key_id="some_id",
        registration_time=0,
        nickname="",
        root=False,
        interchain=False,
        permissions_document={"version": "1", "default_allow": True, "permissions": {}},
    )


class TestApiKeyModel(unittest.TestCase):
    def test_gen_auth_key(self):
        auth_key = api_key_model.gen_auth_key()
        self.assertRegex(auth_key, r"[a-zA-Z0-9]{43}")

    def test_new_from_legacy_parses_old_normal_key_dto(self):
        old_dto = {"id": "some_id", "key": "some_key", "registration_time": 1234, "nickname": "banana"}
        model = api_key_model.new_from_legacy(old_dto, interchain_dcid="")
        self.assertEqual(model.key_id, old_dto["id"])
        self.assertEqual(model.key, old_dto["key"])
        self.assertEqual(model.registration_time, old_dto["registration_time"])
        self.assertEqual(model.nickname, old_dto["nickname"])
        self.assertFalse(model.root)
        self.assertFalse(model.interchain)
        self.assertEqual(model.permissions_document, api_key_model.DEFAULT_PERMISSIONS_DOCUMENT)

    def test_new_from_legacy_parses_old_root_key_dto(self):
        old_dto = {"id": "some_id", "key": "some_key", "root": True, "registration_time": 0}
        model = api_key_model.new_from_legacy(old_dto, interchain_dcid="")
        self.assertEqual(model.key_id, old_dto["id"])
        self.assertEqual(model.key, old_dto["key"])
        self.assertEqual(model.registration_time, old_dto["registration_time"])
        self.assertEqual(model.nickname, "")
        self.assertTrue(model.root)
        self.assertFalse(model.interchain)
        self.assertEqual(model.permissions_document, {"version": "1", "default_allow": True, "permissions": {}})

    def test_new_from_legacy_parses_old_interchain_key_dto(self):
        old_dto = {"key": "some_key", "registration_time": 1234}
        model = api_key_model.new_from_legacy(old_dto, interchain_dcid="banana")
        self.assertEqual(model.key_id, "banana")
        self.assertEqual(model.key, old_dto["key"])
        self.assertEqual(model.registration_time, old_dto["registration_time"])
        self.assertEqual(model.nickname, "")
        self.assertFalse(model.root)
        self.assertTrue(model.interchain)
        self.assertEqual(model.permissions_document, {"version": "1", "default_allow": False, "permissions": {}})

    def test_new_from_at_rest_parses_version_1_dto(self):
        v1_dto = {
            "version": "1",
            "key_id": "some_id",
            "key": "some_key",
            "registration_time": 1234,
            "root": False,
            "nickname": "banana",
            "interchain": True,
            "permissions_document": {},
        }
        model = api_key_model.new_from_at_rest(v1_dto)
        self.assertEqual(model.key_id, v1_dto["key_id"])
        self.assertEqual(model.key, v1_dto["key"])
        self.assertEqual(model.registration_time, v1_dto["registration_time"])
        self.assertEqual(model.nickname, v1_dto["nickname"])
        self.assertFalse(model.root)
        self.assertTrue(model.interchain)

    def test_new_from_at_rest_throws_with_bad_version(self):
        bad_version_dto = {"version": "bad"}
        self.assertRaises(NotImplementedError, api_key_model.new_from_at_rest, bad_version_dto)

    def test_new_root_key_sets_root_and_keys(self):
        model = api_key_model.new_root_key("key_id", "key")
        self.assertTrue(model.root)
        self.assertEqual(model.key_id, "key_id")
        self.assertEqual(model.key, "key")

    def test_new_from_scratch_generates_api_key_model_and_uses_default_permissions(self):
        model = api_key_model.new_from_scratch()
        self.assertIsInstance(model, api_key_model.APIKeyModel)
        self.assertEqual(model.permissions_document, api_key_model.DEFAULT_PERMISSIONS_DOCUMENT)

    def test_new_from_scratch_generates_sc_id_if_contract(self):
        model = api_key_model.new_from_scratch(smart_contract=True)
        self.assertTrue(model.key_id.startswith("SC_"))

    def test_new_from_scratch_uses_interchain_dcid_for_key_id(self):
        model = api_key_model.new_from_scratch(interchain_dcid="banana")
        self.assertEqual(model.key_id, "banana")
        self.assertTrue(model.interchain)
        # Also check that the correct permissions document was created
        self.assertEqual(model.permissions_document, {"version": "1", "default_allow": False, "permissions": {}})

    def test_new_from_scratch_raises_if_dcid_and_contract(self):
        self.assertRaises(RuntimeError, api_key_model.new_from_scratch, interchain_dcid="banana", smart_contract=True)

    def test_export_as_at_rest_returns_good_dto(self):
        model = api_key_model.APIKeyModel(
            key_id="some_id",
            key="some_key",
            registration_time=1234,
            root=False,
            nickname="Banana",
            interchain=False,
            permissions_document={"version": "1", "default_allow": True, "permissions": {}},
        )
        self.assertEqual(
            model.export_as_at_rest(),
            {
                "key": "some_key",
                "key_id": "some_id",
                "nickname": "Banana",
                "registration_time": 1234,
                "root": False,
                "interchain": False,
                "permissions_document": {"version": "1", "default_allow": True, "permissions": {}},
                "version": "1",
            },
        )

    @patch("dragonchain.lib.dto.api_key_model.APIKeyModel.is_key_allowed_v1")
    def test_root_key_is_allowed(self, is_key_allowed_v1):
        model = create_generic_api_key_model()
        model.root = True
        model.permissions_document["default_allow"] = False
        self.assertTrue(model.is_key_allowed("cool", "banana", "salad", interchain=False))
        is_key_allowed_v1.assert_not_called()

    @patch("dragonchain.lib.dto.api_key_model.APIKeyModel.is_key_allowed_v1")
    def test_permissions_doc_v1_is_allowed_uses_is_allowed_v1(self, is_key_allowed_v1):
        model = create_generic_api_key_model()
        model.permissions_document["default_allow"] = False
        self.assertEqual(model.is_key_allowed("cool", "banana", "salad", interchain=False), is_key_allowed_v1.return_value)

    def test_is_allowed_handles_interchain_keys(self):
        model = create_generic_api_key_model()
        model.interchain = True
        self.assertTrue(model.is_key_allowed("", "", "", interchain=True))
        self.assertFalse(model.is_key_allowed("", "", "", interchain=False))

    def test_bad_permission_document_version_raises(self):
        model = create_generic_api_key_model()
        model.permissions_document = {"version": "banana", "default_allow": False, "permissions": {}}
        self.assertRaises(RuntimeError, model.is_key_allowed, "cool", "banana", "salad", interchain=False)

    def test_is_allowed_v1_raises_error_on_bad_api_name(self):
        model = create_generic_api_key_model()
        self.assertRaises(RuntimeError, model.is_key_allowed_v1, "invalid", "api", "name")

    def test_is_allowed_v1_uses_default(self):
        model = create_generic_api_key_model()
        model.permissions_document["default_allow"] = True
        self.assertTrue(model.is_key_allowed_v1("api_keys", "create", "create_api_key"))

    def test_is_allowed_v1_global_crud_overrides_default(self):
        model = create_generic_api_key_model()
        model.permissions_document = {"version": "1", "default_allow": False, "permissions": {"allow_create": True}}
        self.assertTrue(model.is_key_allowed_v1("api_keys", "create", "create_api_key"))

    def test_is_allowed_v1_group_crud_overrides_global_crud(self):
        model = create_generic_api_key_model()
        model.permissions_document = {
            "version": "1",
            "default_allow": False,
            "permissions": {"allow_create": False, "api_keys": {"allow_create": True}},
        }
        self.assertTrue(model.is_key_allowed_v1("api_keys", "create", "create_api_key"))

    def test_is_allowed_v1_group_crud_ignored_when_no_matching_group_crud(self):
        model = create_generic_api_key_model()
        model.permissions_document = {
            "version": "1",
            "default_allow": False,
            "permissions": {"allow_create": True, "api_keys": {"something": "whatever"}},
        }
        self.assertTrue(model.is_key_allowed_v1("api_keys", "create", "create_api_key"))

    def test_is_allowed_v1_specific_api_name_overrides_group_crud(self):
        model = create_generic_api_key_model()
        model.permissions_document = {
            "version": "1",
            "default_allow": False,
            "permissions": {"allow_create": False, "api_keys": {"allow_create": False, "create_api_key": {"allowed": True}}},
        }
        self.assertTrue(model.is_key_allowed_v1("api_keys", "create", "create_api_key"))

    def test_is_allowed_v1_specific_group_ignored_when_no_matching_specific_group(self):
        model = create_generic_api_key_model()
        model.permissions_document = {
            "version": "1",
            "default_allow": False,
            "permissions": {"allow_create": False, "api_keys": {"allow_create": True, "create_api_key": {"irrelevant": "data"}}},
        }
        self.assertTrue(model.is_key_allowed_v1("api_keys", "create", "create_api_key"))

    def test_is_allowed_v1_raises_with_bad_action(self):
        model = create_generic_api_key_model()
        self.assertRaises(RuntimeError, model.is_key_allowed_v1, "api_keys", "not_an_action", "create_api_key")

    def test_is_allowed_v1_crud_reads_correct_fields(self):
        model = create_generic_api_key_model()
        model.permissions_document = {
            "version": "1",
            "default_allow": False,
            "permissions": {"allow_create": True, "allow_read": True, "allow_update": True, "allow_delete": True},
        }
        self.assertTrue(model.is_key_allowed_v1("api_keys", "create", "create_api_key"))
        self.assertTrue(model.is_key_allowed_v1("api_keys", "read", "get_api_key"))
        self.assertTrue(model.is_key_allowed_v1("api_keys", "update", "update_api_key"))
        self.assertTrue(model.is_key_allowed_v1("api_keys", "delete", "delete_api_key"))

    def test_check_create_transaction_permission_returns_true_with_no_extra_data(self):
        model = create_generic_api_key_model()
        model.permissions_document = {
            "version": "1",
            "default_allow": False,
            "permissions": {"transactions": {"create_transaction": {"not": "checked"}}},
        }
        self.assertTrue(model.is_key_allowed("transactions", "create", "create_transaction", False))

    def test_check_create_transaction_works_with_allowed_value_and_provided_extra_data(self):
        model = create_generic_api_key_model()
        model.permissions_document = {
            "version": "1",
            "default_allow": False,
            "permissions": {"transactions": {"create_transaction": {"allowed": True, "transaction_types": {"banana": False, "salad": True}}}},
        }
        # Check allowed true, specific type false
        self.assertFalse(model.is_key_allowed("transactions", "create", "create_transaction", False, {"requested_types": {"banana"}}))
        # Check allowed true, specific type true
        self.assertTrue(model.is_key_allowed("transactions", "create", "create_transaction", False, {"requested_types": {"salad"}}))
        # Check allowed true, no specific type
        self.assertTrue(model.is_key_allowed("transactions", "create", "create_transaction", False, {"requested_types": {"bacon"}}))
        # Check allowed true, specific type none and true
        self.assertTrue(model.is_key_allowed("transactions", "create", "create_transaction", False, {"requested_types": {"bacon", "salad"}}))
        # Check allowed true, specific type none and false
        self.assertFalse(model.is_key_allowed("transactions", "create", "create_transaction", False, {"requested_types": {"bacon", "banana"}}))
        # Check allowed true, specific type true and false
        self.assertFalse(model.is_key_allowed("transactions", "create", "create_transaction", False, {"requested_types": {"banana", "salad"}}))
        model.permissions_document["permissions"]["transactions"]["create_transaction"]["allowed"] = False
        # Check allowed false, specific type false
        self.assertFalse(model.is_key_allowed("transactions", "create", "create_transaction", False, {"requested_types": {"banana"}}))
        # Check allowed false, specific type true
        self.assertTrue(model.is_key_allowed("transactions", "create", "create_transaction", False, {"requested_types": {"salad"}}))
        # Check allowed false, no specific type
        self.assertFalse(model.is_key_allowed("transactions", "create", "create_transaction", False, {"requested_types": {"bacon"}}))
        # Check allowed true, specific type none and true
        self.assertFalse(model.is_key_allowed("transactions", "create", "create_transaction", False, {"requested_types": {"bacon", "salad"}}))
        # Check allowed true, specific type none and false
        self.assertFalse(model.is_key_allowed("transactions", "create", "create_transaction", False, {"requested_types": {"bacon", "banana"}}))
        # Check allowed true, specific type true and false
        self.assertFalse(model.is_key_allowed("transactions", "create", "create_transaction", False, {"requested_types": {"banana", "salad"}}))

    def test_check_create_transaction_defaults_if_no_allowed_set(self):
        model = create_generic_api_key_model()
        model.permissions_document = {
            "version": "1",
            "default_allow": False,
            "permissions": {"transactions": {"create_transaction": {"transaction_types": {"banana": False, "salad": True}}}},
        }
        self.assertFalse(model.is_key_allowed("transactions", "create", "create_transaction", False, {"requested_types": {"bacon"}}))
        model.permissions_document["default_allow"] = True
        self.assertTrue(model.is_key_allowed("transactions", "create", "create_transaction", False, {"requested_types": {"bacon"}}))
