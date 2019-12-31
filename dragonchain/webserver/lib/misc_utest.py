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

import os
import unittest
from unittest.mock import patch

from dragonchain import test_env  # noqa: F401
from dragonchain.webserver.lib import misc


class TestMisc(unittest.TestCase):
    @patch("dragonchain.lib.keys.get_public_id")
    @patch("dragonchain.lib.matchmaking.get_matchmaking_config")
    def test_get_status_retrieves_matchmaking_data_and_id(self, mock_matchmaking, mock_get_id):
        misc.get_v1_status()
        mock_matchmaking.assert_called_once()
        mock_get_id.assert_called_once()

    @patch("dragonchain.lib.keys.get_public_id")
    @patch("dragonchain.lib.matchmaking.get_matchmaking_config")
    def test_get_status_returns_expected_dto_l1(self, mock_matchmaking, mock_get_id):
        mock_matchmaking.return_value = {"level": "1", "url": "abc", "hashAlgo": "bcd", "scheme": "yup", "version": "1.2.3", "encryptionAlgo": "algo"}
        mock_get_id.return_value = "my_id"
        self.assertEqual(
            misc.get_v1_status(),
            {
                "id": "my_id",
                "level": 1,
                "url": "abc",
                "hashAlgo": "bcd",
                "scheme": "yup",
                "version": "1.2.3",
                "encryptionAlgo": "algo",
                "indexingEnabled": True,
            },
        )

    @patch("dragonchain.lib.keys.get_public_id")
    @patch("dragonchain.lib.matchmaking.get_matchmaking_config")
    def test_get_status_returns_expected_dto_l5(self, mock_matchmaking, mock_get_id):
        os.environ["LEVEL"] = "5"
        mock_matchmaking.return_value = {
            "level": "1",
            "url": "abc",
            "hashAlgo": "bcd",
            "scheme": "yup",
            "version": "1.2.3",
            "encryptionAlgo": "algo",
            "funded": True,
            "broadcastInterval": "1.23",
            "network": "net",
            "interchainWallet": "0xabc",
        }
        mock_get_id.return_value = "my_id"
        self.assertEqual(
            misc.get_v1_status(),
            {
                "id": "my_id",
                "level": 1,
                "url": "abc",
                "hashAlgo": "bcd",
                "scheme": "yup",
                "version": "1.2.3",
                "encryptionAlgo": "algo",
                "indexingEnabled": True,
                "funded": True,
                "broadcastInterval": 1.23,
                "network": "net",
                "interchainWallet": "0xabc",
            },
        )
        os.environ["LEVEL"] = "1"
