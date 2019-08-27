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
import os
import uuid
from typing import Dict, Union, Any, TYPE_CHECKING

from dragonchain.lib.dto import transaction_model
from dragonchain.lib.interfaces import storage
from dragonchain.lib.database import redis
from dragonchain import logger
from dragonchain import exceptions

if TYPE_CHECKING:
    import aiohttp

FAAS_GATEWAY = os.environ["FAAS_GATEWAY"]
REDIS_ENDPOINT = os.environ["REDIS_ENDPOINT"]
REDIS_PORT = os.environ["REDIS_PORT"]

_log = logger.get_logger()


async def invoke(session: "aiohttp.ClientSession", invocation_request: Dict[str, Any]) -> None:
    """
    This function packages transactions for smart contracts and invoke
    them, taking the result, putting it on the Dragonchain and storing
    the output in the heap.
    """
    try:
        transaction = invocation_request["transaction"]
        contract_id = invocation_request["contract_id"]

        # Create model
        transaction = transaction_model.new_from_queue_input(transaction)

        # Invoke the SC
        _log.info(f"Invoking smart contract for txn_type {transaction.txn_type}")
        try:
            invocation_response = await call_contract(session, contract_id, transaction.export_as_full())
        except exceptions.ContractInvocationError as e:
            create_output_transaction(transaction, f"Error occurred while executing smart contract: {str(e)}")
            output_transaction(transaction)
            redis.hdel_sync("mq:contract-processing", invocation_request["unique_id"])

        # Parse response if possible
        try:
            _log.info("Attempting to parse JSON from contract response")
            parsed_response = json.loads(invocation_response)
            if not isinstance(parsed_response, dict):
                raise TypeError
        except (TypeError, json.decoder.JSONDecodeError):
            _log.warning("Warning: could not parse JSON response, outputting raw response.")
            parsed_response = {"rawResponse": invocation_response}

        _log.info("Writing to contract heap")
        if parsed_response.get("OUTPUT_TO_HEAP") is not False:
            output_to_heap(parsed_response, contract_id=contract_id)

        if parsed_response.get("OUTPUT_TO_CHAIN") is not False:
            _log.info("Creating output transaction")
            create_output_transaction(transaction, parsed_response)
            output_transaction(transaction)

        # Mark as finished processing
        redis.hdel_sync("mq:contract-processing", invocation_request["unique_id"])
    except Exception:
        _log.exception("Uncaught exception invoking contract")
        # Ensure we don't continually process failing contract
        redis.hdel_sync("mq:contract-processing", invocation_request["unique_id"])
        raise RuntimeError(f"Contract invoker failure! Transaction: {transaction.export_as_full()}")


def output_to_heap(contract_response: Dict[str, Any], contract_id: str) -> None:
    for key, value in contract_response.items():
        _log.info(f"[SC-RETURN] Heap set request {key} : {value} to {contract_id}")
        storage.put_object_as_json(f"SMARTCONTRACT/{contract_id}/HEAP/{key}", value)


def create_output_transaction(transaction: transaction_model.TransactionModel, smart_contract_output: Union[Dict[Any, Any], str]) -> None:
    # Replace tags if specified
    if isinstance(smart_contract_output, dict) and "tag" in smart_contract_output and isinstance(smart_contract_output["tag"], str):
        transaction.tag = smart_contract_output["tag"]
        del smart_contract_output["tag"]

    #  Create new transaction by modifying invocation request
    transaction.invoker = transaction.txn_id
    transaction.payload = smart_contract_output
    transaction.txn_id = str(uuid.uuid4())


def output_transaction(transaction: transaction_model.TransactionModel) -> None:
    _log.info("Enqueueing to transaction processor")
    new_transaction = json.dumps(transaction.export_as_queue_task(), separators=(",", ":"))
    pushed = redis.lpush_sync("dc:tx:incoming", new_transaction)
    if pushed == 0:
        _log.info("Could not output transaction")
        raise exceptions.LedgerError("Error outputting contract data on chain")
    else:
        _log.info("Successfully enqueued SC response as transaction")


async def call_contract(session: "aiohttp.ClientSession", contract_id: str, payload: Dict[Any, Any]) -> str:
    _log.info(f"INVOKE -> {contract_id} {payload}")
    url = f"{FAAS_GATEWAY}/function/contract-{contract_id}"
    _log.info(f"Posting to {url}")
    r = await session.request("POST", url=url, json=payload)
    response = await r.text()
    _log.info(f"Response: status code={r.status}, body={response}")
    if r.status == 404:
        _log.info("404 response from contract")
        raise exceptions.ContractInvocationError("Contract invocation was attempted, but function was not found.")
    elif r.status != 200:
        _log.warning(f"Non 200 response from contract: {r.status}")
        return json.dumps({"error": f"Contract received non-200 response: {r.status}"}, separators=(",", ":"))
    else:
        return response
