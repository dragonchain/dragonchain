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

import json
import datetime
import unittest
from unittest.mock import patch, MagicMock

from dragonchain import test_env  # noqa: F401
from dragonchain.lib import authorization
from dragonchain import exceptions


class TestAuthorization(unittest.TestCase):
    def assertRaisesWithMessage(self, exception, msg, func, *args, **kwargs):  # noqa N802
        """
        Helper to assert a particular exception with a certain message is raised via our UserException
        """
        try:
            func(*args, **kwargs)
            self.assertFail()
        except exception as e:
            self.assertEqual(str(e), msg)

    def test_datetime(self):
        self.assertIsInstance(authorization.get_now_datetime(), datetime.datetime)

    def test_gen_auth_key(self):
        auth_key = authorization.gen_auth_key()
        self.assertRegex(auth_key, r"[a-zA-Z0-9]{43}")

    def test_gen_auth_key_id(self):
        auth_key_id = authorization.gen_auth_key_id()
        self.assertRegex(auth_key_id, r"[A-Z]{12}")
        auth_key_id = authorization.gen_auth_key_id(True)
        self.assertRegex(auth_key_id, r"SC_[A-Z]{12}")

    def test_get_hmac_string(self):
        http_verb = "TEST"
        full_path = "/somepath"
        dcid = "test_dcid"
        timestamp = "timestamp_str"
        content_type = "mimetype"
        content = b"some content"
        hmac_hash_type = "SHA256"
        hash_type = authorization.get_supported_hmac_hash(hmac_hash_type)

        hmac_str = authorization.get_hmac_message_string(http_verb, full_path, dcid, timestamp, content_type, content, hash_type)
        self.assertEqual(hmac_str, "TEST\n/somepath\ntest_dcid\ntimestamp_str\nmimetype\nKQ9JPET11j0Gs3TQpavSkvrji5LKsvrl7+/hsOk0f1Y=")

    @patch("dragonchain.lib.authorization.get_hmac_message_string", return_value="hmac_string")
    def test_get_authorization(self, mock_hmac_string):
        self.assertEqual(
            authorization.get_authorization("id", "key", "TEST", "/path", "dcid", "timestamp", "mimetype", b"content", "SHA256"),
            "DC1-HMAC-SHA256 id:G0ufeozs9/jOZCvIAkEfWhwCxx0NBDrvapnqdqShxWA=",
        )

    @patch("dragonchain.lib.authorization.storage.get_json_from_object", return_value={"key": "thing"})
    def test_get_auth_key(self, mock_storage):
        self.assertEqual(authorization.get_auth_key("test", False), "thing")
        mock_storage.assert_called_with("KEYS/test")

    @patch("dragonchain.lib.authorization.storage.get_json_from_object", return_value={"key": "thing"})
    def test_get_auth_key_interchain(self, mock_storage):
        self.assertEqual(authorization.get_auth_key("test", True), "thing")
        mock_storage.assert_called_with("KEYS/INTERCHAIN/test")

    @patch("dragonchain.lib.authorization.storage.get_json_from_object", side_effect=exceptions.NotFound)
    def test_get_auth_key_returns_none_on_not_found(self, mock_storage):
        self.assertIsNone(authorization.get_auth_key("test", False))

    @patch("dragonchain.lib.authorization.storage.get_json_from_object", return_value=None)
    def test_get_auth_key_returns_none_on_empty_storage_get(self, mock_storage):
        self.assertIsNone(authorization.get_auth_key("test", False))

    @patch("dragonchain.lib.authorization.storage.delete", return_value=True)
    def test_remove_auth_key(self, mock_storage):
        self.assertTrue(authorization.remove_auth_key("test"))
        mock_storage.assert_called_with("KEYS/test")

    @patch("dragonchain.lib.authorization.storage.delete", return_value=True)
    def test_remove_auth_key_interchain(self, mock_storage):
        self.assertTrue(authorization.remove_auth_key("test", True))
        mock_storage.assert_called_with("KEYS/INTERCHAIN/test")

    @patch("dragonchain.lib.authorization.storage.delete", return_value=True)
    def test_remove_auth_key_returns_false_on_error(self, mock_storage):
        mock_storage.side_effect = RuntimeError
        self.assertFalse(authorization.remove_auth_key("test"))

    @patch("dragonchain.lib.authorization.gen_auth_key", return_value="test_key")
    @patch("dragonchain.lib.authorization.gen_auth_key_id", return_value="test_key_id")
    @patch("dragonchain.lib.authorization.storage.put_object_as_json")
    @patch("dragonchain.lib.authorization.get_auth_key", return_value=False)
    def test_register_new_auth_key_with_valid_data(self, mock_get_auth_key, mock_storage, mock_gen_key_id, mock_gen_key):
        self.assertRaises(ValueError, authorization.register_new_auth_key, False, None, "id")
        result = authorization.register_new_auth_key()
        mock_storage.assert_called_with("KEYS/test_key_id", result)
        self.assertEqual(result["key"], "test_key")
        self.assertEqual(result["id"], "test_key_id")

    @patch("dragonchain.lib.authorization.storage.put_object_as_json")
    def test_register_new_auth_key_supplying_both_key_and_id(self, mock_storage):
        result = authorization.register_new_auth_key(auth_key="test", auth_key_id="yes")
        mock_storage.assert_called_with("KEYS/yes", result)
        self.assertEqual(result["key"], "test")
        self.assertEqual(result["id"], "yes")

    @patch("dragonchain.lib.authorization.storage.put_object_as_json")
    def test_register_new_interchain_key_returns_true_on_success(self, mock_storage):
        self.assertTrue(authorization.save_interchain_auth_key("test", "key"))
        mock_storage.assert_called_once()

    @patch("dragonchain.lib.authorization.storage.put_object_as_json", side_effect=Exception)
    def test_register_new_interchain_key_returns_false_on_error(self, mock_storage):
        self.assertFalse(authorization.save_interchain_auth_key("test", "key"))

    @patch("dragonchain.lib.authorization.keys.get_public_id", return_value="test_dcid")
    @patch("dragonchain.lib.authorization.keys.get_my_keys", return_value=MagicMock(make_signature=MagicMock(return_value="sig")))
    @patch("dragonchain.lib.authorization.save_interchain_auth_key", return_value=True)
    @patch("dragonchain.lib.authorization.requests.post", return_value=MagicMock(status_code=201))
    @patch("dragonchain.lib.authorization.gen_auth_key", return_value="key")
    @patch("dragonchain.lib.authorization.matchmaking.get_dragonchain_address", return_value="https://someurl")
    def test_register_interchain_key_with_remote_returns_valid(self, mock_get_address, mock_gen_auth, mock_post, mock_save, mock_keys, mock_dcid):
        remote_dcid = "remote"
        url = "https://someurl/v1/interchain-auth-register"
        expected_key = {"dcid": "test_dcid", "key": "key", "signature": "sig"}
        self.assertEqual(authorization.register_new_interchain_key_with_remote(remote_dcid), "key")
        mock_post.assert_called_with(url, json=expected_key, timeout=30)

    @patch("dragonchain.lib.authorization.keys.get_my_keys")
    @patch("dragonchain.lib.authorization.save_interchain_auth_key", return_value=True)
    @patch("dragonchain.lib.authorization.requests.post", return_value=MagicMock(status_code=100))
    @patch("dragonchain.lib.authorization.gen_auth_key", return_value="key")
    @patch("dragonchain.lib.authorization.matchmaking.get_dragonchain_address", return_value="https://someurl")
    def test_register_interchain_key_raises_with_bad_status_code(self, mock_get_address, mock_gen_auth, mock_post, mock_save, mock_keys):
        self.assertRaises(RuntimeError, authorization.register_new_interchain_key_with_remote, "thing")

    @patch("dragonchain.lib.authorization.keys.get_my_keys")
    @patch("dragonchain.lib.authorization.save_interchain_auth_key", return_value=False)
    @patch("dragonchain.lib.authorization.requests.post", return_value=MagicMock(status_code=201))
    @patch("dragonchain.lib.authorization.gen_auth_key", return_value="key")
    @patch("dragonchain.lib.authorization.matchmaking.get_dragonchain_address", return_value="https://someurl")
    def test_register_interchain_key_raises_with_failure_to_register_interchain_key(
        self, mock_get_address, mock_gen_auth, mock_post, mock_save, mock_keys
    ):
        self.assertRaises(RuntimeError, authorization.register_new_interchain_key_with_remote, "thing")

    @patch("dragonchain.lib.authorization.keys.get_public_id", return_value="test_dcid")
    @patch("dragonchain.lib.authorization.register_new_interchain_key_with_remote", return_value="key")
    @patch("dragonchain.lib.authorization.get_now_datetime", return_value=MagicMock(isoformat=MagicMock(return_value="timestamp")))
    @patch("dragonchain.lib.authorization.get_auth_key", return_value=None)
    def test_gen_interchain_request_dcid(self, mock_get_auth_key, date_mock, mock_register, mock_dcid):
        dcid = "adcid"
        full_path = "/path"
        json_content = {"thing": "test"}
        json_str = json.dumps(json_content, separators=(",", ":")).encode("utf-8")
        expected_headers = {
            "Content-Type": "application/json",
            "timestamp": "timestampZ",
            "dragonchain": dcid,
            "Authorization": "DC1-HMAC-SHA256 test_dcid:1oJseWBqbZokioWGWjb2jq1iq493MkgUyc3FkQND5XM=",
        }
        # Test valid SHA256
        headers, content = authorization.generate_authenticated_request("POST", dcid, full_path, json_content, "SHA256")
        self.assertEqual(content, json_str)
        self.assertDictEqual(headers, expected_headers)
        # Test valid BLAKE2b512
        headers, content = authorization.generate_authenticated_request("POST", dcid, full_path, json_content, "BLAKE2b512")
        expected_headers[
            "Authorization"
        ] = "DC1-HMAC-BLAKE2b512 test_dcid:JJiXbVuTjJ03/hNW8fZipw5DUiktO2lJSyml824eWS++mmilth7/BABgDYPvprAa99PHzFzYPA41iL45bI4p1w=="
        self.assertEqual(content, json_str)
        self.assertDictEqual(headers, expected_headers)
        # Test valid SHA3-256
        headers, content = authorization.generate_authenticated_request("POST", dcid, full_path, json_content, "SHA3-256")
        expected_headers["Authorization"] = "DC1-HMAC-SHA3-256 test_dcid:ANsT9nToNzhWbxtoank/oLMDZoish5tFVuhAMzF/obo="
        self.assertEqual(content, json_str)
        self.assertDictEqual(headers, expected_headers)

    @patch("dragonchain.lib.authorization.keys.get_public_id", return_value="test_dcid")
    @patch("dragonchain.lib.authorization.get_matchmaking_key", return_value=None)
    @patch("dragonchain.lib.authorization.register_new_key_with_matchmaking", return_value="key")
    @patch("dragonchain.lib.authorization.get_now_datetime", return_value=MagicMock(isoformat=MagicMock(return_value="timestamp")))
    def test_gen_interchain_request_matchmaking(self, date_mock, mock_register, mock_get, mock_dcid):
        full_path = "/path"
        json_content = {"thing": "test"}
        json_str = json.dumps(json_content, separators=(",", ":")).encode("utf-8")
        expected_headers = {
            "Content-Type": "application/json",
            "timestamp": "timestampZ",
            "Authorization": "DC1-HMAC-SHA256 test_dcid:ab+hEQC0NNJB7mHwpqsfQqEcOyolNOmDEQe9gvUZTYI=",
        }
        headers, content = authorization.generate_authenticated_request("POST", "matchmaking", full_path, json_content, "SHA256")
        self.assertEqual(content, json_str)
        self.assertDictEqual(headers, expected_headers)

    @patch("dragonchain.lib.authorization.redis.get_sync", return_value=True)
    def test_sig_replay_returns_true_with_existing_replay(self, mock_get_sync):
        self.assertTrue(authorization.signature_is_replay("thing"))

    @patch("dragonchain.lib.authorization.redis.get_sync", return_value=False)
    @patch("dragonchain.lib.authorization.redis.set_sync")
    def test_sig_replay_returns_false_when_valid(self, mock_set, mock_get):
        self.assertFalse(authorization.signature_is_replay("thing"))
        mock_set.assert_called_once()

    @patch("dragonchain.lib.authorization.RATE_LIMIT", 0)
    @patch("dragonchain.lib.authorization.keys.get_public_id", return_value="test_dcid")
    @patch("dragonchain.lib.authorization.signature_is_replay", return_value=False)
    @patch("dragonchain.lib.authorization.get_now_datetime", return_value=datetime.datetime(2018, 11, 14, 9, 5, 25, 128176))
    @patch("dragonchain.lib.authorization.get_auth_key", return_value="key")
    def test_verify_req_auth_raises_with_wrong_dc_id(self, mock_get_auth_key, mock_date, mock_is_replay, mock_dcid):
        auth_str = "DC1-HMAC-SHA256 id:gr1FvIvTe1oOmFZqHgRQUhi6s/EyBvZmJWqH1oWV+UQ="
        http_verb = "GET"
        full_path = "/path"
        timestamp = "2018-11-14T09:05:25.128176Z"
        self.assertRaisesWithMessage(
            exceptions.UnauthorizedException,
            "Incorrect Dragonchain ID",
            authorization.verify_request_authorization,
            auth_str,
            http_verb,
            full_path,
            "not_matching",
            timestamp,
            "",
            b"",
            False,
            False,
        )

    @patch("dragonchain.lib.authorization.RATE_LIMIT", 0)
    @patch("dragonchain.lib.authorization.keys.get_public_id", return_value="test_dcid")
    @patch("dragonchain.lib.authorization.signature_is_replay", return_value=False)
    @patch("dragonchain.lib.authorization.get_now_datetime", return_value=datetime.datetime(2018, 11, 14, 9, 5, 25, 128176))
    @patch("dragonchain.lib.authorization.get_auth_key", return_value="key")
    def test_verify_req_auth_raises_with_unsupported_auth_version(self, mock_get_auth_key, mock_date, mock_is_replay, mock_dcid):
        http_verb = "GET"
        full_path = "/path"
        dcid = "test_dcid"
        timestamp = "2018-11-14T09:05:25.128176Z"
        self.assertRaisesWithMessage(
            exceptions.UnauthorizedException,
            "Unsupported DC Authorization Version",
            authorization.verify_request_authorization,
            "DC9-HMAC",
            http_verb,
            full_path,
            dcid,
            timestamp,
            "",
            b"",
            False,
            False,
        )

    @patch("dragonchain.lib.authorization.RATE_LIMIT", 0)
    @patch("dragonchain.lib.authorization.keys.get_public_id", return_value="test_dcid")
    @patch("dragonchain.lib.authorization.signature_is_replay", return_value=False)
    @patch("dragonchain.lib.authorization.get_now_datetime", return_value=datetime.datetime(2018, 11, 14, 9, 5, 25, 128176))
    @patch("dragonchain.lib.authorization.get_auth_key", return_value="key")
    def test_verify_req_auth_raises_with_unsupported_hmac_hash(self, mock_get_auth_key, mock_date, mock_is_replay, mock_dcid):
        http_verb = "GET"
        full_path = "/path"
        dcid = "test_dcid"
        timestamp = "2018-11-14T09:05:25.128176Z"
        self.assertRaisesWithMessage(
            exceptions.UnauthorizedException,
            "Unsupported HMAC Hash Type",
            authorization.verify_request_authorization,
            "DC1-HMAC-INVALID thing",
            http_verb,
            full_path,
            dcid,
            timestamp,
            "",
            b"",
            False,
            False,
        )

    @patch("dragonchain.lib.authorization.RATE_LIMIT", 0)
    @patch("dragonchain.lib.authorization.keys.get_public_id", return_value="test_dcid")
    @patch("dragonchain.lib.authorization.signature_is_replay", return_value=False)
    @patch("dragonchain.lib.authorization.get_now_datetime", return_value=datetime.datetime(2018, 11, 14, 9, 5, 25, 128176))
    @patch("dragonchain.lib.authorization.get_auth_key", return_value="key")
    def test_verify_req_auth_raises_with_old_timestamp(self, mock_get_auth_key, mock_date, mock_is_replay, mock_dcid):
        auth_str = "DC1-HMAC-SHA256 id:gr1FvIvTe1oOmFZqHgRQUhi6s/EyBvZmJWqH1oWV+UQ="
        http_verb = "GET"
        full_path = "/path"
        dcid = "test_dcid"
        self.assertRaisesWithMessage(
            exceptions.UnauthorizedException,
            "Timestamp of request too skewed",
            authorization.verify_request_authorization,
            auth_str,
            http_verb,
            full_path,
            dcid,
            "2019-11-14T09:05:25Z",
            "",
            b"",
            False,
            False,
        )

    @patch("dragonchain.lib.authorization.RATE_LIMIT", 0)
    @patch("dragonchain.lib.authorization.keys.get_public_id", return_value="test_dcid")
    @patch("dragonchain.lib.authorization.signature_is_replay", return_value=False)
    @patch("dragonchain.lib.authorization.get_now_datetime", return_value=datetime.datetime(2018, 11, 14, 9, 5, 25, 128176))
    @patch("dragonchain.lib.authorization.get_auth_key", return_value="key")
    def test_verify_req_auth_raises_with_malformed_authorization(self, mock_get_auth_key, mock_date, mock_is_replay, mock_dcid):
        http_verb = "GET"
        full_path = "/path"
        dcid = "test_dcid"
        timestamp = "2018-11-14T09:05:25.128176Z"
        self.assertRaisesWithMessage(
            exceptions.UnauthorizedException,
            "Malformed Authorization Header",
            authorization.verify_request_authorization,
            "DC1-HMAC-SHA256 thing",
            http_verb,
            full_path,
            dcid,
            timestamp,
            "",
            b"",
            False,
            False,
        )
        self.assertRaisesWithMessage(
            exceptions.UnauthorizedException,
            "Malformed Authorization Header",
            authorization.verify_request_authorization,
            "bad_auth",
            http_verb,
            full_path,
            dcid,
            timestamp,
            "",
            b"",
            False,
            False,
        )

    @patch("dragonchain.lib.authorization.RATE_LIMIT", 0)
    @patch("dragonchain.lib.authorization.keys.get_public_id", return_value="test_dcid")
    @patch("dragonchain.lib.authorization.signature_is_replay", return_value=False)
    @patch("dragonchain.lib.authorization.get_now_datetime", return_value=datetime.datetime(2018, 11, 14, 9, 5, 25, 128176))
    @patch("dragonchain.lib.authorization.get_auth_key", return_value="key")
    def test_verify_req_auth_raises_with_invalid_hmac(self, mock_get_auth_key, mock_date, mock_is_replay, mock_dcid):
        http_verb = "GET"
        full_path = "/path"
        dcid = "test_dcid"
        timestamp = "2018-11-14T09:05:25.128176Z"
        self.assertRaisesWithMessage(
            exceptions.UnauthorizedException,
            "Invalid HMAC Authentication",
            authorization.verify_request_authorization,
            "DC1-HMAC-SHA256 id:badsignaturemFZqHgRQUhi6s/EyBvZmJWqH1oWV+UQ=",
            http_verb,
            full_path,
            dcid,
            timestamp,
            "",
            b"",
            False,
            False,
        )

    @patch("dragonchain.lib.authorization.RATE_LIMIT", 0)
    @patch("dragonchain.lib.authorization.keys.get_public_id", return_value="test_dcid")
    @patch("dragonchain.lib.authorization.signature_is_replay", return_value=False)
    @patch("dragonchain.lib.authorization.get_now_datetime", return_value=datetime.datetime(2018, 11, 14, 9, 5, 25, 128176))
    @patch("dragonchain.lib.authorization.get_auth_key", return_value="key")
    def test_verify_req_auth_passes_when_valid(self, mock_get_auth_key, mock_date, mock_is_replay, mock_dcid):
        auth_str = "DC1-HMAC-SHA256 id:gr1FvIvTe1oOmFZqHgRQUhi6s/EyBvZmJWqH1oWV+UQ="
        http_verb = "GET"
        full_path = "/path"
        dcid = "test_dcid"
        timestamp = "2018-11-14T09:05:25.128176Z"
        # Test valid SHA256
        authorization.verify_request_authorization(auth_str, http_verb, full_path, dcid, timestamp, "", b"", False, False)
        # Test valid BLAKE2b512
        authorization.verify_request_authorization(
            "DC1-HMAC-BLAKE2b512 id:x1PrKtbs51CR1X6/NTIxyjwOPmZF3rxIXdtJARDialRV+H3FbmUxLmqDuCQvPKEOLN9rNUFhsZa3QZVf8+kXkA==",
            http_verb,
            full_path,
            dcid,
            timestamp,
            "",
            b"",
            False,
            False,
        )
        # Test valid SHA3-256
        authorization.verify_request_authorization(
            "DC1-HMAC-SHA3-256 id:IjPhj3dzTyj0VhcI5oUl5vcFapX8/GpJaO5M82SD3dE=", http_verb, full_path, dcid, timestamp, "", b"", False, False
        )

    @patch("dragonchain.lib.authorization.RATE_LIMIT", 0)
    @patch("dragonchain.lib.authorization.keys.get_public_id", return_value="test_dcid")
    @patch("dragonchain.lib.authorization.signature_is_replay", return_value=True)
    @patch("dragonchain.lib.authorization.get_now_datetime", return_value=datetime.datetime(2018, 11, 14, 9, 5, 25, 128176))
    @patch("dragonchain.lib.authorization.get_auth_key", return_value="key")
    def test_verify_req_auth_raises_on_replay(self, mock_get_auth_key, mock_date, mock_is_replay, mock_dcid):
        auth_str = "DC1-HMAC-SHA256 id:gr1FvIvTe1oOmFZqHgRQUhi6s/EyBvZmJWqH1oWV+UQ="
        http_verb = "GET"
        full_path = "/path"
        dcid = "test_dcid"
        timestamp = "2018-11-14T09:05:25.128176Z"
        self.assertRaisesWithMessage(
            exceptions.UnauthorizedException,
            "Previous matching request found (no replays allowed)",
            authorization.verify_request_authorization,
            auth_str,
            http_verb,
            full_path,
            dcid,
            timestamp,
            "",
            b"",
            False,
            False,
        )

    @patch("dragonchain.lib.authorization.RATE_LIMIT", 0)
    @patch("dragonchain.lib.authorization.keys.get_public_id", return_value="test_dcid")
    @patch("dragonchain.lib.authorization.signature_is_replay", return_value=False)
    @patch("dragonchain.lib.authorization.should_rate_limit", return_value=True)
    @patch("dragonchain.lib.authorization.get_now_datetime", return_value=datetime.datetime(2018, 11, 14, 9, 5, 25, 128176))
    @patch("dragonchain.lib.authorization.get_auth_key", return_value="key")
    def test_verify_req_auth_raises_with_rate_limit(self, mock_get_auth_key, mock_date, mock_should_limit, mock_is_replay, mock_dcid):
        auth_str = "DC1-HMAC-SHA256 id:gr1FvIvTe1oOmFZqHgRQUhi6s/EyBvZmJWqH1oWV+UQ="
        http_verb = "GET"
        full_path = "/path"
        dcid = "test_dcid"
        timestamp = "2018-11-14T09:05:25.128176Z"
        self.assertRaisesWithMessage(
            exceptions.APIRateLimitException,
            f"API Rate Limit Exceeded. {authorization.RATE_LIMIT} requests allowed per minute.",
            authorization.verify_request_authorization,
            auth_str,
            http_verb,
            full_path,
            dcid,
            timestamp,
            "",
            b"",
            False,
            False,
        )

    @patch("dragonchain.lib.authorization.RATE_LIMIT", 0)
    @patch("dragonchain.lib.authorization.keys.get_public_id", return_value="test_dcid")
    @patch("dragonchain.lib.authorization.signature_is_replay", return_value=False)
    @patch("dragonchain.lib.authorization.get_now_datetime", return_value=datetime.datetime(2018, 11, 14, 9, 5, 25, 128176))
    @patch("dragonchain.lib.authorization.get_auth_key", return_value=None)
    def test_verify_req_auth_raises_with_no_key(self, mock_get_auth_key, mock_date, mock_is_replay, mock_dcid):
        auth_str = "DC1-HMAC-SHA256 id:gr1FvIvTe1oOmFZqHgRQUhi6s/EyBvZmJWqH1oWV+UQ="
        http_verb = "GET"
        full_path = "/path"
        dcid = "test_dcid"
        timestamp = "2018-11-14T09:05:25.128176Z"
        self.assertRaisesWithMessage(
            exceptions.UnauthorizedException,
            "Invalid HMAC Authentication",
            authorization.verify_request_authorization,
            auth_str,
            http_verb,
            full_path,
            dcid,
            timestamp,
            "",
            b"",
            False,
            False,
        )

    @patch("dragonchain.lib.authorization.RATE_LIMIT", 0)
    @patch("dragonchain.lib.authorization.keys.get_public_id", return_value="test_dcid")
    @patch("dragonchain.lib.authorization.signature_is_replay", return_value=False)
    @patch("dragonchain.lib.authorization.get_now_datetime", return_value=datetime.datetime(2018, 11, 14, 9, 5, 25, 128176))
    @patch("dragonchain.lib.authorization.get_auth_key", side_effect=Exception)
    def test_verify_req_auth_raises_on_get_key_error(self, mock_get_auth_key, mock_date, mock_is_replay, mock_dcid):
        auth_str = "DC1-HMAC-SHA256 id:gr1FvIvTe1oOmFZqHgRQUhi6s/EyBvZmJWqH1oWV+UQ="
        http_verb = "GET"
        full_path = "/path"
        dcid = "test_dcid"
        timestamp = "2018-11-14T09:05:25.128176Z"
        self.assertRaisesWithMessage(
            exceptions.UnauthorizedException,
            "Invalid HMAC Format",
            authorization.verify_request_authorization,
            auth_str,
            http_verb,
            full_path,
            dcid,
            timestamp,
            "",
            b"",
            False,
            False,
        )

    @patch("dragonchain.lib.authorization.keys.get_public_id", return_value="test_dcid")
    @patch("dragonchain.lib.authorization.signature_is_replay", return_value=False)
    @patch("dragonchain.lib.authorization.get_now_datetime", return_value=datetime.datetime(2018, 11, 14, 9, 5, 25, 128176))
    @patch("dragonchain.lib.authorization.get_auth_key", return_value="key")
    def test_generated_authenticated_request_with_verifier(self, mock_get_auth_key, mock_date, mock_is_replay, mock_get_id):
        """
        This is more of psuedo integration test, ensuring that
        the generate_authenticated_request 'POST', will generate things are properly
        validated by verify_request_authorization

        If this test ever fails, it means that interchain communication will be broken
        even if all other tests pass
        """
        full_path = "/path"
        dcid = "test_dcid"
        timestamp = "2018-11-14T09:05:25.128176Z"
        json_content = {"thing": "test"}
        headers, content = authorization.generate_authenticated_request("POST", dcid, full_path, json_content, "SHA256")
        auth_str = headers["Authorization"]
        # Test with SHA256 HMAC Auth
        authorization.verify_request_authorization(auth_str, "POST", full_path, dcid, timestamp, "application/json", content, False, False)
        headers, content = authorization.generate_authenticated_request("POST", dcid, full_path, json_content, "BLAKE2b512")
        auth_str = headers["Authorization"]
        # Test with BLAKE2b512 HMAC Auth
        authorization.verify_request_authorization(auth_str, "POST", full_path, dcid, timestamp, "application/json", content, False, False)
        headers, content = authorization.generate_authenticated_request("POST", dcid, full_path, json_content, "SHA3-256")
        auth_str = headers["Authorization"]
        # Test with SHA3-256 HMAC Auth
        authorization.verify_request_authorization(auth_str, "POST", full_path, dcid, timestamp, "application/json", content, False, False)

    @patch("dragonchain.lib.authorization.RATE_LIMIT", 0)
    @patch("dragonchain.lib.authorization.redis.lindex_sync")
    def test_should_rate_limit_disabled_on_0(self, mock_lindex):
        self.assertFalse(authorization.should_rate_limit("test"))
        mock_lindex.assert_not_called()

    @patch("dragonchain.lib.authorization.RATE_LIMIT", 1)
    @patch("dragonchain.lib.authorization.redis.lindex_sync")
    @patch("dragonchain.lib.authorization.redis.ltrim_sync")
    @patch("dragonchain.lib.authorization.redis.lpush_sync")
    @patch("dragonchain.lib.authorization.time.time", return_value=1554249099.7634845)
    def test_should_rate_limit_calls_lpush_when_returning_false(self, mock_time, mock_lpush, mock_ltrim, mock_lindex):
        self.assertFalse(authorization.should_rate_limit("test"))
        mock_lpush.assert_called_once_with("request:test", "1554249099.7634845")

    @patch("dragonchain.lib.authorization.RATE_LIMIT", 2)
    @patch("dragonchain.lib.authorization.redis.lindex_sync")
    @patch("dragonchain.lib.authorization.redis.lpush_sync")
    @patch("dragonchain.lib.authorization.random.randint", return_value=0)
    @patch("dragonchain.lib.authorization.redis.ltrim_sync")
    def test_should_rate_limit_calls_ltrim(self, mock_ltrim, mock_rand, mock_lpush, mock_lindex):
        authorization.should_rate_limit("test")
        mock_ltrim.assert_called_once_with("request:test", 0, 1)

    @patch("dragonchain.lib.authorization.RATE_LIMIT", 2)
    @patch("dragonchain.lib.authorization.redis.lpush_sync")
    @patch("dragonchain.lib.authorization.redis.ltrim_sync")
    @patch("dragonchain.lib.authorization.redis.lindex_sync")
    def test_should_rate_limit_calls_lindex(self, mock_lindex, mock_ltrim, mock_lpush):
        authorization.should_rate_limit("test")
        mock_lindex.assert_called_once_with("request:test", 1, decode=False)

    @patch("dragonchain.lib.authorization.RATE_LIMIT", 2)
    @patch("dragonchain.lib.authorization.redis.lindex_sync", return_value=b"1554249095.7634845")
    @patch("dragonchain.lib.authorization.redis.ltrim_sync")
    @patch("dragonchain.lib.authorization.time.time", return_value=1554249099.7634845)
    def test_should_rate_limit_returns_true_when_limited(self, mock_time, mock_ltrim, mock_lindex):
        self.assertTrue(authorization.should_rate_limit("test"))
