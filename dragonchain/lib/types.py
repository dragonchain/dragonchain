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

from typing import List, Union, Dict, Tuple, Any, TYPE_CHECKING

from mypy_extensions import TypedDict

if not TYPE_CHECKING:
    raise RuntimeError("dragonchain.lib.types should never be imported during runtime")


JSONEncodableNatives = Union[str, int, float, bool, None]
# Doesn't cover 100%, but is better than nothing...
JSONType = Union[Dict[Any, Any], List[Any], Tuple[Any], JSONEncodableNatives]
DockerLogin = TypedDict("DockerLogin", {"username": str, "password": str})
RSearch = TypedDict("RSearch", {"results": List[Any], "total": int})
L1Headers = TypedDict("L1Headers", {"dc_id": str, "block_id": str, "proof": str})
custom_index = TypedDict("custom_index", {"path": str, "field_name": str, "type": str, "options": Dict[str, Any]})
permissions_doc = TypedDict("permissions_doc", {"version": str, "default_allow": bool, "permissions": Dict[str, Any]})
