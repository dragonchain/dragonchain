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
from unittest.mock import patch, ANY

from dragonchain import test_env  # noqa: F401
from dragonchain import exceptions
from dragonchain.webserver import helpers


class TestWebserverHelpers(unittest.TestCase):
    def test_flask_http_response_returns_correctly(self):
        response = helpers.flask_http_response(123, {"thing": "data"})
        expected_response = ('{"thing":"data"}', 123, {"Content-Type": "application/json"})
        self.assertEqual(response, expected_response)

    def test_format_success_returns_correctly(self):
        self.assertEqual({"success": "thing"}, helpers.format_success("thing"))

    def test_format_error_returns_correctly(self):
        response = helpers.format_error("test_category", "test_message")
        expected_response = {"error": {"type": "test_category", "details": "test_message"}}
        self.assertEqual(response, expected_response)

    @patch("dragonchain.webserver.helpers.error_reporter.report_exception")
    @patch("dragonchain.webserver.helpers.flask_http_response")
    def test_webserver_error_handler_not_found(self, mock_http_response, mock_report_exception):
        exception = exceptions.NotFound()
        helpers.webserver_error_handler(exception)
        mock_report_exception.assert_not_called()
        mock_http_response.assert_called_once_with(404, ANY)

    @patch("dragonchain.webserver.helpers.error_reporter.report_exception")
    @patch("dragonchain.webserver.helpers.flask_http_response")
    def test_webserver_error_handler_validation_exception(self, mock_http_response, mock_report_exception):
        exception = exceptions.ValidationException()
        helpers.webserver_error_handler(exception)
        mock_report_exception.assert_not_called()
        mock_http_response.assert_called_once_with(400, ANY)

    @patch("dragonchain.webserver.helpers.error_reporter.report_exception")
    @patch("dragonchain.webserver.helpers.flask_http_response")
    def test_webserver_error_handler_action_forbidden(self, mock_http_response, mock_report_exception):
        exception = exceptions.ActionForbidden()
        helpers.webserver_error_handler(exception)
        mock_report_exception.assert_not_called()
        mock_http_response.assert_called_once_with(403, ANY)

    @patch("dragonchain.webserver.helpers.error_reporter.report_exception")
    @patch("dragonchain.webserver.helpers.flask_http_response")
    def test_webserver_error_handler_insufficient_crypto(self, mock_http_response, mock_report_exception):
        exception = exceptions.NotEnoughCrypto()
        helpers.webserver_error_handler(exception)
        mock_report_exception.assert_not_called()
        mock_http_response.assert_called_once_with(400, ANY)

    @patch("dragonchain.webserver.helpers.error_reporter.report_exception")
    @patch("dragonchain.webserver.helpers.flask_http_response")
    def test_webserver_error_handler_contract_conflict(self, mock_http_response, mock_report_exception):
        exception = exceptions.ContractConflict()
        helpers.webserver_error_handler(exception)
        mock_report_exception.assert_not_called()
        mock_http_response.assert_called_once_with(409, ANY)

    @patch("dragonchain.webserver.helpers.error_reporter.report_exception")
    @patch("dragonchain.webserver.helpers.flask_http_response")
    def test_webserver_error_handler_transaction_type_conflict(self, mock_http_response, mock_report_exception):
        exception = exceptions.TransactionTypeConflict()
        helpers.webserver_error_handler(exception)
        mock_report_exception.assert_not_called()
        mock_http_response.assert_called_once_with(409, ANY)

    @patch("dragonchain.webserver.helpers.error_reporter.report_exception")
    @patch("dragonchain.webserver.helpers.flask_http_response")
    def test_webserver_error_handler_invalid_transaction_type(self, mock_http_response, mock_report_exception):
        exception = exceptions.InvalidTransactionType()
        helpers.webserver_error_handler(exception)
        mock_report_exception.assert_not_called()
        mock_http_response.assert_called_once_with(403, ANY)

    @patch("dragonchain.webserver.helpers.error_reporter.report_exception")
    @patch("dragonchain.webserver.helpers.flask_http_response")
    def test_webserver_error_handler_contract_limit_exceeded(self, mock_http_response, mock_report_exception):
        exception = exceptions.ContractLimitExceeded()
        helpers.webserver_error_handler(exception)
        mock_report_exception.assert_not_called()
        mock_http_response.assert_called_once_with(403, ANY)

    @patch("dragonchain.webserver.helpers.error_reporter.report_exception")
    @patch("dragonchain.webserver.helpers.flask_http_response")
    def test_webserver_error_handler_bad_state_error(self, mock_http_response, mock_report_exception):
        exception = exceptions.BadStateError()
        helpers.webserver_error_handler(exception)
        mock_report_exception.assert_not_called()
        mock_http_response.assert_called_once_with(400, ANY)

    @patch("dragonchain.webserver.helpers.error_reporter.report_exception")
    @patch("dragonchain.webserver.helpers.flask_http_response")
    def test_webserver_error_handler_unauthorized_exception(self, mock_http_response, mock_report_exception):
        exception = exceptions.UnauthorizedException()
        helpers.webserver_error_handler(exception)
        mock_report_exception.assert_not_called()
        mock_http_response.assert_called_once_with(401, ANY)

    @patch("dragonchain.webserver.helpers.error_reporter.report_exception")
    @patch("dragonchain.webserver.helpers.flask_http_response")
    def test_webserver_error_handler_api_rate_limit(self, mock_http_response, mock_report_exception):
        exception = exceptions.APIRateLimitException()
        helpers.webserver_error_handler(exception)
        mock_report_exception.assert_not_called()
        mock_http_response.assert_called_once_with(429, ANY)

    @patch("dragonchain.webserver.helpers.error_reporter.report_exception")
    @patch("dragonchain.webserver.helpers.flask_http_response")
    def test_webserver_error_handler_invalid_node_level(self, mock_http_response, mock_report_exception):
        exception = exceptions.InvalidNodeLevel()
        helpers.webserver_error_handler(exception)
        mock_report_exception.assert_not_called()
        mock_http_response.assert_called_once_with(400, ANY)

    @patch("dragonchain.webserver.helpers.error_reporter.report_exception")
    @patch("dragonchain.webserver.helpers.flask_http_response")
    def test_webserver_error_handler_not_accepting_verifications(self, mock_http_response, mock_report_exception):
        exception = exceptions.NotAcceptingVerifications()
        helpers.webserver_error_handler(exception)
        mock_report_exception.assert_not_called()
        mock_http_response.assert_called_once_with(412, ANY)

    @patch("dragonchain.webserver.helpers.error_reporter.report_exception")
    @patch("dragonchain.webserver.helpers.flask_http_response")
    def test_webserver_error_handler_bad_request(self, mock_http_response, mock_report_exception):
        exception = exceptions.BadRequest()
        helpers.webserver_error_handler(exception)
        mock_report_exception.assert_not_called()
        mock_http_response.assert_called_once_with(400, ANY)

    @patch("dragonchain.webserver.helpers.error_reporter.report_exception")
    @patch("dragonchain.webserver.helpers.flask_http_response")
    def test_webserver_error_handler_bad_auth_error(self, mock_http_response, mock_report_exception):
        exception = exceptions.BadDockerAuth()
        helpers.webserver_error_handler(exception)
        mock_report_exception.assert_not_called()
        mock_http_response.assert_called_once_with(400, ANY)

    @patch("dragonchain.webserver.helpers.error_reporter.report_exception")
    @patch("dragonchain.webserver.helpers.flask_http_response")
    def test_webserver_error_handler_lab_chain_forbidden(self, mock_http_response, mock_report_exception):
        exception = exceptions.LabChainForbiddenException()
        helpers.webserver_error_handler(exception)
        mock_report_exception.assert_not_called()
        mock_http_response.assert_called_once_with(403, ANY)

    @patch("dragonchain.webserver.helpers.error_reporter.report_exception")
    @patch("dragonchain.webserver.helpers.flask_http_response")
    def test_webserver_error_handler_unkown_error(self, mock_http_response, mock_report_exception):
        exception = RuntimeError()
        helpers.webserver_error_handler(exception)
        mock_report_exception.assert_called_once_with(exception, "")
        mock_http_response.assert_called_once_with(500, ANY)
