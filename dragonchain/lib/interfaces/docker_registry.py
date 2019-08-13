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

import os
from typing import Any, TYPE_CHECKING

import docker

from dragonchain.lib.interfaces import secrets

if TYPE_CHECKING:
    from dragonchain.lib.types import DockerLogin

REGISTRY_USERNAME = os.environ["REGISTRY_USERNAME"]


def get_login(as_token: bool = False) -> "DockerLogin":
    """
    returns auth from container registry service which will be stored in environment variable
    """
    return {"username": REGISTRY_USERNAME, "password": secrets.get_dc_secret("registry-password")}


def delete_image(repository: Any, image_digest: str) -> None:
    """
    Remove image from Docker registry
    """
    docker.remove_image(image_digest)
