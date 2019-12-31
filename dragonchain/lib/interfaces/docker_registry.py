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
import base64
from typing import Any, TYPE_CHECKING

import requests

from dragonchain.lib.interfaces import secrets

if TYPE_CHECKING:
    from dragonchain.lib.types import DockerLogin

REGISTRY_USERNAME = os.environ["REGISTRY_USERNAME"]
FAAS_REGISTRY = os.environ["FAAS_REGISTRY"]


def get_login(as_token: bool = False) -> "DockerLogin":
    """
    returns auth from container registry service which will be stored in environment variable
    """
    return {"username": REGISTRY_USERNAME, "password": secrets.get_dc_secret("registry-password")}


def get_login_token() -> str:
    """
    returns auth from container registry service as token
    """
    return base64.b64encode(f"{REGISTRY_USERNAME}:{secrets.get_dc_secret('registry-password')}".encode("utf-8")).decode("ascii")


def delete_image(repository: Any, image_digest: str) -> None:
    """
    Remove image from Docker registry
    """
    try:
        requests.delete(
            f"https://{FAAS_REGISTRY}/v2/{repository}/manifests/{image_digest}", headers={"Authorization": f"Basic {get_login_token()}"}, timeout=30
        )
    except requests.exceptions.SSLError:  # Registry SSL is not configured properly, try http instead (don't allow auth for insecure connections)
        requests.delete(f"http://{FAAS_REGISTRY}/v2/{repository}/manifests/{image_digest}", timeout=30)
