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

from dragonchain.lib.dto import smart_contract_model
from dragonchain.lib.database import redis


def begin_task(sc_model: "smart_contract_model.SmartContractModel", task_type: "smart_contract_model.ContractActions") -> None:
    """Notify builder service to begin a task via message queue
    Args:
        sc_model (obj): Start an invocation of this smart contract
        task_type (Enum, optional): Task type of this invocation
    Raises:
        RuntimeError: When failing to begin a task by pushing to redis
    """
    if redis.lpush_sync("mq:contract-task", json.dumps(sc_model.export_as_contract_task(task_type=task_type), separators=(",", ":"))) == 0:
        raise RuntimeError("Failed to push to job MQ")
