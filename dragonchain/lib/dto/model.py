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

from typing import Set

# TODO With python 3.8, implement protocols (static duck typing) for models


class Model(object):
    def export_as_search_index(self) -> dict:
        """Abstract Method"""
        raise NotImplementedError("This is an abstract method")

    def export_as_at_rest(self) -> dict:
        """Abstract Method"""
        raise NotImplementedError("This is an abstract method")


class BlockModel(Model):
    block_id: str
    dc_id: str
    proof: str

    def get_associated_l1_dcid(self) -> str:
        """Abstract Method"""
        raise NotImplementedError("This is an abstract method")

    def get_associated_l1_block_id(self) -> Set[str]:
        """Abstract Method"""
        raise NotImplementedError("This is an abstract method")
