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

from dragonchain.webserver.lib import dragonnet
from dragonchain import test_env  # noqa: F401


class TestDragonnet(unittest.TestCase):
    @patch("dragonchain.webserver.lib.dragonnet.VERIFICATION_NOTIFICATION", {"all": ["url1"]})
    @patch("dragonchain.webserver.lib.dragonnet.requests.post")
    @patch("dragonchain.webserver.lib.dragonnet.sign", return_value=("banana", "pubKey"))
    def test_calls_requests_when_all_is_set(self, mock_get_registration, mock_requests):
        fake_block_model = MagicMock(export_as_at_rest=MagicMock(return_value={"banana": True}))
        dragonnet.send_verification_notifications(2, fake_block_model)
        fake_block_model.export_as_at_rest.assert_called_once_with()
        mock_requests.assert_called_once_with(
            "url1", '{"banana": true}', headers={"Content-Type": "application/json", "Authorization": "Bearer banana", "DragonchainId": "pubKey"}
        )

    @patch("dragonchain.webserver.lib.dragonnet.VERIFICATION_NOTIFICATION", {"all": ["url1"], "l2": ["url1", "url2"]})
    @patch("dragonchain.webserver.lib.dragonnet.requests.post")
    @patch("dragonchain.webserver.lib.dragonnet.sign", return_value=("banana", "pubKey"))
    def test_uniquely_calls_requests_when_level_is_set(self, mock_get_registration, mock_requests):
        fake_block_model = MagicMock(export_as_at_rest=MagicMock(return_value={"banana": True}))
        dragonnet.send_verification_notifications(2, fake_block_model)
        fake_block_model.export_as_at_rest.assert_called_once_with()
        mock_requests.assert_any_call(
            "url1", '{"banana": true}', headers={"Content-Type": "application/json", "Authorization": "Bearer banana", "DragonchainId": "pubKey"}
        )
        mock_requests.assert_any_call(
            "url2", '{"banana": true}', headers={"Content-Type": "application/json", "Authorization": "Bearer banana", "DragonchainId": "pubKey"}
        )
