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
import json
from typing import Any

from dragonchain import exceptions

SECRET_LOCATION = os.environ["SECRET_LOCATION"]


def get_dc_secret(secret_name: str) -> Any:
    """Get the secret value for this Dragonchain's owned secrets
    Args:
        secret_name: The name of the secret to fetch
    Returns:
        Dragonchain secret by its key (usually a string, but not necessarily)
    """
    try:
        with open(SECRET_LOCATION) as f:
            secrets_json = json.loads(f.read())
    except Exception:
        raise RuntimeError("Error occurred loading DC secrets from file system")
    try:
        return secrets_json[secret_name]
    except Exception:
        raise exceptions.NotFound(f"Secret {secret_name} was not found")
