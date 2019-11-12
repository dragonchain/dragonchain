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

import kubernetes

from dragonchain import test_env  # noqa: F401
from dragonchain.job_processor import job_processor


valid_task_definition = {
    "task_type": "create",
    "txn_type": "test",
    "id": "my-id",
    "image": "test",
    "cmd": "echo",
    "args": [],
    "env": {},
    "execution_order": "serial",
}
valid_task_definition_string = (
    '{"task_type":"create","txn_type":"test","id":"my-id","image":"test","cmd":"echo","args":[],"env":{},"execution_order":"serial"}'
)
invalid_task_definition_string = '{"txn_type":"test","id":"my-id","image":"test","cmd":"echo","args":[],"env":{},"execution_order":"serial"}'


class TestJobPoller(unittest.TestCase):
    def test_get_image_name(self):
        self.assertEqual(job_processor.get_image_name(), "/dragonchain_core:test-")

    def test_get_job_name(self):
        self.assertEqual(job_processor.get_job_name("my-id"), "contract-my-id")

    def test_get_job_labels(self):
        mock_event = {"id": "my-id"}
        self.assertDictEqual(
            job_processor.get_job_labels(mock_event),
            {
                "app.kubernetes.io/name": "contract-my-id",
                "app.kubernetes.io/component": "-job",
                "app.kubernetes.io/version": "",
                "app.kubernetes.io/instance": "my-id",
                "app.kubernetes.io/part-of": "",
                "dragonchainId": "",
                "stage": "test",
            },
        )

    @patch("dragonchain.job_processor.job_processor.redis.brpop_sync", return_value=(1, valid_task_definition_string))
    def test_can_get_next_task(self, mock_brpop):
        self.assertEqual(job_processor.get_next_task(), valid_task_definition)
        mock_brpop.assert_called_once_with("mq:contract-task", 0, decode=False)

    @patch("dragonchain.job_processor.job_processor.redis.brpop_sync", return_value=(1, invalid_task_definition_string))
    def test_get_next_task_returns_none_on_invalid_json_schema(self, mock_brpop):
        self.assertIsNone(job_processor.get_next_task())
        mock_brpop.assert_called_once_with("mq:contract-task", 0, decode=False)

    @patch("dragonchain.job_processor.job_processor.redis.brpop_sync", return_value=(1, '!i "am" not {valid} json!'))
    def test_get_next_task_returns_none_on_invalid_json(self, mock_brpop):
        self.assertIsNone(job_processor.get_next_task())
        mock_brpop.assert_called_once_with("mq:contract-task", 0, decode=False)

    @patch("dragonchain.job_processor.job_processor._kube", read_namespaced_job_status=MagicMock(return_value={"test": "dict"}))
    def test_get_existing_job_status(self, mock_kube):
        self.assertEqual(job_processor.get_existing_job_status({"id": "my-id"}), {"test": "dict"})
        mock_kube.read_namespaced_job_status.assert_called_once_with("contract-my-id", "")

    @patch(
        "dragonchain.job_processor.job_processor._kube",
        read_namespaced_job_status=MagicMock(side_effect=kubernetes.client.rest.ApiException(status=404)),
    )
    def test_get_existing_job_status_returns_none_on_not_found(self, mock_kube):
        self.assertIsNone(job_processor.get_existing_job_status({"id": "my-id"}))
        mock_kube.read_namespaced_job_status.assert_called_once_with("contract-my-id", "")

    @patch(
        "dragonchain.job_processor.job_processor._kube",
        read_namespaced_job_status=MagicMock(side_effect=kubernetes.client.rest.ApiException(status=500)),
    )
    def test_get_existing_job_status_raises_on_error(self, mock_kube):
        self.assertRaises(RuntimeError, job_processor.get_existing_job_status, {"id": "my-id"})
        mock_kube.read_namespaced_job_status.assert_called_once_with("contract-my-id", "")

    @patch("dragonchain.job_processor.job_processor._kube", delete_namespaced_job=MagicMock(return_value={"test": "dict"}))
    def test_delete_existing_job(self, mock_kube):
        self.assertEqual(job_processor.delete_existing_job({"id": "my-id"}), {"test": "dict"})
        mock_kube.delete_namespaced_job.assert_called_once_with(
            "contract-my-id", "", body=kubernetes.client.V1DeleteOptions(propagation_policy="Background")
        )

    @patch(
        "dragonchain.job_processor.job_processor._kube", delete_namespaced_job=MagicMock(side_effect=kubernetes.client.rest.ApiException(status=404))
    )
    def test_delete_existing_job_returns_none_on_not_found(self, mock_kube):
        self.assertIsNone(job_processor.delete_existing_job({"id": "my-id"}))
        mock_kube.delete_namespaced_job.assert_called_once_with(
            "contract-my-id", "", body=kubernetes.client.V1DeleteOptions(propagation_policy="Background")
        )

    @patch(
        "dragonchain.job_processor.job_processor._kube", delete_namespaced_job=MagicMock(side_effect=kubernetes.client.rest.ApiException(status=500))
    )
    def test_delete_existing_job_raises_on_error(self, mock_kube):
        self.assertRaises(RuntimeError, job_processor.delete_existing_job, {"id": "my-id"})
        mock_kube.delete_namespaced_job.assert_called_once_with(
            "contract-my-id", "", body=kubernetes.client.V1DeleteOptions(propagation_policy="Background")
        )

    @patch("dragonchain.job_processor.job_processor.get_next_task", return_value=valid_task_definition)
    @patch("dragonchain.job_processor.job_processor.get_existing_job_status", return_value=None)
    @patch("dragonchain.job_processor.job_processor.delete_existing_job")
    @patch("dragonchain.job_processor.job_processor.attempt_job_launch")
    def test_start_task_launches_job_when_no_existing_job(self, mock_job_launch, mock_delete_job, mock_get_job, mock_get_task):
        job_processor.start_task()

        mock_get_task.assert_called_once_with()
        mock_get_job.assert_called_once_with(valid_task_definition)
        mock_delete_job.assert_not_called()
        mock_job_launch.assert_called_once_with(valid_task_definition)

    @patch("dragonchain.job_processor.job_processor.get_next_task", return_value=valid_task_definition)
    @patch(
        "dragonchain.job_processor.job_processor.get_existing_job_status", return_value=MagicMock(status=MagicMock(active=0, succeeded=1, failed=0))
    )
    @patch("dragonchain.job_processor.job_processor.delete_existing_job")
    @patch("dragonchain.job_processor.job_processor.attempt_job_launch")
    def test_start_task_deletes_and_launches_job_when_finished_existing_job(self, mock_job_launch, mock_delete_job, mock_get_job, mock_get_task):
        job_processor.start_task()

        mock_get_task.assert_called_once_with()
        mock_get_job.assert_called_once_with(valid_task_definition)
        mock_delete_job.assert_called_once_with(valid_task_definition)
        mock_job_launch.assert_called_once_with(valid_task_definition)

    @patch("dragonchain.job_processor.job_processor.get_next_task", return_value=valid_task_definition)
    @patch(
        "dragonchain.job_processor.job_processor.get_existing_job_status", return_value=MagicMock(status=MagicMock(active=1, succeeded=0, failed=0))
    )
    @patch("dragonchain.job_processor.job_processor.delete_existing_job")
    @patch("dragonchain.job_processor.job_processor.attempt_job_launch")
    def test_start_task_no_ops_when_running_job(self, mock_job_launch, mock_delete_job, mock_get_job, mock_get_task):
        job_processor.start_task()

        mock_get_task.assert_called_once_with()
        mock_get_job.assert_called_once_with(valid_task_definition)
        mock_delete_job.assert_not_called()
        mock_job_launch.assert_not_called()

    def test_attempt_job_launch_raises_on_too_many_retries(self):
        self.assertRaises(RuntimeError, job_processor.attempt_job_launch, valid_task_definition, retry=6)

    @patch(
        "dragonchain.job_processor.job_processor._kube", create_namespaced_job=MagicMock(side_effect=kubernetes.client.rest.ApiException(status=500))
    )
    def test_attempt_job_launch_raises_on_error(self, mock_kube):
        self.assertRaises(RuntimeError, job_processor.attempt_job_launch, valid_task_definition)
        mock_kube.create_namespaced_job.assert_called_once()

    @patch(
        "dragonchain.job_processor.job_processor._kube", create_namespaced_job=MagicMock(side_effect=kubernetes.client.rest.ApiException(status=409))
    )
    @patch("time.sleep")
    def test_attempt_job_launch_retry_logic(self, sleep_patch, mock_kube):
        self.assertRaises(RuntimeError, job_processor.attempt_job_launch, valid_task_definition)
        self.assertEqual(mock_kube.create_namespaced_job.call_count, 6)
        self.assertEqual(sleep_patch.call_count, 6)

    @patch("dragonchain.job_processor.job_processor._kube")
    def test_attempt_job_launch_launches_job_correctly(self, mock_kube):
        job_processor.attempt_job_launch(valid_task_definition)
        mock_kube.create_namespaced_job.assert_called_once_with(
            namespace="",
            body=kubernetes.client.V1Job(
                metadata=kubernetes.client.V1ObjectMeta(
                    name=job_processor.get_job_name(valid_task_definition["id"]), labels=job_processor.get_job_labels(valid_task_definition)
                ),
                spec=kubernetes.client.V1JobSpec(
                    completions=1,
                    parallelism=1,
                    backoff_limit=1,
                    active_deadline_seconds=600,
                    template=kubernetes.client.V1PodTemplateSpec(
                        metadata=kubernetes.client.V1ObjectMeta(annotations={}, labels=job_processor.get_job_labels(valid_task_definition)),
                        spec=kubernetes.client.V1PodSpec(
                            containers=[
                                kubernetes.client.V1Container(
                                    name=job_processor.get_job_name(valid_task_definition["id"]),
                                    image=job_processor.get_image_name(),
                                    security_context=kubernetes.client.V1SecurityContext(privileged=True),
                                    volume_mounts=[
                                        kubernetes.client.V1VolumeMount(name="dockersock", mount_path="/var/run/docker.sock"),
                                        kubernetes.client.V1VolumeMount(name="faas", mount_path="/etc/openfaas-secret", read_only=True),
                                        kubernetes.client.V1VolumeMount(name="secrets", mount_path="", read_only=True),
                                    ],
                                    command=["sh"],
                                    args=["entrypoints/contract_job.sh"],
                                    env=[
                                        kubernetes.client.V1EnvVar(name="EVENT", value=valid_task_definition_string),
                                        kubernetes.client.V1EnvVar(name="SERVICE", value="contract-job"),
                                    ],
                                    env_from=[
                                        kubernetes.client.V1EnvFromSource(config_map_ref=kubernetes.client.V1ConfigMapEnvSource(name="-configmap"))
                                    ],
                                )
                            ],
                            volumes=[
                                kubernetes.client.V1Volume(
                                    name="dockersock", host_path=kubernetes.client.V1HostPathVolumeSource(path="/var/run/docker.sock")
                                ),
                                kubernetes.client.V1Volume(
                                    name="faas", secret=kubernetes.client.V1SecretVolumeSource(secret_name="openfaas-auth")  # nosec
                                ),
                                kubernetes.client.V1Volume(
                                    name="secrets", secret=kubernetes.client.V1SecretVolumeSource(secret_name="d--secrets")  # nosec
                                ),
                            ],
                            restart_policy="Never",
                        ),
                    ),
                ),
            ),
        )
