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

import base64
from typing import TYPE_CHECKING

import boto3

if TYPE_CHECKING:
    from dragonchain.lib.types import DockerLogin

ecr = boto3.client("ecr")


def get_login() -> "DockerLogin":
    """
    Gets the docker login for ECR

    Params:
        auth_config: If true, will return in format for use with docker-py. Otherwise returns b64 token
    """
    username, password = base64.b64decode(get_login_token()).decode("utf-8").split(":")
    return {"username": username, "password": password}


def get_login_token() -> str:
    """
    returns auth from container registry service as token
    """
    return ecr.get_authorization_token(registryIds=["381978683274"])["authorizationData"][0]["authorizationToken"]


def delete_image(repository: str, image_digest: str) -> None:
    ecr.batch_delete_image(registryId="381978683274", repositoryName=repository, imageIds=[{"imageDigest": image_digest}])
