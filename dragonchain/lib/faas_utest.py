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
from unittest.mock import patch, MagicMock
import base64
import os

from dragonchain.lib import faas
from dragonchain import exceptions

FAAS_GATEWAY = os.environ["FAAS_GATEWAY"]


class TestGetFaaSAuth(unittest.TestCase):
    @patch("builtins.open", unittest.mock.mock_open(read_data="mydata"))
    def test_delete_contract(self):
        my_fake_auth = f"Basic {base64.b64encode('mydata:mydata'.encode('utf-8')).decode('ascii')}"
        data = faas.get_faas_auth()
        self.assertEqual(my_fake_auth, data)


class TestGetContractLogs(unittest.TestCase):
    @patch("dragonchain.lib.faas.requests.get", return_value=MagicMock(status_code=200))
    @patch("dragonchain.lib.faas.get_faas_auth", return_value="auth")
    def test_get_raw_logs_makes_request(self, mock_get_auth, mock_get):
        expected_query_params = {"name": "contract-contract-id", "since": "date", "tail": 100}
        expected_headers = {"Authorization": "auth"}
        faas._get_raw_logs("contract-id", "date", 100)

        mock_get_auth.assert_called_once()
        mock_get.assert_called_once_with(f"{FAAS_GATEWAY}/system/logs", params=expected_query_params, headers=expected_headers)

    @patch("dragonchain.lib.faas.requests.get", return_value=MagicMock(status_code=500))
    @patch("dragonchain.lib.faas.get_faas_auth", return_value="auth")
    def test_get_raw_logs_raises_runtime_error_on_bad_response(self, mock_get_auth, mock_get):
        expected_query_params = {"name": "contract-contract-id", "since": "date", "tail": 100}
        expected_headers = {"Authorization": "auth"}

        self.assertRaises(exceptions.OpenFaasException, faas._get_raw_logs, "contract-id", "date", 100)
        mock_get_auth.assert_called_once()
        mock_get.assert_called_once_with(f"{FAAS_GATEWAY}/system/logs", params=expected_query_params, headers=expected_headers)

    @patch("dragonchain.lib.faas._get_raw_logs")
    def test_get_logs_calls_get_raw(self, mock_get_raw):
        faas.get_logs("contract-id", "date", 100)

        mock_get_raw.assert_called_once_with("contract-id", "date", 100)
