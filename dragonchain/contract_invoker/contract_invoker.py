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

import json
import random
import asyncio
from queue import Queue
from threading import Thread

import aiohttp
import fastjsonschema

from dragonchain.lib.dto import schema
from dragonchain.lib.dao import smart_contract_dao
from dragonchain.lib.database import redis
from dragonchain.contract_invoker import contract_invoker_service
from dragonchain import logger
from dragonchain import exceptions
from dragonchain.lib import error_reporter

_log = logger.get_logger()
_serial_worker_threads: dict = {}
_serial_queues: dict = {}
_validate_sc_invoke_request = fastjsonschema.compile(schema.smart_contract_invoke_request_schema)


def setup() -> None:
    _log.info("Initializing contract service...")
    restart_dead_workers()
    _log.info("Service initialized!")


async def start() -> None:
    _log.info("Checking for any previously in-process SC invocations that need to be re-queued")
    # Recover contracts that didn't finish processing (in case of crash, etc)
    events = await redis.hgetall_async("mq:contract-processing", decode=False)
    event_list = []
    for _, value in events.items():
        event_list.append(value)
    if event_list:
        # Push them to the front of the queue, and reset current processing list
        await redis.rpush_async("mq:contract-invoke", *event_list)
        await redis.delete_async("mq:contract-processing")

    _log.info("Starting event loop")
    session = aiohttp.ClientSession()
    try:
        while True:
            await process_events(session)
    except Exception:
        await session.close()
        raise


async def process_events(session: aiohttp.ClientSession) -> None:
    try:
        unique_id = str(random.randint(0, 9999999999999))
        _, event = await redis.brpop_async("mq:contract-invoke", timeout=0, decode=False)
        # Place into in process queue for safety (deleted after contract finishes invoking)
        await redis.hset_async("mq:contract-processing", unique_id, event)
        _log.info(f"Receieved contract invocation request {event}")
        event = json.loads(event)
        _validate_sc_invoke_request(event)
        event["unique_id"] = unique_id
    except Exception:
        await redis.hdel_async("mq:contract-processing", unique_id)
        _log.exception("Invalid contract invocation request")
        raise

    # Invoke the contract!
    if event["execution_order"] == "parallel":
        # Invoke the contract asynchronously with the event loop. "fire-and-forget"
        asyncio.create_task(contract_invoker_service.invoke(session, event))
    elif event["execution_order"] == "serial":
        _log.info(f"Executing contract {event['contract_id']} as serial")
        # Ensure the worker is running
        existing_thread = _serial_worker_threads.get(event["contract_id"])
        if not existing_thread or not existing_thread.is_alive():
            restart_serial_worker(event["contract_id"])
        # Queue the actual job for the serial worker
        _serial_queues[event["contract_id"]].put(event, block=False)
    else:
        _log.warning(f"Invalid execution order on invocation request: {event}")
        # TODO: Push event to failed queue.


def restart_serial_worker(contract_id: str) -> None:
    _log.info(f"Restarting worker {contract_id}")
    _serial_queues[contract_id] = Queue()
    _serial_worker_threads[contract_id] = Thread(target=asyncio.run, args=[serial_contract_worker(contract_id)], daemon=True)
    _serial_worker_threads[contract_id].start()


def restart_dead_workers() -> None:
    try:
        for contract in smart_contract_dao.get_serial_contracts():
            restart_serial_worker(contract["id"])
    except exceptions.NotFound:
        _log.warning("No serial contracts found")


async def serial_contract_worker(contract_id: str) -> None:
    session = aiohttp.ClientSession()
    _log.info(f"Worker started for contract {contract_id}")
    while True:
        try:
            event = _serial_queues[contract_id].get(block=True)  # Blocks until receives from queue
            _log.info(f"Executing {contract_id}")
            await contract_invoker_service.invoke(session, event)
        except Exception:
            _log.exception("Error invoking serial contract")


def error_handler(loop: "asyncio.AbstractEventLoop", context: dict) -> None:
    exception = context.get("exception")
    if exception:
        message = error_reporter.get_exception_message(exception)
        error_reporter.report_exception(exception, message)
        loop.stop()
        loop.close()


if __name__ == "__main__":
    try:
        setup()
        event_loop = asyncio.get_event_loop()
        event_loop.set_exception_handler(error_handler)
        event_loop.run_until_complete(start())
    except Exception as e:
        error_reporter.report_exception(e, "Error running contract invoker")
        raise
