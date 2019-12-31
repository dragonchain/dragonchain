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

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dragonchain.lib.types import DockerLogin

REGISTRY_TYPE = os.environ["FAAS_REGISTRY"].lower()
if ".ecr." in REGISTRY_TYPE:
    import dragonchain.lib.interfaces.aws.ecr as registry
else:
    import dragonchain.lib.interfaces.docker_registry as registry  # noqa: T484 this is intentional


def get_login() -> "DockerLogin":
    """
    Returns login username and password from
    either aws or docker registry for on prem
    """
    return registry.get_login()


def get_login_token() -> str:
    """
    returns auth from container registry service as token
    """
    return registry.get_login_token()


def delete_image(repository: str, image_digest: str) -> None:
    """
    Delete image from ECR or on prem Docker registry
    """
    registry.delete_image(repository, image_digest)
