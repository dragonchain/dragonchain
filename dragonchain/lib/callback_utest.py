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
from dragonchain.lib.callback import register_callback, fire_if_exists

fake_redis = MagicMock()
fake_session = MagicMock()


class TestCallback(unittest.TestCase):
    @patch("dragonchain.lib.callback.redis.hset_sync")
    def test_register_if_callback_url_is_not_none(self, mock_hset):
        register_callback("banana", "NotNone")
        mock_hset.assert_called_once_with("dc:tx:callback", "banana", "NotNone")

    @patch("dragonchain.lib.callback.redis.hget_sync", return_value=None)
    @patch("dragonchain.lib.callback.redis.hdel_sync")
    def test_fire_if_exists_no_op_when_no_trigger_exists(self, mock_hdel, mock_hget):
        fake_txn_model = MagicMock()
        fire_if_exists("fakeTxnId", fake_txn_model)
        mock_hdel.assert_not_called()

    @patch("dragonchain.lib.callback.redis.hget_sync", return_value="ExistingTriggerUrl")
    @patch("dragonchain.lib.callback.redis.hdel_sync")
    @patch("requests.Session", return_value=fake_session)
    def test_fire_if_exists_when_trigger_exists(self, whatev, mock_hget, mock_hdel):
        fake_txn_model = MagicMock()
        fire_if_exists("fakeTxnId", fake_txn_model)
        fake_session.__enter__().post.assert_called_with("ExistingTriggerUrl", json=fake_txn_model.export_as_full(), timeout=10)

    @patch("dragonchain.lib.callback.redis.hget_sync", return_value="ExistingTriggerUrl")
    @patch("dragonchain.lib.callback.redis.hdel_sync")
    @patch("requests.Session", side_effect=Exception)
    def test_fire_if_exists_when_exception_is_thrown(self, whatev, mock_hget, mock_hdel):
        fake_txn_model = MagicMock()
        fire_if_exists("fakeTxnId", fake_txn_model)
        fake_session.post.assert_not_called()

    @patch("dragonchain.lib.callback.redis.hdel_sync")
    @patch("dragonchain.lib.callback.redis.hget_sync", return_value="ExistingTriggerUrl")
    @patch("requests.Session", side_effect=Exception)
    def test_fire_if_exists_calls_hdel_no_matter_what(self, whatev, mock_get, mock_hdel):
        fake_txn_model = MagicMock()
        fire_if_exists("fakeTxnId", fake_txn_model)
        mock_hdel.assert_called_with("dc:tx:callback", "fakeTxnId")
