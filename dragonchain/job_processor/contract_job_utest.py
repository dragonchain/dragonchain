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

import importlib
import unittest
from unittest.mock import patch, MagicMock

from dragonchain import test_env  # noqa: F401
from dragonchain import exceptions
from dragonchain.job_processor import contract_job
from dragonchain.lib.dto import smart_contract_model
from dragonchain.lib.dao import smart_contract_dao


class ContractJobTest(unittest.TestCase):
    class BuildTaskResult(object):
        def __init__(self, txn_type, task_type, state, cmd, args, secrets=None, image=None, auth=None):
            self.txn_type = txn_type
            self.task_type = task_type
            self.id = txn_type
            self.start_state = state
            self.cmd = cmd
            self.args = args
            self.secrets = secrets or {"secret-key": "banana"}
            self.existing_secrets = secrets
            self.env = {"bana": "na", "STAGE": "banana"}
            self.image = image
            self.image_digest = "image_digest"
            self.auth = auth
            self.auth_key_id = ""
            self.execution_order = "parallel"
            self.seconds = 0
            self.cron = "* * * * *"
            self.set_state = MagicMock()
            self.desired_state = "active"
            self.update_faas_fields = MagicMock()
            self.save = MagicMock()
            self.update = MagicMock()
            self.status = "active"

    class BuildTaskResultWithHelpers(object):
        def __init__(self, txn_type, task_type, state, cmd, args, secrets=None, image=None, auth=None):
            self.txn_type = txn_type
            self.task_type = task_type
            self.id = txn_type
            self.start_state = state
            self.cmd = cmd
            self.args = args
            self.secrets = secrets or {"secret-key": "banana"}
            self.existing_secrets = secrets
            self.env = {"bana": "na", "STAGE": "banana"}
            self.image = image
            self.image_digest = "image_digest"
            self.auth = auth
            self.auth_key_id = ""
            self.execution_order = "parallel"
            self.seconds = 0
            self.cron = "* * * * *"
            self.set_state = self.set_state_helper
            self.desired_state = "active"
            self.set_state = self.set_state_helper
            self.update_faas_fields = self.update_faas_helper
            self.save = MagicMock()
            self.update = MagicMock()
            self.status = "active"

        def update_faas_helper(self, update_model):
            contract_job.smart_contract_model.SmartContractModel.update_faas_fields(self, update_model=update_model)

        def set_state_helper(self, state, msg):
            contract_job.smart_contract_model.SmartContractModel.set_state(self, state=state, msg=msg)

    @patch(
        "dragonchain.job_processor.contract_job.smart_contract_model.new_from_build_task",
        return_value=BuildTaskResult("banana", "delete", "active", "ban", "ana", {}),
    )
    @patch("dragonchain.job_processor.contract_job.ContractJob.docker_login_if_necessary")
    def setUp(self, mock_login, mock_new_build_task):
        self.test_job = contract_job.ContractJob({"task_type": "create"})
        importlib.reload(contract_job)
        contract_job.EVENT = '{"task_type": "create"}'

    @patch(
        "dragonchain.job_processor.contract_job.smart_contract_model.new_from_build_task",
        return_value=BuildTaskResult("banana", "update", "active", "ban", "ana"),
    )
    def test_init_job_update(self, mock_new_build_task):
        test_job = contract_job.ContractJob({"task_type": "update"})
        mock_new_build_task.assert_called_once()
        self.assertIsNotNone(test_job.update_model)

    @patch(
        "dragonchain.job_processor.contract_job.smart_contract_model.new_from_build_task",
        return_value=BuildTaskResult("banana", "create", "active", "ban", "ana"),
    )
    @patch("dragonchain.job_processor.contract_job.ContractJob.docker_login_if_necessary")
    def test_init_job_create(self, mock_login, mock_new_build_task):
        test_job = contract_job.ContractJob({"task_type": "create"})
        mock_new_build_task.assert_called_once()
        self.assertIsNone(test_job.update_model)
        self.assertEqual(test_job.model.task_type, "create")

    @patch(
        "dragonchain.job_processor.contract_job.smart_contract_model.new_from_build_task",
        return_value=BuildTaskResult("banana", "delete", "active", "ban", "ana"),
    )
    @patch("dragonchain.job_processor.contract_job.ContractJob.docker_login_if_necessary")
    def test_init_job_delete(self, mock_login, mock_new_build_task):
        test_job = contract_job.ContractJob({"task_type": "delete"})
        mock_new_build_task.assert_called_once()
        self.assertIsNone(test_job.update_model)
        self.assertEqual(test_job.model.task_type, "delete")

    @patch("dragonchain.job_processor.contract_job.authorization.register_new_auth_key", return_value={"key": "ban", "id": "ana"})
    def test_populate_api_keys(self, mock_register_auth):
        self.test_job.populate_api_keys()
        self.assertEqual(self.test_job.model.secrets["secret-key"], "ban")
        self.assertEqual(self.test_job.model.secrets["auth-key-id"], "ana")
        self.assertEqual(self.test_job.model.auth_key_id, "ana")

    @patch("dragonchain.lib.keys.get_public_id", return_value="z7S3WADvnjCyFkUmL48cPGqrSHDrQghNxLFMwBEwwtMa")
    def test_populate_env(self, mock_get_id):
        self.test_job.model.env = {}
        self.test_job.model.id = "banana"
        self.test_job.model.txn_type = "bananaphone"
        self.test_job.populate_env()
        self.assertEqual(self.test_job.model.env["STAGE"], "test")
        self.assertEqual(self.test_job.model.env["INTERNAL_ID"], "")
        self.assertEqual(self.test_job.model.env["SMART_CONTRACT_ID"], "banana")
        self.assertEqual(self.test_job.model.env["SMART_CONTRACT_NAME"], "bananaphone")

    @patch("dragonchain.job_processor.contract_job.open")
    @patch("dragonchain.job_processor.contract_job.os.path.abspath")
    @patch("dragonchain.job_processor.contract_job.os.path.dirname", return_value="/banana")
    def test_create_dockerfile(self, mock_dirname, mock_abspath, mock_open):
        mock_open.return_value.read.return_value = "fakeSecret"
        result = self.test_job.create_dockerfile()
        mock_dirname.assert_called()
        mock_open.assert_called()
        self.assertEqual(result, "/banana")

    def test_docker_login_if_necessary_update_model(self):
        self.test_job.docker = MagicMock()
        self.test_job.docker.login = MagicMock(side_effect=Exception)
        self.test_job.update_model = self.BuildTaskResult("banana", "delete", "active", "ban", "ana", {}, image="banana/chain", auth="YmFuYTpuYQ==")
        try:
            self.test_job.docker_login_if_necessary()
            self.fail()  # Force test to fail if no exceptions.BadDockerAuth thrown
        except exceptions.BadDockerAuth:
            self.test_job.docker.login.assert_called_with("bana", "na", registry="banana")

    def test_docker_login_if_necessary_no_update_model(self):
        self.test_job.docker = MagicMock()
        self.test_job.docker.login = MagicMock(side_effect=Exception)
        self.test_job.model = self.BuildTaskResult("banana", "delete", "active", "ban", "ana", {}, image="banana/chain", auth="YmFuYTpuYQ==")
        try:
            self.test_job.docker_login_if_necessary()
            self.fail()  # Force test to fail if no exceptions.BadDockerAuth thrown
        except exceptions.BadDockerAuth:
            self.test_job.docker.login.assert_called_with("bana", "na", registry="banana")

    def test_docker_login_if_necessary_attempt_login(self):
        self.test_job.docker = MagicMock()
        self.test_job.docker.login = MagicMock()
        self.test_job.model = self.BuildTaskResult("banana", "delete", "active", "ban", "ana", {}, image="banana/chain", auth="YmFuYTpuYQ==")
        self.test_job.docker_login_if_necessary()
        self.test_job.docker.login.assert_called_with("bana", "na")

    def test_docker_login_bad_auth(self):
        self.test_job.update_model = self.BuildTaskResult("banana", "delete", "active", "ban", "ana", {}, image="banana/chain", auth="banana")
        try:
            self.test_job.docker_login_if_necessary()
        except exceptions.BadDockerAuth:
            return
        self.fail()  # Force test to fail if no exceptions.BadDockerAuth thrown

    @patch("dragonchain.job_processor.contract_job.open")
    def test_get_faas_auth(self, mock_open):
        self.maxDiff = None
        mock_open.return_value.read.return_value = "bana:na"
        result = self.test_job.get_faas_auth()
        self.assertEqual(result.split(" ")[0], "Basic")
        self.assertIsNotNone(result.split(" ")[1])

    @patch("dragonchain.lib.keys.get_public_id", return_value="z7S3WADvnjCyFkUmL48cPGqrSHDrQghNxLFMwBEwwtMa")
    def test_get_openfaas_spec(self, mock_get_id):
        self.maxDiff = None
        self.test_job.update_model = {"execution_order": "parallel"}
        self.test_job.model.image_digest = "sha256:imasha"
        result = self.test_job.get_openfaas_spec()
        self.assertEqual(
            result,
            {
                "service": "contract-banana",
                "envProcess": "ban a n a",
                "envVars": {
                    "INTERNAL_ID": "",
                    "DRAGONCHAIN_ID": "z7S3WADvnjCyFkUmL48cPGqrSHDrQghNxLFMwBEwwtMa",
                    "DRAGONCHAIN_ENDPOINT": "http://fake.org",
                    "SMART_CONTRACT_ID": "banana",
                    "SMART_CONTRACT_NAME": "banana",
                    "STAGE": "test",
                    "bana": "na",
                    "read_timeout": "60s",
                    "combine_output": "false",
                    "write_debug": "true",
                    "write_timeout": "60s",
                },
                "secrets": ["sc-banana-banana"],
                "labels": {
                    "com.dragonchain.id": "",
                    "com.openfaas.scale.factor": "20",
                    "com.openfaas.scale.max": "20",
                    "com.openfaas.scale.min": "1",
                    "com.openfaas.fwatchdog.version": "0.15.4",
                },
                "limits": {"cpu": "0.50", "memory": "600M"},
                "requests": {"cpu": "0.25", "memory": "600M"},
                "image": "/customer-contracts@sha256:imasha",
            },
        )

    def test_check_image_size(self):
        try:
            self.test_job.docker = MagicMock()
            self.test_job.docker.images = MagicMock()
            self.test_job.docker.images.pull = MagicMock(return_value=MagicMock(attrs={"Size": 500000}))
            self.test_job.pull_image("banana")
            self.test_job.docker.images.pull.assert_called()
        except Exception:
            self.fail()  # Fail test if exception thrown

    def test_check_image_size_too_large(self):
        try:
            self.test_job.docker = MagicMock()
            self.test_job.docker.images = MagicMock()
            self.test_job.docker.images.pull = MagicMock(return_value=MagicMock(attrs={"Size": 600000000}))
            self.test_job.pull_image("banana")
        except Exception:
            self.test_job.docker.images.pull.assert_called()
            return
        self.fail()  # Fail test if exception not thrown

    @patch("dragonchain.job_processor.contract_job.registry_interface.delete_image")
    def test_delete_contract_image(self, mock_ecr):
        self.test_job.delete_contract_image("some_digest")
        mock_ecr.assert_called()

    @patch("dragonchain.job_processor.contract_job.registry_interface.delete_image", side_effect=Exception)
    def test_delete_contract_image_failure(self, mock_ecr):
        try:
            self.test_job.model.set_state = MagicMock()
            self.test_job.model.save = MagicMock()
            self.test_job.delete_contract_image("some_digest")
            self.fail()  # Fail if no exception thrown
        except Exception:
            mock_ecr.assert_called()
            self.test_job.model.set_state.assert_called_once()

    @patch("dragonchain.job_processor.contract_job.registry_interface.get_login")
    @patch("dragonchain.job_processor.contract_job.docker")
    def test_build_contract_image(self, mock_docker, mock_ecr):
        self.test_job.docker_login_if_necessary = MagicMock()
        self.test_job.update_model = MagicMock()
        self.test_job.update_model.image = "bananamage"
        self.test_job.model.image_digest = ""
        self.test_job.docker = MagicMock()
        self.test_job.docker.images = MagicMock()
        self.test_job.pull_image = MagicMock(return_value=MagicMock(id="bana:na", attrs={"Size": 1234123}))
        self.test_job.create_dockerfile = MagicMock()
        self.test_job.docker.images.build = MagicMock(return_value=[MagicMock(id="ba:nana"), True])
        self.test_job.docker.images.push = MagicMock()

        self.test_job.build_contract_image()
        self.test_job.pull_image.assert_called()
        self.test_job.create_dockerfile.assert_called()
        self.test_job.docker.images.build.assert_called()
        self.test_job.docker.images.push.assert_called()

    @patch("dragonchain.job_processor.contract_job.requests.post", return_value=MagicMock(status_code=202))
    def test_create_openfaas_secrets(self, mock_requests):
        self.test_job.get_faas_auth = MagicMock()
        self.test_job.model.existing_secrets = []
        self.test_job.model.secrets = {"banana": "secret banana"}

        self.test_job.create_openfaas_secrets()
        mock_requests.assert_called()
        self.test_job.get_faas_auth.assert_called()
        self.assertEqual(self.test_job.model.existing_secrets, ["banana"])

    @patch("dragonchain.job_processor.contract_job.requests.post", return_value=MagicMock(status_code=400))
    def test_create_openfaas_secrets_throws(self, mock_requests):
        self.test_job.get_faas_auth = MagicMock()
        self.test_job.model.existing_secrets = []
        self.test_job.model.secrets = {"banana": "secret banana"}
        self.test_job.model.set_state = MagicMock()
        self.test_job.model.save = MagicMock()
        self.test_job.send_report = MagicMock()

        self.assertRaises(exceptions.ContractException, self.test_job.create_openfaas_secrets)
        self.test_job.model.set_state.assert_called()
        mock_requests.assert_called()
        self.test_job.get_faas_auth.assert_called()
        self.assertEqual(self.test_job.model.existing_secrets, [])

    @patch("dragonchain.job_processor.contract_job.open")
    @patch("dragonchain.job_processor.contract_job.requests.delete", return_value=MagicMock(status_code=202))
    def test_delete_openfaas_secrets(self, mock_requests, mock_open):
        mock_open.return_value.read.return_value = "banana"
        self.test_job.model.existing_secrets = ["banana"]

        self.test_job.delete_openfaas_secrets()
        mock_requests.assert_called()
        mock_open.assert_called()
        # because the model will be deleted, there's no need to check that the secret specifically has been removed

    @patch("dragonchain.job_processor.contract_job.open")
    @patch("dragonchain.job_processor.contract_job.requests.delete", return_value=MagicMock(status_code=400))
    def test_delete_openfaas_secrets_throws(self, mock_requests, mock_open):
        mock_open.return_value.read.return_value = "banana"
        self.test_job.model.existing_secrets = ["banana"]
        self.test_job.model.set_state = MagicMock()
        self.test_job.model.save = MagicMock()

        self.test_job.delete_openfaas_secrets()
        self.test_job.model.set_state.assert_called()
        mock_requests.assert_called()
        mock_open.assert_called()
        # because the model will be deleted, there's no need to check that the secret specifically has been removed

    @patch("dragonchain.job_processor.contract_job.open")
    @patch("dragonchain.job_processor.contract_job.storage")
    @patch("dragonchain.job_processor.contract_job.requests")
    def test_deploy_to_openfaas(self, mock_requests, mock_storage, mock_open):
        self.test_job.task_type = "update"
        mock_requests.put.return_value = MagicMock(status_code=200)
        mock_open.return_value.read.return_value = "banana"
        try:
            self.test_job.deploy_to_openfaas()
        except Exception:
            self.fail()

        mock_requests.put.assert_called()
        mock_storage.put_object_as_json.assert_called()
        mock_open.assert_called()

    @patch("dragonchain.job_processor.contract_job.open")
    @patch("dragonchain.job_processor.contract_job.requests")
    def test_deploy_to_openfaas_throws(self, mock_requests, mock_open):
        self.test_job.task_type = "update"
        self.test_job.model.set_state = MagicMock()
        self.test_job.model.save = MagicMock()
        mock_requests.put.return_value = MagicMock(status_code=400)
        mock_open.return_value.read.return_value = "banana"

        self.assertRaises(exceptions.ContractException, self.test_job.deploy_to_openfaas)
        self.test_job.model.set_state.assert_called()
        mock_requests.put.assert_called()
        mock_open.assert_called()

    @patch("dragonchain.job_processor.contract_job.open")
    @patch("dragonchain.job_processor.contract_job.requests.delete")
    def test_delete_openfaas_function(self, mock_requests, mock_open):
        mock_requests.return_value = MagicMock(status_code=202)
        self.test_job.delete_openfaas_function()
        mock_requests.assert_called()
        mock_open.assert_called()

    @patch("dragonchain.job_processor.contract_job.open")
    @patch("dragonchain.job_processor.contract_job.requests.delete")
    def test_delete_openfaas_function_throws(self, mock_requests, mock_open):
        self.test_job.model.set_state = MagicMock()
        self.test_job.model.save = MagicMock()
        mock_requests.return_value = MagicMock(status_code=400)

        self.test_job.delete_openfaas_function()

        self.test_job.model.set_state.assert_called()
        mock_requests.assert_called()
        mock_open.assert_called()

    @patch("dragonchain.job_processor.contract_job.transaction_type_dao.remove_existing_transaction_type")
    @patch("dragonchain.job_processor.contract_job.elasticsearch.remove_index")
    @patch("dragonchain.job_processor.contract_job.storage.delete_directory")
    @patch("dragonchain.job_processor.contract_job.storage.delete")
    def test_delete_contract_data(self, mock_delete, mock_delete_directory, mock_remove_index, mock_delete_txn_type):
        self.test_job.contract_service = MagicMock()
        self.test_job.delete_contract_data()

        mock_delete_directory.assert_called_once_with(f"SMARTCONTRACT/{self.test_job.model.id}")
        mock_delete.assert_called_once_with(f"KEYS/{self.test_job.model.auth_key_id}")
        mock_remove_index.assert_called_once()
        mock_delete_txn_type.assert_called_once()

    @patch("dragonchain.job_processor.contract_job.scheduler.schedule_contract_invocation")
    def test_schedule_contract(self, mock_schedule):
        self.test_job.model.seconds = 1
        self.test_job.schedule_contract()
        mock_schedule.assert_called()

    @patch("dragonchain.job_processor.contract_job.scheduler.schedule_contract_invocation")
    def test_unschedule_contract(self, mock_schedule):
        self.test_job.unschedule_contract()
        mock_schedule.assert_called()

    @patch("dragonchain.job_processor.contract_job.transaction_dao.ledger_contract_action")
    def test_ledger(self, mock_ledger):
        self.test_job.ledger()
        mock_ledger.assert_called()

    @patch("dragonchain.job_processor.contract_job.transaction_dao.ledger_contract_action")
    def test_ledger_throws(self, mock_ledger):
        self.test_job.model.set_state = MagicMock()
        self.test_job.model.save = MagicMock()
        mock_ledger.side_effect = Exception

        self.test_job.ledger()

        self.test_job.model.set_state.assert_called()
        mock_ledger.assert_called()

    @patch("dragonchain.lib.keys.get_public_id", return_value="z7S3WADvnjCyFkUmL48cPGqrSHDrQghNxLFMwBEwwtMa")
    def test_migrate_env(self, mock_get_id):
        self.test_job.model.env = MagicMock()
        self.test_job.update_model = MagicMock()
        self.test_job.update_model.env = {"orange": "banana"}
        self.test_job.migrate_env()
        self.test_job.model.env.update.assert_called_once_with(self.test_job.update_model.env)

    def test_main_create(self):
        self.test_job.model = self.BuildTaskResult("banana", "create", "active", "ban", "ana", {}, image="image", auth="YmFuYTpuYQ==")
        self.test_job.model.save = MagicMock()
        smart_contract_model.new_from_build_task = MagicMock(return_value=self.test_job.model)
        contract_job.EVENT = '{"task_type": "create"}'
        contract_job.ContractJob.create = MagicMock()
        contract_job.main()
        contract_job.ContractJob.create.assert_called()

    @patch("dragonchain.job_processor.contract_job.ContractJob.delete")
    def test_run_delete(self, delete_mock):
        self.test_job.model = self.BuildTaskResult("banana", "delete", "active", "ban", "ana", {}, image="image", auth="YmFuYTpuYQ==")
        smart_contract_model.new_from_build_task = MagicMock(return_value=self.test_job.model)
        contract_job.EVENT = '{"task_type": "delete"}'
        contract_job.main()
        delete_mock.assert_called()

    @patch("dragonchain.lib.keys.get_public_id", return_value="z7S3WADvnjCyFkUmL48cPGqrSHDrQghNxLFMwBEwwtMa")
    def test_create(self, mock_get_id):
        self.test_job.docker = MagicMock()
        self.test_job.schedule_contract = MagicMock()
        self.test_job.build_contract_image = MagicMock()
        self.test_job.deploy_to_openfaas = MagicMock()
        self.test_job.create_openfaas_secrets = MagicMock()
        self.test_job.model.cron = "* * * * *"
        self.test_job.model.save = MagicMock()
        self.test_job.populate_api_keys = MagicMock()
        self.test_job.create()

    @patch("dragonchain.lib.keys.get_public_id", return_value="z7S3WADvnjCyFkUmL48cPGqrSHDrQghNxLFMwBEwwtMa")
    @patch("dragonchain.job_processor.contract_job.smart_contract_dao")
    def test_update(self, mock_model, mock_get_id):
        self.test_job.deploy_to_openfaas = MagicMock()
        self.test_job.schedule_contract = MagicMock()
        self.test_job.update_model = self.BuildTaskResult("banana", "update", "active", "ban", "ana")
        self.test_job.model.save = MagicMock()
        self.test_job.create_openfaas_secrets = MagicMock()
        self.test_job.update()

    @patch("dragonchain.lib.keys.get_public_id", return_value="z7S3WADvnjCyFkUmL48cPGqrSHDrQghNxLFMwBEwwtMa")
    @patch("dragonchain.job_processor.contract_job.registry_interface.get_login")
    @patch("dragonchain.job_processor.contract_job.ContractJob.docker_login_if_necessary")
    @patch("dragonchain.job_processor.contract_job.docker")
    def test_main_pass_does_update_model(self, mock_docker, mock_login, mock_ecr, mock_secrets):
        contract_job.EVENT = '{"txn_type": "test", "task_type": "update", "id": "123", "start_state": "inactive", "auth": "auth", "image": "image", "cmd": "cmd", "args": "[one]", "secrets": "{}", "existing_secrets": "[]", "env": "{}", "cron": "None", "seconds": "30",  "execution_order": "serial", "desired_state": "active"}'  # noqa: B950
        self.test_job.model = self.BuildTaskResultWithHelpers("banana", "create", "inactive", "ban", "ana", {}, image="image", auth="YmFuYTpuYQ==")
        self.test_job.update_model = self.BuildTaskResultWithHelpers(
            "banana", "create", "active", "banana", "ana", {}, image="new/image", auth="YmFuYTpuYQ=!"
        )
        self.test_job.model.update_faas_fields(update_model=self.test_job.update_model)
        self.test_job.update_model.update_faas_fields(update_model=self.test_job.update_model)
        smart_contract_dao.get_contract_by_txn_type = MagicMock(return_value=self.test_job.model)
        smart_contract_model.new_from_build_task = MagicMock(return_value=self.test_job.update_model)
        contract_job.ContractJob.create_dockerfile = MagicMock()
        contract_job.ContractJob.create_openfaas_secrets = MagicMock()
        contract_job.ContractJob.delete_contract_image = MagicMock()
        contract_job.ContractJob.deploy_to_openfaas = MagicMock()
        contract_job.ContractJob.pull_image = MagicMock()
        contract_job.ContractJob.schedule_contract = MagicMock()
        mock_docker.from_env = MagicMock()
        mock_docker.images.push = MagicMock()
        mock_docker.images.get = MagicMock()

        try:
            job = contract_job.main()
            self.assertEqual(job.model.image, "new/image")
            self.assertEqual(job.update_model.image, "new/image")
            self.assertEqual(job.model.cmd, "banana")
            self.assertEqual(job.model.status["state"], "active")
            job.model.save.assert_called()
        except Exception:
            self.fail("should not have thrown a generic exception!")

    def test_delete(self):
        self.test_job.model.cron = "* * * * *"
        self.test_job.delete_openfaas_secrets = MagicMock()
        self.test_job.delete_openfaas_function = MagicMock()
        self.test_job.delete_contract_data = MagicMock()
        self.test_job.delete_contract_image = MagicMock()
        self.test_job.unschedule_contract = MagicMock()
        self.test_job.model.save = MagicMock()
        self.test_job.delete()
        self.test_job.delete_openfaas_secrets.assert_called_once()
        self.test_job.delete_openfaas_function.assert_called_once()
        self.test_job.delete_contract_image.assert_called_once()
        self.test_job.delete_contract_data.assert_called_once()
        self.test_job.unschedule_contract.assert_called_once()
