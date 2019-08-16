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

from typing import TYPE_CHECKING

from dragonchain import exceptions
from dragonchain.lib.dto import eth
from dragonchain.lib.dto import btc
from dragonchain.lib.interfaces import storage

if TYPE_CHECKING:
    from dragonchain.lib.dto import model

FOLDER = "INTERCHAINS"
BITCOIN = "bitcoin"
ETHEREUM = "ethereum"


def get_interchain_client(blockchain: str, name: str) -> "model.InterchainModel":
    """Get a specific interchain client
    Args:
        blockchain: the blockchain of the desired client (i.e. bitcoin, ethereum, etc)
        name: the name (id) of the network to get (user defined on the creation of the interchain)
    Raises:
        exceptions.NotFound: When the requested client can't be found
    """
    if blockchain == BITCOIN:
        return btc.new_from_at_rest(storage.get_json_from_object(f"{FOLDER}/{BITCOIN}/{name}"))
    elif blockchain == ETHEREUM:
        return eth.new_from_at_rest(storage.get_json_from_object(f"{FOLDER}/{ETHEREUM}/{name}"))
    else:
        raise exceptions.NotFound(f"Blockchain network {blockchain} is not supported")


def set_default_interchain_client(blockchain: str, name: str) -> None:
    """Set the default interchain model for this chain
    Args:
        blockchain: the blockchain of the desired client (i.e. bitcoin, ethereum, etc)
        name: the name (id) of the network to set as default (user defined on the creation of the interchain)
    Raises:
        exceptions.NotFound: When trying to set a default to an interchain that doesn't exist on this chain
    """
    # Make sure the specified interchain exists before setting as default
    get_interchain_client(blockchain, name)
    storage.put_object_as_json(f"{FOLDER}/default", {"version": "1", "blockchain": blockchain, "name": name})


def get_default_interchain_client() -> "model.InterchainModel":
    """Get the interchain model which has been set as the default for this chain
    Returns:
        Instantiated InterchainModel
    Raises:
        exceptions.NotFound: When default has not been set, or set default cannot be found
        NotImplementedError: WHen the saved default is a bad version
    """
    default_dto = storage.get_json_from_object(f"{FOLDER}/default")
    if default_dto.get("version") == "1":
        return get_interchain_client(default_dto.get("blockchain"), default_dto.get("name"))
    else:
        raise NotImplementedError(f"Default dto error. Version {default_dto.get('version')} not supported")


def delete_interchain_client(blockchain: str, name: str) -> None:
    """Delete an interchain client from this chain
    Args:
        blockchain: the blockchain of the desired client (i.e. bitcoin, ethereum, etc)
        name: the name (id) of the network to delete (user defined on the creation of the interchain)
    """
    storage.delete(f"{FOLDER}/{blockchain}/{name}")
