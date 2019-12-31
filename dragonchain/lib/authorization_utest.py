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

    @patch("dragonchain.lib.authorization.redis.set_sync")
    def test_save_matchmaking_auth_key_calls_redis(self, mock_redis_set):
        self.assertTrue(authorization.save_matchmaking_auth_key("key"))
        mock_redis_set.assert_called_once_with("authorization:matchmaking", "key")

    @patch("dragonchain.lib.authorization.redis.set_sync", side_effect=Exception)
    def test_save_matchmaking_auth_returns_false_on_redis_error(self, mock_redis_set):
        self.assertFalse(authorization.save_matchmaking_auth_key("key"))

    @patch("dragonchain.lib.authorization.redis.get_sync", return_value="banana")
    def test_get_matchmaking_key_returns_from_redis(self, mock_redis_get):
        self.assertEqual(authorization.get_matchmaking_key(), "banana")
        mock_redis_get.assert_called_once_with("authorization:matchmaking")

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

    @patch("dragonchain.lib.authorization.api_key_dao.save_api_key")
    @patch("dragonchain.lib.authorization.api_key_model.new_from_scratch")
    @patch("dragonchain.lib.authorization.keys.get_public_id", return_value="test_dcid")
    @patch("dragonchain.lib.authorization.keys.get_my_keys", return_value=MagicMock(make_signature=MagicMock(return_value="sig")))
    @patch("dragonchain.lib.authorization.requests.post", return_value=MagicMock(status_code=201))
    @patch("dragonchain.lib.authorization.matchmaking.get_dragonchain_address", return_value="https://someurl")
    def test_register_interchain_key_with_remote_returns_valid(self, mock_get_address, mock_post, mock_keys, mock_dcid, mock_new_key, mock_save):
        remote_dcid = "remote"
        url = "https://someurl/v1/interchain-auth-register"
        expected_key = {"dcid": "test_dcid", "key": mock_new_key.return_value.key, "signature": "sig"}
        self.assertEqual(authorization.register_new_interchain_key_with_remote(remote_dcid), mock_new_key.return_value)
        mock_post.assert_called_with(url, json=expected_key, timeout=30)
        mock_save.assert_called_once_with(mock_new_key.return_value)

    @patch("dragonchain.lib.authorization.api_key_model.new_from_scratch")
    @patch("dragonchain.lib.keys.get_public_id", return_value="z7S3WADvnjCyFkUmL48cPGqrSHDrQghNxLFMwBEwwtMa")
    @patch("dragonchain.lib.authorization.keys.get_my_keys")
    @patch("dragonchain.lib.authorization.requests.post", return_value=MagicMock(status_code=100))
    @patch("dragonchain.lib.authorization.matchmaking.get_dragonchain_address", return_value="https://someurl")
    def test_register_interchain_key_raises_with_bad_status_code(self, mock_get_address, mock_post, mock_keys, mock_get_id, mock_new_key):
        self.assertRaises(RuntimeError, authorization.register_new_interchain_key_with_remote, "thing")

    @patch("dragonchain.lib.authorization.api_key_model.new_from_scratch")
    @patch("dragonchain.lib.keys.get_public_id", return_value="z7S3WADvnjCyFkUmL48cPGqrSHDrQghNxLFMwBEwwtMa")
    @patch("dragonchain.lib.authorization.keys.get_my_keys")
    @patch("dragonchain.lib.authorization.requests.post", side_effect=Exception)
    @patch("dragonchain.lib.authorization.matchmaking.get_dragonchain_address", return_value="https://someurl")
    def test_register_interchain_key_raises_with_bad_request_exception(self, mock_get_address, mock_post, mock_keys, mock_get_id, mock_new_key):
        self.assertRaises(RuntimeError, authorization.register_new_interchain_key_with_remote, "thing")

    @patch("dragonchain.lib.authorization.api_key_model.gen_auth_key", return_value="banana")
    @patch("dragonchain.lib.keys.get_public_id", return_value="z7S3WADvnjCyFkUmL48cPGqrSHDrQghNxLFMwBEwwtMa")
    @patch("dragonchain.lib.authorization.keys.get_my_keys", return_value=MagicMock(make_signature=MagicMock(return_value="signature")))
    @patch("dragonchain.lib.authorization.requests.post", return_value=MagicMock(status_code=201))
    @patch("dragonchain.lib.authorization.save_matchmaking_auth_key", return_value=True)
    def test_register_with_matchmaking_returns_valid(self, mock_save_key, mock_post, mock_get_keys, mock_get_id, mock_gen_key):
        self.assertEqual(authorization.register_new_key_with_matchmaking(), "banana")

    @patch("dragonchain.lib.authorization.api_key_model.gen_auth_key", return_value="banana")
    @patch("dragonchain.lib.keys.get_public_id", return_value="z7S3WADvnjCyFkUmL48cPGqrSHDrQghNxLFMwBEwwtMa")
    @patch("dragonchain.lib.authorization.keys.get_my_keys", return_value=MagicMock(make_signature=MagicMock(return_value="signature")))
    @patch("dragonchain.lib.authorization.requests.post", return_value=MagicMock(status_code=100))
    @patch("dragonchain.lib.authorization.save_matchmaking_auth_key", return_value=True)
    def test_register_with_matchmaking_raises_with_bad_status_code(self, mock_save_key, mock_post, mock_get_keys, mock_get_id, mock_gen_key):
        self.assertRaises(RuntimeError, authorization.register_new_key_with_matchmaking)

    @patch("dragonchain.lib.authorization.api_key_model.gen_auth_key", return_value="banana")
    @patch("dragonchain.lib.keys.get_public_id", return_value="z7S3WADvnjCyFkUmL48cPGqrSHDrQghNxLFMwBEwwtMa")
    @patch("dragonchain.lib.authorization.keys.get_my_keys", return_value=MagicMock(make_signature=MagicMock(return_value="signature")))
    @patch("dragonchain.lib.authorization.requests.post", side_effect=Exception)
    @patch("dragonchain.lib.authorization.save_matchmaking_auth_key", return_value=True)
    def test_register_with_matchmaking_raises_with_request_exception(self, mock_save_key, mock_post, mock_get_keys, mock_get_id, mock_gen_key):
        self.assertRaises(RuntimeError, authorization.register_new_key_with_matchmaking)

    @patch("dragonchain.lib.authorization.api_key_model.gen_auth_key", return_value="banana")
    @patch("dragonchain.lib.keys.get_public_id", return_value="z7S3WADvnjCyFkUmL48cPGqrSHDrQghNxLFMwBEwwtMa")
    @patch("dragonchain.lib.authorization.keys.get_my_keys", return_value=MagicMock(make_signature=MagicMock(return_value="signature")))
    @patch("dragonchain.lib.authorization.requests.post", return_value=MagicMock(status_code=200))
    @patch("dragonchain.lib.authorization.save_matchmaking_auth_key", return_value=False)
    def test_register_with_matchmaking_raises_with_bad_key_save(self, mock_save_key, mock_post, mock_get_keys, mock_get_id, mock_gen_key):
        self.assertRaises(RuntimeError, authorization.register_new_key_with_matchmaking)

    @patch("dragonchain.lib.authorization.keys.get_public_id", return_value="test_dcid")
    @patch("dragonchain.lib.authorization.register_new_interchain_key_with_remote", return_value=MagicMock(key="key"))
    @patch("dragonchain.lib.authorization.get_now_datetime", return_value=MagicMock(isoformat=MagicMock(return_value="timestamp")))
    @patch("dragonchain.lib.authorization.api_key_dao.get_api_key", side_effect=exceptions.NotFound)
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
    @patch("dragonchain.lib.authorization.api_key_dao.get_api_key", return_value=MagicMock(key="key", is_key_allowed=MagicMock(return_value=True)))
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
            "api_keys",
            "create",
            "create_api_key",
        )

    @patch("dragonchain.lib.authorization.RATE_LIMIT", 0)
    @patch("dragonchain.lib.authorization.keys.get_public_id", return_value="test_dcid")
    @patch("dragonchain.lib.authorization.signature_is_replay", return_value=False)
    @patch("dragonchain.lib.authorization.get_now_datetime", return_value=datetime.datetime(2018, 11, 14, 9, 5, 25, 128176))
    @patch("dragonchain.lib.authorization.api_key_dao.get_api_key", return_value=MagicMock(key="key", is_key_allowed=MagicMock(return_value=True)))
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
            "api_keys",
            "create",
            "create_api_key",
        )

    @patch("dragonchain.lib.authorization.RATE_LIMIT", 0)
    @patch("dragonchain.lib.authorization.keys.get_public_id", return_value="test_dcid")
    @patch("dragonchain.lib.authorization.signature_is_replay", return_value=False)
    @patch("dragonchain.lib.authorization.get_now_datetime", return_value=datetime.datetime(2018, 11, 14, 9, 5, 25, 128176))
    @patch("dragonchain.lib.authorization.api_key_dao.get_api_key", return_value=MagicMock(key="key", is_key_allowed=MagicMock(return_value=True)))
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
            "api_keys",
            "create",
            "create_api_key",
        )

    @patch("dragonchain.lib.authorization.RATE_LIMIT", 0)
    @patch("dragonchain.lib.authorization.keys.get_public_id", return_value="test_dcid")
    @patch("dragonchain.lib.authorization.signature_is_replay", return_value=False)
    @patch("dragonchain.lib.authorization.get_now_datetime", return_value=datetime.datetime(2018, 11, 14, 9, 5, 25, 128176))
    @patch("dragonchain.lib.authorization.api_key_dao.get_api_key", return_value=MagicMock(key="key", is_key_allowed=MagicMock(return_value=True)))
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
            "api_keys",
            "create",
            "create_api_key",
        )

    @patch("dragonchain.lib.authorization.RATE_LIMIT", 0)
    @patch("dragonchain.lib.authorization.keys.get_public_id", return_value="test_dcid")
    @patch("dragonchain.lib.authorization.signature_is_replay", return_value=False)
    @patch("dragonchain.lib.authorization.get_now_datetime", return_value=datetime.datetime(2018, 11, 14, 9, 5, 25, 128176))
    @patch("dragonchain.lib.authorization.api_key_dao.get_api_key", return_value=MagicMock(key="key", is_key_allowed=MagicMock(return_value=True)))
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
            "api_keys",
            "create",
            "create_api_key",
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
            "api_keys",
            "create",
            "create_api_key",
        )

    @patch("dragonchain.lib.authorization.RATE_LIMIT", 0)
    @patch("dragonchain.lib.authorization.keys.get_public_id", return_value="test_dcid")
    @patch("dragonchain.lib.authorization.signature_is_replay", return_value=False)
    @patch("dragonchain.lib.authorization.get_now_datetime", return_value=datetime.datetime(2018, 11, 14, 9, 5, 25, 128176))
    @patch("dragonchain.lib.authorization.api_key_dao.get_api_key", return_value=MagicMock(key="key", is_key_allowed=MagicMock(return_value=True)))
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
            "api_keys",
            "create",
            "create_api_key",
        )

    @patch("dragonchain.lib.authorization.RATE_LIMIT", 0)
    @patch("dragonchain.lib.authorization.keys.get_public_id", return_value="test_dcid")
    @patch("dragonchain.lib.authorization.signature_is_replay", return_value=False)
    @patch("dragonchain.lib.authorization.get_now_datetime", return_value=datetime.datetime(2018, 11, 14, 9, 5, 25, 128176))
    @patch("dragonchain.lib.authorization.api_key_dao.get_api_key", return_value=MagicMock(key="key", is_key_allowed=MagicMock(return_value=True)))
    def test_verify_req_auth_passes_when_valid(self, mock_get_auth_key, mock_date, mock_is_replay, mock_dcid):
        auth_str = "DC1-HMAC-SHA256 id:gr1FvIvTe1oOmFZqHgRQUhi6s/EyBvZmJWqH1oWV+UQ="
        http_verb = "GET"
        full_path = "/path"
        dcid = "test_dcid"
        timestamp = "2018-11-14T09:05:25.128176Z"
        # Test valid SHA256
        authorization.verify_request_authorization(
            auth_str, http_verb, full_path, dcid, timestamp, "", b"", False, "api_keys", "create", "create_api_key"
        )
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
            "api_keys",
            "create",
            "create_api_key",
        )
        # Test valid SHA3-256
        authorization.verify_request_authorization(
            "DC1-HMAC-SHA3-256 id:IjPhj3dzTyj0VhcI5oUl5vcFapX8/GpJaO5M82SD3dE=",
            http_verb,
            full_path,
            dcid,
            timestamp,
            "",
            b"",
            False,
            "api_keys",
            "create",
            "create_api_key",
        )

    @patch("dragonchain.lib.authorization.RATE_LIMIT", 0)
    @patch("dragonchain.lib.authorization.keys.get_public_id", return_value="test_dcid")
    @patch("dragonchain.lib.authorization.signature_is_replay", return_value=True)
    @patch("dragonchain.lib.authorization.get_now_datetime", return_value=datetime.datetime(2018, 11, 14, 9, 5, 25, 128176))
    @patch("dragonchain.lib.authorization.api_key_dao.get_api_key", return_value=MagicMock(key="key", is_key_allowed=MagicMock(return_value=True)))
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
            "api_keys",
            "create",
            "create_api_key",
        )

    @patch("dragonchain.lib.authorization.RATE_LIMIT", 0)
    @patch("dragonchain.lib.authorization.keys.get_public_id", return_value="test_dcid")
    @patch("dragonchain.lib.authorization.signature_is_replay", return_value=False)
    @patch("dragonchain.lib.authorization.get_now_datetime", return_value=datetime.datetime(2018, 11, 14, 9, 5, 25, 128176))
    @patch("dragonchain.lib.authorization.api_key_dao.get_api_key", return_value=MagicMock(key="key", is_key_allowed=MagicMock(return_value=False)))
    def test_verify_req_auth_raises_on_key_not_allowed(self, mock_get_auth_key, mock_date, mock_is_replay, mock_dcid):
        auth_str = "DC1-HMAC-SHA256 id:gr1FvIvTe1oOmFZqHgRQUhi6s/EyBvZmJWqH1oWV+UQ="
        http_verb = "GET"
        full_path = "/path"
        dcid = "test_dcid"
        timestamp = "2018-11-14T09:05:25.128176Z"
        self.assertRaisesWithMessage(
            exceptions.ActionForbidden,
            "This key is not allowed to perform create_api_key",
            authorization.verify_request_authorization,
            auth_str,
            http_verb,
            full_path,
            dcid,
            timestamp,
            "",
            b"",
            False,
            "api_keys",
            "create",
            "create_api_key",
        )

    @patch("dragonchain.lib.authorization.RATE_LIMIT", 0)
    @patch("dragonchain.lib.authorization.keys.get_public_id", return_value="test_dcid")
    @patch("dragonchain.lib.authorization.signature_is_replay", return_value=False)
    @patch("dragonchain.lib.authorization.get_now_datetime", return_value=datetime.datetime(2018, 11, 14, 9, 5, 25, 128176))
    @patch(
        "dragonchain.lib.authorization.api_key_dao.get_api_key", return_value=MagicMock(key="key", is_key_allowed=MagicMock(side_effect=Exception))
    )
    def test_verify_req_auth_raises_on_key_allowed_exception(self, mock_get_auth_key, mock_date, mock_is_replay, mock_dcid):
        auth_str = "DC1-HMAC-SHA256 id:gr1FvIvTe1oOmFZqHgRQUhi6s/EyBvZmJWqH1oWV+UQ="
        http_verb = "GET"
        full_path = "/path"
        dcid = "test_dcid"
        timestamp = "2018-11-14T09:05:25.128176Z"
        self.assertRaisesWithMessage(
            exceptions.ActionForbidden,
            "This key is not allowed to perform create_api_key",
            authorization.verify_request_authorization,
            auth_str,
            http_verb,
            full_path,
            dcid,
            timestamp,
            "",
            b"",
            False,
            "api_keys",
            "create",
            "create_api_key",
        )

    @patch("dragonchain.lib.authorization.RATE_LIMIT", 0)
    @patch("dragonchain.lib.authorization.keys.get_public_id", return_value="test_dcid")
    @patch("dragonchain.lib.authorization.signature_is_replay", return_value=False)
    @patch("dragonchain.lib.authorization.should_rate_limit", return_value=True)
    @patch("dragonchain.lib.authorization.get_now_datetime", return_value=datetime.datetime(2018, 11, 14, 9, 5, 25, 128176))
    @patch("dragonchain.lib.authorization.api_key_dao.get_api_key", return_value=MagicMock(key="key", is_key_allowed=MagicMock(return_value=True)))
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
            "api_keys",
            "create",
            "create_api_key",
        )

    @patch("dragonchain.lib.authorization.RATE_LIMIT", 0)
    @patch("dragonchain.lib.authorization.keys.get_public_id", return_value="test_dcid")
    @patch("dragonchain.lib.authorization.signature_is_replay", return_value=False)
    @patch("dragonchain.lib.authorization.get_now_datetime", return_value=datetime.datetime(2018, 11, 14, 9, 5, 25, 128176))
    @patch("dragonchain.lib.authorization.api_key_dao.get_api_key", side_effect=exceptions.NotFound)
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
            "api_keys",
            "create",
            "create_api_key",
        )

    @patch("dragonchain.lib.authorization.RATE_LIMIT", 0)
    @patch("dragonchain.lib.authorization.keys.get_public_id", return_value="test_dcid")
    @patch("dragonchain.lib.authorization.signature_is_replay", return_value=False)
    @patch("dragonchain.lib.authorization.get_now_datetime", return_value=datetime.datetime(2018, 11, 14, 9, 5, 25, 128176))
    @patch("dragonchain.lib.authorization.api_key_dao.get_api_key", side_effect=Exception)
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
            "api_keys",
            "create",
            "create_api_key",
        )

    @patch("dragonchain.lib.authorization.keys.get_public_id", return_value="test_dcid")
    @patch("dragonchain.lib.authorization.signature_is_replay", return_value=False)
    @patch("dragonchain.lib.authorization.get_now_datetime", return_value=datetime.datetime(2018, 11, 14, 9, 5, 25, 128176))
    @patch("dragonchain.lib.authorization.api_key_dao.get_api_key", return_value=MagicMock(key="key", is_key_allowed=MagicMock(return_value=True)))
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
        authorization.verify_request_authorization(
            auth_str, "POST", full_path, dcid, timestamp, "application/json", content, False, "api_keys", "create", "create_api_key"
        )
        headers, content = authorization.generate_authenticated_request("POST", dcid, full_path, json_content, "BLAKE2b512")
        auth_str = headers["Authorization"]
        # Test with BLAKE2b512 HMAC Auth
        authorization.verify_request_authorization(
            auth_str, "POST", full_path, dcid, timestamp, "application/json", content, False, "api_keys", "create", "create_api_key"
        )
        headers, content = authorization.generate_authenticated_request("POST", dcid, full_path, json_content, "SHA3-256")
        auth_str = headers["Authorization"]
        # Test with SHA3-256 HMAC Auth
        authorization.verify_request_authorization(
            auth_str, "POST", full_path, dcid, timestamp, "application/json", content, False, "api_keys", "create", "create_api_key"
        )

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
