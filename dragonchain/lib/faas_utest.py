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
        faas.get_raw_logs("contract-id", "date", 100)

        mock_get_auth.assert_called_once()
        mock_get.assert_called_once_with(f"{FAAS_GATEWAY}/system/logs", params=expected_query_params, headers=expected_headers)

    @patch("dragonchain.lib.faas.requests.get", return_value=MagicMock(status_code=500))
    @patch("dragonchain.lib.faas.get_faas_auth", return_value="auth")
    def test_get_raw_logs_raises_runtime_error_on_bad_response(self, mock_get_auth, mock_get):
        expected_query_params = {"name": "contract-contract-id", "since": "date", "tail": 100}
        expected_headers = {"Authorization": "auth"}

        self.assertRaises(exceptions.OpenFaasException, faas.get_raw_logs, "contract-id", "date", 100)
        mock_get_auth.assert_called_once()
        mock_get.assert_called_once_with(f"{FAAS_GATEWAY}/system/logs", params=expected_query_params, headers=expected_headers)

    @patch("dragonchain.lib.faas.get_raw_logs")
    def test_get_logs_calls_get_raw(self, mock_get_raw):
        faas.get_logs("contract-id", "date", 100)

        mock_get_raw.assert_called_once_with("contract-id", "date", 100)
