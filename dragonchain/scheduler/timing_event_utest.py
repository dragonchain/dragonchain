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
from unittest.mock import patch, ANY

import apscheduler

from dragonchain import test_env  # noqa: F401
from dragonchain.scheduler import timing_event


class TestTimingEvent(unittest.TestCase):
    @patch("dragonchain.scheduler.timing_event.redis.hexists_sync", return_value="banana")
    def test_get_job_exists(self, hexists):
        result = timing_event.exists("id")
        hexists.assert_called_with("scheduler:params", "id")
        self.assertEqual(result, "banana")

    @patch("dragonchain.scheduler.timing_event.redis.hget_sync", return_value=None)
    def test_get_by_id_fails(self, hget):
        try:
            timing_event.get_by_id("id")
        except Exception as e:
            self.assertEqual(str(e), "NOT_FOUND")

    @patch("dragonchain.scheduler.timing_event.redis.hget_sync", return_value='{"contract_id":"goobie", "seconds":2}')
    def test_get_by_id_valid(self, hget):
        event = timing_event.get_by_id("id")
        self.assertIsInstance(event, timing_event.TimingEvent)

    @patch("dragonchain.scheduler.timing_event.background_scheduler.background_scheduler.remove_job")
    @patch("dragonchain.scheduler.timing_event.redis.hdel_sync")
    def test_delete(self, hdel, remove_job):
        event = timing_event.TimingEvent(timing_id="garbage", seconds=1)
        event.delete()
        hdel.assert_called_with("scheduler:params", "garbage")
        remove_job.assert_called_with("garbage")

    @patch("dragonchain.scheduler.timing_event.background_scheduler.background_scheduler.modify_job")
    @patch("dragonchain.scheduler.timing_event.redis.hset_sync")
    def test_update_interval(self, hset, modify_job):
        event = timing_event.TimingEvent(timing_id="garbage", txn_type="banana", execution_order="serial", seconds=1)
        event.update(seconds=3, txn_type="banana", execution_order="serial")
        hset.assert_called_with(
            "scheduler:params", "garbage", '{"cron":null,"seconds":3,"contract_id":"garbage","execution_order":"serial","txn_type":"banana"}'
        )

    @patch("dragonchain.scheduler.timing_event.background_scheduler.background_scheduler.modify_job")
    @patch("dragonchain.scheduler.timing_event.redis.hset_sync")
    def test_update_cron(self, hset, modify_job):
        event = timing_event.TimingEvent(timing_id="garbage", txn_type="banana", execution_order="serial", seconds=3)
        event.update(cron="* * * * 1", txn_type="banana", execution_order="serial")
        hset.assert_called_with(
            "scheduler:params",
            "garbage",
            '{"cron":"* * * * 1","seconds":null,"contract_id":"garbage","execution_order":"serial","txn_type":"banana"}',
        )
        modify_job.assert_called_with("garbage", None, next_run_time=ANY, trigger=ANY)

    @patch("dragonchain.scheduler.timing_event.background_scheduler.background_scheduler.modify_job")
    @patch("dragonchain.scheduler.timing_event.redis.hset_sync")
    def test_update_raises(self, hset, modify_job):
        event = timing_event.TimingEvent(timing_id="garbage", seconds=1)
        try:
            event.update()
        except Exception as e:
            self.assertEqual(str(e), "BAD_REQUEST")

    def test_returns_instance(self):
        event = timing_event.TimingEvent(timing_id="garbage")
        self.assertIsInstance(event, timing_event.TimingEvent)

    @patch("dragonchain.scheduler.timing_event.redis.hset_sync", return_value="1")
    @patch("dragonchain.scheduler.timing_event.background_scheduler.background_scheduler.add_job")
    @patch("dragonchain.scheduler.timing_event.background_scheduler.background_scheduler.start")
    @patch("dragonchain.scheduler.timing_event.background_scheduler.background_scheduler.add_jobstore")
    def test_add_job_called_for_interval(self, scheduler_add_jobstore, scheduler_start, scheduler_add_job, hset):
        contract_id = "flim-flam"
        seconds = 3
        event = timing_event.TimingEvent(timing_id=contract_id, seconds=seconds)
        event.start()
        scheduler_add_job.assert_called_once_with(ANY, trigger=ANY, id=contract_id, max_instances=1)

    @patch(
        "dragonchain.scheduler.timing_event.background_scheduler.background_scheduler.add_job",
        side_effect=apscheduler.jobstores.base.ConflictingIdError("a"),
    )
    @patch("dragonchain.scheduler.timing_event.redis.hset_sync", return_value="banana")
    def test_start_raises_conflict_when_add_job_conflicts(self, a, b):
        contract_id = "flim-flam"
        seconds = 3
        event = timing_event.TimingEvent(timing_id=contract_id, seconds=seconds)
        try:
            event.start()
            self.fail("no error thrown")
        except Exception as e:
            self.assertEqual(str(e), "CONFLICT")

    @patch("dragonchain.scheduler.timing_event.redis.hset_sync", return_value="1")
    @patch("dragonchain.scheduler.timing_event.background_scheduler.background_scheduler.add_job")
    @patch("dragonchain.scheduler.timing_event.background_scheduler.background_scheduler.start")
    @patch("dragonchain.scheduler.timing_event.background_scheduler.background_scheduler.add_jobstore")
    @patch("apscheduler.triggers.cron.CronTrigger.from_crontab", return_value="whatever")
    def test_add_job_called_for_cron(self, from_crontab, scheduler_add_jobstore, scheduler_start, scheduler_add_job, hset):
        contract_id = "flim-flam"
        cron = "* * * * *"
        func = ANY
        event = timing_event.TimingEvent(timing_id=contract_id, cron=cron)
        event.start()
        scheduler_add_job.assert_called_once_with(func, id=contract_id, max_instances=1, trigger="whatever")


class FakeEvent(object):
    def __init__(self, exception):
        self.exception = exception
        self.traceback = "traceback"

    def exception(self):
        return self.exception
