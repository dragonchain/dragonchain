import unittest
from unittest.mock import patch, MagicMock
import os


from dragonchain.lib.logs import get_logs, get_raw_logs

FAAS_GATEWAY = os.environ["FAAS_GATEWAY"]


class TestGetContractLogs(unittest.TestCase):
    @patch("dragonchain.lib.logs.requests.get", return_value=MagicMock(status_code=200))
    @patch("dragonchain.lib.logs.get_faas_auth", return_value="auth")
    def test_get_raw_logs_makes_request(self, mock_get_auth, mock_get):
        expected_query_params = {"name": "contract-contract-id", "since": "date", "tail": 100}
        expected_headers = {"Authorization": "auth"}
        get_raw_logs("contract-id", "date", 100)

        mock_get_auth.assert_called_once()
        mock_get.assert_called_once_with(f"{FAAS_GATEWAY}/system/logs", params=expected_query_params, headers=expected_headers)

    @patch("dragonchain.lib.logs.requests.get", return_value=MagicMock(status_code=500))
    @patch("dragonchain.lib.logs.get_faas_auth", return_value="auth")
    def test_get_raw_logs_raises_runtime_error_on_bad_response(self, mock_get_auth, mock_get):
        expected_query_params = {"name": "contract-contract-id", "since": "date", "tail": 100}
        expected_headers = {"Authorization": "auth"}

        self.assertRaises(RuntimeError, get_raw_logs, "contract-id", "date", 100)
        mock_get_auth.assert_called_once()
        mock_get.assert_called_once_with(f"{FAAS_GATEWAY}/system/logs", params=expected_query_params, headers=expected_headers)

    @patch("dragonchain.lib.logs.get_raw_logs")
    def test_get_logs_calls_get_raw(self, mock_get_raw):
        get_logs("contract-id", "date", 100)

        mock_get_raw.assert_called_once_with("contract-id", "date", 100)
