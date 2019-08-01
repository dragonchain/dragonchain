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
from unittest.mock import patch, MagicMock, ANY

from apscheduler.jobstores.base import ConflictingIdError

from dragonchain.scheduler import scheduler
from dragonchain import test_env  # noqa: F401
from dragonchain import exceptions


class FakeScModel(object):  # noqa: B903
    def __init__(self, name, cron, seconds):
        self.seconds = seconds
        self.cron = cron
        self.name = name


class SchedulerTest(unittest.TestCase):
    @patch("dragonchain.scheduler.scheduler.worker")
    @patch("dragonchain.scheduler.scheduler.redis.delete_sync", return_value="OK")
    @patch("dragonchain.scheduler.scheduler.redis.lpush_sync", return_value="OK")
    @patch("dragonchain.scheduler.scheduler.redis.brpop_sync", return_value=["whatever", '{"action":"create","contract_id":"apples","seconds":60}'])
    def test_subscribe1(self, brpop, lpush, delete, mock_worker):
        scheduler.subscribe("mq:scheduler")
        mock_worker.assert_called_with({"action": "create", "contract_id": "apples", "seconds": 60})

    @patch("dragonchain.scheduler.scheduler.worker", side_effect=exceptions.TimingEventSchedulerError("boom"))
    @patch("dragonchain.scheduler.scheduler.redis.delete_sync", return_value="OK")
    @patch("dragonchain.scheduler.scheduler.redis.lpush_sync", return_value="OK")
    @patch("dragonchain.scheduler.scheduler.redis.brpop_sync", return_value=["whatever", '{"action":"create","contract_id":"apples","seconds":60}'])
    def test_subscribe2(self, brpop, lpush, delete, mock_worker):
        self.assertRaises(exceptions.TimingEventSchedulerError, scheduler.subscribe, "mq:scheduler")
        lpush.assert_called_with("mq:scheduler:errors", ANY)

    @patch("dragonchain.scheduler.scheduler.redis.lpush_sync", return_value="OK")
    @patch("dragonchain.scheduler.scheduler.redis.hgetall_sync", return_value={"banana": '{"contract_id":"banana","seconds":54}'})
    def test_revive_dead_workers(self, hgetall, lpush):
        scheduler.revive_dead_workers()
        hgetall.assert_called_with("scheduler:params", decode=False)
        lpush.assert_called_with("mq:scheduler", '{"contract_id":"banana","seconds":54,"action":"create"}')

    def test_parse_json_or_fail(self):
        try:
            scheduler.parse_json_or_fail("{{{{{}{}")
        except Exception as e:
            self.assertEqual(str(e), "MALFORMED_JSON")
            return
        self.fail()  # Force a failure if no exception thrown

    @patch("dragonchain.scheduler.scheduler.redis.lpush_sync")
    def test_schedule_contract_invocation(self, lpush):
        sc_model = MagicMock()
        sc_model.id = "my_name"
        sc_model.cron = "* * * * *"
        sc_model.seconds = None
        sc_model.txn_type = "banana"
        sc_model.execution_order = "serial"
        scheduler.schedule_contract_invocation(sc_model)
        lpush.assert_called_with(
            "mq:scheduler",
            '{"action":"create","contract_id":"my_name","txn_type":"banana","execution_order":"serial","cron":"* * * * *","seconds":null}',
        )

    @patch("dragonchain.scheduler.scheduler.redis.lpush_sync")
    def test_schedule_contract_invocation_raises(self, lpush):
        sc_model = FakeScModel("my_name", None, None)
        try:
            scheduler.schedule_contract_invocation(sc_model)
            self.fail("no error raised")
        except Exception as e:
            self.assertEqual(str(e), "You must provide cron or seconds to schedule a job")
            return
        self.fail()  # Force a failure if no exception thrown

    # CREATE NON EXISTENT JOB
    @patch("dragonchain.scheduler.timing_event.redis.hexists_sync", return_value=False)
    @patch("dragonchain.scheduler.timing_event.redis.hset_sync", return_value="1")
    def test_create_new_job(self, hset, hexists):
        change_request = {"action": "create", "contract_id": "goo", "txn_type": "banana", "execution_order": "serial", "cron": "* * * * *"}
        scheduler.worker(change_request)
        hset.assert_called_with(
            "scheduler:params", "goo", '{"cron":"* * * * *","seconds":null,"contract_id":"goo","execution_order":"serial","txn_type":"banana"}'
        )

    # CREATE EXISTING JOB
    @patch("dragonchain.scheduler.timing_event.redis.hset_sync")
    @patch("dragonchain.scheduler.timing_event.redis.hexists_sync", return_value=True)
    @patch("apscheduler.schedulers.background.BackgroundScheduler.add_job", side_effect=ConflictingIdError("goo"))
    def test_create_existing_job(self, hexists, mock_hexists, mock_hset):
        self.assertRaises(
            exceptions.TimingEventSchedulerError,
            scheduler.worker,
            {"action": "create", "contract_id": "goo", "txn_type": "banana", "execution_order": "serial", "cron": "* * * * *"},
        )

    # DELETE EXISTING JOB
    @patch("dragonchain.scheduler.timing_event.redis.hexists_sync")
    @patch("dragonchain.scheduler.timing_event.redis.hget_sync", return_value='{"contract_id":"goo","action":"delete","seconds":60}')
    @patch("dragonchain.scheduler.timing_event.redis.hdel_sync")
    @patch("apscheduler.schedulers.background.BackgroundScheduler.remove_job")
    def test_delete_job(self, remove_job, hdel, hget, hexists):
        change_request = {"action": "delete", "contract_id": "banana", "txn_type": "banana", "execution_order": "serial"}
        scheduler.worker(change_request)
        remove_job.assert_called_once()
        hdel.assert_called_once()

    # DELETE NON EXISTENT JOB
    @patch("dragonchain.scheduler.scheduler.timing_event.exists", return_value=False)
    def test_delete_non_existent_job(self, exists):
        change_request = {"action": "delete", "contract_id": "banana", "txn_type": "banana", "execution_order": "serial"}
        self.assertRaises(exceptions.TimingEventSchedulerError, scheduler.worker, change_request)

    # UPDATE
    @patch("dragonchain.scheduler.scheduler.timing_event.exists", return_value=True)
    @patch("apscheduler.schedulers.background.BackgroundScheduler.reschedule_job")
    @patch("dragonchain.scheduler.timing_event.redis.hget_sync", return_value='{"contract_id":"whatever"}')
    @patch("dragonchain.scheduler.timing_event.redis.hset_sync")
    def test_update_job(self, mock_hset, mock_hget, reschedule_job, exists):
        change_request = {"action": "update", "contract_id": "banana", "execution_order": "serial", "txn_type": "banana", "seconds": 61}
        scheduler.worker(change_request)
        reschedule_job.assert_called_with("whatever", trigger=ANY)

    # UPDATE NON EXISTENT JOB
    @patch("dragonchain.scheduler.scheduler.timing_event.exists", return_value=False)
    @patch(
        "dragonchain.scheduler.scheduler.redis.hgetall_sync",
        return_value={"a": '{"action":"update","contract_id":"goo","execution_order":"serial","txn_type":"banana",seconds":60}'},
    )
    def test_update_non_existent_job(self, hgetall, hexists):
        change_request = {"action": "update", "contract_id": "banana", "execution_order": "serial", "txn_type": "banana", "seconds": 61}
        self.assertRaises(exceptions.TimingEventSchedulerError, scheduler.worker, change_request)
