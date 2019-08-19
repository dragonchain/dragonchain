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

import enum
from typing import Dict, Any

MAX_CUSTOM_INDEXES = 5


class DCRN(enum.Enum):
    """Dragonchain Resource Name Enum"""

    # Singular transaction model names
    Transaction_L1_Search_Index = "Transaction::L1::SearchIndex"  # What is indexed by ES
    Transaction_L1_Full = "Transaction::L1::FullTransaction"  # A transaction containing header, payload and signature
    Transaction_L1_Stripped = "Transaction::L1::Stripped"  # A transaction with header and signature, but no payload

    # Block model names
    Block_L1_Search_Index = "Block::L1::SearchIndex"  # What is indexed by ES
    Block_L2_Search_Index = "Block::L2::SearchIndex"  # What is used to index blocks
    Block_L3_Search_Index = "Block::L3::SearchIndex"  # What is used to index blocks
    Block_L4_Search_Index = "Block::L4::SearchIndex"  # What is used to index blocks
    Block_L5_Search_Index = "Block::L5::SearchIndex"  # What is used to index blocks

    Block_L1_At_Rest = "Block::L1::AtRest"  # Contains stringified Transaction::L1::Stripped array, what is stored in storage
    Block_L2_At_Rest = "Block::L2::AtRest"  # What is stored in storage
    Block_L3_At_Rest = "Block::L3::AtRest"  # What is stored in storage
    Block_L4_At_Rest = "Block::L4::AtRest"  # What is stored in storage
    Block_L5_At_Rest = "Block::L5::AtRest"  # What is stored in storage

    # Smart contract model names
    SmartContract_L1_At_Rest = "SmartContract::L1::AtRest"  # What is stored in storage
    SmartContract_L1_Search_Index = "SmartContract::L1::SearchIndex"  # What is indexed by ES

    Error_InTransit_Template = "Error::L{}::InTransit"


api_key_create_schema_v1 = {"type": "object", "properties": {"nickname": {"type": "string"}}, "additionalProperties": False}


api_key_update_schema_v1 = {"type": "object", "properties": {"nickname": {"type": "string"}}, "required": ["nickname"], "additionalProperties": False}


interchain_auth_registration_schema_v1 = {
    "type": "object",
    "properties": {"dcid": {"type": "string"}, "key": {"type": "string"}, "signature": {"type": "string"}},
    "required": ["dcid", "key", "signature"],
}


transaction_create_schema_v1 = {
    "type": "object",
    "properties": {
        "version": {"type": "string"},
        "txn_type": {
            "type": "string",
            #  The following regex disallows the usage of our reserved namespace (begins with -) for txn_type
            "pattern": "^[^-].*$",
            "maxLength": 128,  # We can change max txn_type length if needed
        },
        "payload": {"type": ["object", "string"]},
        "tag": {"type": "string", "maxLength": 1024},  # We can change max tag length if needed, this is rather arbitrary at the moment
    },
    "required": ["txn_type", "payload"],
}


bulk_transaction_create_schema_v1 = {
    "type": "array",
    "items": transaction_create_schema_v1,
    "minItems": 1,
    "maxItems": 250,  # Arbitrarily set for now. Feel free to change this if needed
}


transaction_search_index_schema = {
    "type": "object",
    "properties": {
        "version": {"type": "string"},
        "dcrn": {"type": "string", "enum": [DCRN.Transaction_L1_Search_Index.value]},
        "txn_type": {"type": "string"},
        "dc_id": {"type": "string"},
        "txn_id": {"type": "string"},
        "tag": {"type": "string"},
        "block_id": {"type": "integer"},
        "timestamp": {"type": "integer"},
        "invoker": {"type": "string"},
        "s3_object_folder": {"type": "string"},
        "s3_object_id": {"type": "string"},
        "l2_rejections": {"type": "integer"},
    },
    "required": [
        "version",
        "dcrn",
        "txn_type",
        "dc_id",
        "txn_id",
        "tag",
        "block_id",
        "timestamp",
        "invoker",
        "s3_object_folder",
        "s3_object_id",
        "l2_rejections",
    ],
}


transaction_full_schema = {
    "type": "object",
    "properties": {
        "version": {"type": "string"},
        "dcrn": {"type": "string", "enum": [DCRN.Transaction_L1_Full.value]},
        "header": {
            "type": "object",
            "properties": {
                "txn_type": {"type": "string"},
                "dc_id": {"type": "string"},
                "txn_id": {"type": "string"},
                "tag": {"type": "string"},
                "block_id": {"type": "string"},
                "invoker": {"type": "string"},
            },
            "required": ["txn_type", "dc_id", "txn_id", "block_id"],
        },
        "payload": {"type": "string"},
        "proof": {"type": "object", "properties": {"full": {"type": "string"}, "stripped": {"type": "string"}}, "required": ["full", "stripped"]},
    },
    "required": ["version", "dcrn", "header", "payload", "proof"],
}


def get_transaction_queue_task_schema(dict_payload: bool = False) -> Dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "version": {"type": "string"},
            "header": {
                "type": "object",
                "properties": {
                    "txn_type": {"type": "string"},
                    "dc_id": {"type": "string"},
                    "txn_id": {"type": "string"},
                    "tag": {"type": "string"},
                    "timestamp": {"type": "string"},
                    "invoker": {"type": "string"},
                },
                "required": ["txn_type", "dc_id", "txn_id"],
            },
            "payload": {"type": ["object", "string"]} if dict_payload else {"type": "string"},
        },
        "required": ["version", "header", "payload"],
    }


transaction_stripped_schema = {
    "type": "object",
    "properties": {
        "version": {"type": "string"},
        "dcrn": {"type": "string", "enum": [DCRN.Transaction_L1_Stripped.value]},
        "header": {
            "type": "object",
            "properties": {
                "txn_type": {"type": "string"},
                "dc_id": {"type": "string"},
                "txn_id": {"type": "string"},
                "block_id": {"type": "string"},
                "tag": {"type": "string"},
                "invoker": {"type": "string"},
            },
            "required": ["txn_type", "dc_id", "txn_id", "block_id", "tag", "invoker"],
        },
        "proof": {"type": "object", "properties": {"full": {"type": "string"}, "stripped": {"type": "string"}}, "required": ["full", "stripped"]},
    },
    "required": ["version", "dcrn", "header", "proof"],
}


l1_search_index_schema = {
    "type": "object",
    "properties": {
        "version": {"type": "string"},
        "dcrn": {"type": "string", "enum": [DCRN.Block_L1_Search_Index.value]},
        "dc_id": {"type": "string"},
        "block_id": {"type": "integer"},
        "timestamp": {"type": "integer"},
        "prev_id": {"type": "integer"},
        "prev_proof": {"type": "string"},
        "s3_object_folder": {"type": "string"},
        "s3_object_id": {"type": "string"},
        "l2_verifications": {"type": "integer"},
        "l3_verifications": {"type": "integer"},
        "l4_verifications": {"type": "integer"},
        "l5_verifications": {"type": "integer"},
    },
    "required": [
        "version",
        "dcrn",
        "dc_id",
        "block_id",
        "timestamp",
        "prev_id",
        "prev_proof",
        "s3_object_folder",
        "s3_object_id",
        "l2_verifications",
        "l3_verifications",
        "l4_verifications",
        "l5_verifications",
    ],
}


l1_block_at_rest_schema = {
    "type": "object",
    "properties": {
        "version": {"type": "string"},
        "dcrn": {"type": "string", "enum": [DCRN.Block_L1_At_Rest.value]},
        "header": {
            "type": "object",
            "properties": {
                "dc_id": {"type": "string"},
                "block_id": {"type": "string"},
                "level": {"type": "integer"},
                "timestamp": {"type": "string"},
                "prev_id": {"type": "string"},
                "prev_proof": {"type": "string"},
            },
            "required": ["dc_id", "block_id", "prev_id", "prev_proof"],
        },
        "transactions": {"type": "array", "items": {"type": "string"}},
        "proof": {
            "type": "object",
            "properties": {"scheme": {"type": "string"}, "proof": {"type": "string"}, "nonce": {"type": "integer"}},
            "required": ["scheme", "proof"],
        },
    },
    "required": ["version", "dcrn", "header", "transactions", "proof"],
}

l1_broadcast_schema_v1 = {
    "type": "object",
    "properties": {"version": {"type": "string"}, "payload": l1_block_at_rest_schema},
    "required": ["version", "payload"],
}


smart_contract_invoke_request_schema = {
    "type": "object",
    "properties": {
        "version": {"type": "string"},
        "contract_id": {"type": "string"},
        "execution_order": {"type": "string"},
        "transaction": get_transaction_queue_task_schema(dict_payload=True),
    },
}


smart_contract_build_task_schema = {
    "type": "object",
    "properties": {
        "version": {"type": "string"},
        "task_type": {"type": "string", "enum": ["create", "update", "delete"]},
        "txn_type": {"type": "string"},
        "id": {"type": "string"},
        "auth": {"type": ["string", "null"]},
        "image": {"type": ["string", "null"]},
        "cmd": {"type": ["string", "null"]},
        "args": {"type": ["array", "null"], "items": {"type": "string"}},
        "env": {"type": ["object", "null"]},
        "secrets": {"type": ["object", "null"]},
        "existing_secrets": {"type": ["null", "array"]},
        "execution_order": {"type": ["string", "null"]},
        "image_digest": {"type": ["string", "null"]},
        "start_state": {"type": ["string", "null"]},
        "desired_state": {"type": ["string", "null"], "enum": ["active", "inactive", None]},
    },
    "required": ["task_type", "txn_type", "id", "image", "cmd", "args", "env", "execution_order"],
}


smart_contract_create_schema_v1 = {
    "type": "object",
    "properties": {
        "version": {"type": "string"},
        "txn_type": {"type": "string", "pattern": "[a-zA-Z0-9][a-zA-Z0-9-]+", "maxLength": 20},
        "image": {
            "type": "string",
            "pattern": r"""^(?:(?=[^:\/]{4,253})(?!-)[a-zA-Z0-9-]{1,63}(?<!-)(?:\.(?!-)[a-zA-Z0-9-]{1,63}(?<!-))*(?::[0-9]{1,5})?/)?((?![._-])(?:[a-z0-9._-]*)(?<![._-])(?:/(?![._-])[a-z0-9._-]*(?<![._-]))*)(:(?![.-])[a-zA-Z0-9_.-]{1,128})$""",  # noqa: B950
        },
        "auth": {"type": "string"},
        "cmd": {"type": "string"},
        "args": {"type": "array", "items": {"type": "string"}},
        "env": {"type": "object"},
        "secrets": {"type": "object"},
        "seconds": {"type": "integer", "minimum": 1, "maximum": 60},
        "cron": {"type": "string"},
        "execution_order": {"type": "string", "enum": ["serial", "parallel"]},
    },
    "required": ["version", "txn_type", "image", "cmd", "execution_order"],
}


smart_contract_update_schema_v1 = {
    "type": "object",
    "properties": {
        "version": {"type": "string"},
        "desired_state": {"type": "string", "enum": ["active", "inactive"]},
        "image": {
            "type": "string",
            "pattern": r"""^(?:(?=[^:\/]{4,253})(?!-)[a-zA-Z0-9-]{1,63}(?<!-)(?:\.(?!-)[a-zA-Z0-9-]{1,63}(?<!-))*(?::[0-9]{1,5})?/)?((?![._-])(?:[a-z0-9._-]*)(?<![._-])(?:/(?![._-])[a-z0-9._-]*(?<![._-]))*)(:(?![.-])[a-zA-Z0-9_.-]{1,128})$""",  # noqa: B950
        },
        "auth": {"type": "string"},
        "cmd": {"type": "string"},
        "args": {"type": "array", "items": {"type": "string"}},
        "env": {"type": "object"},
        "secrets": {"type": "object"},
        "seconds": {"type": "integer", "minimum": 1, "maximum": 60},
        "cron": {"type": "string"},
        "execution_order": {"type": "string", "enum": ["serial", "parallel"]},
    },
}


smart_contract_at_rest_schema = {
    "type": "object",
    "properties": {
        "dcrn": {"type": "string", "enum": [DCRN.SmartContract_L1_At_Rest.value]},
        "version": {"type": "string"},
        "txn_type": {"type": "string"},
        "id": {"type": "string"},
        "status": {
            "type": "object",
            "properties": {
                "state": {"type": "string", "enum": ["pending", "error", "active", "inactive", "updating", "deleting", "delete failed"]},
                "msg": {"type": "string"},
                "timestamp": {"type": "string"},
            },
            "required": ["state", "msg"],
        },
        "image": {"type": "string"},
        "faas_image": {"type": "string"},
        "cmd": {"type": "string"},
        "args": {"type": "array", "items": {"type": "string"}},
        "env": {"type": "object"},
        "secrets": {"type": "array", "items": {"type": "string"}},
        "cron": {"type": "string"},
        "seconds": {"type": "integer"},
        "image_digest": {"type": ["string", "null"]},
        "execution_order": {"type": "string", "enum": ["serial", "parallel"]},
    },
    "required": ["dcrn", "version", "txn_type", "id", "status", "image", "cmd", "env", "execution_order"],
}


smart_contract_index_schema = {
    "type": "object",
    "properties": {
        "dcrn": {"type": "string", "enum": [DCRN.SmartContract_L1_Search_Index.value]},
        "version": {"type": "string"},
        "id": {"type": "string"},
        "txn_type": {"type": "string"},
        "image_digest": {"type": ["string", "null"]},
        "state": {"type": "string"},
    },
    "required": ["dcrn", "version", "id", "state"],
}


l2_block_at_rest_schema = {
    "type": "object",
    "properties": {
        "version": {"type": "string"},
        "dcrn": {"type": "string", "enum": [DCRN.Block_L2_At_Rest.value]},
        "header": {
            "type": "object",
            "properties": {
                "dc_id": {"type": "string"},
                "level": {"type": "integer"},
                "block_id": {"type": "string"},
                "timestamp": {"type": "string"},
                "prev_proof": {"type": "string"},
            },
            "required": ["dc_id", "level", "block_id", "prev_proof"],
        },
        "validation": {
            "type": "object",
            "properties": {
                "dc_id": {"type": "string"},
                "block_id": {"type": "string"},
                "stripped_proof": {"type": "string"},
                "transactions": {"type": "string"},
            },
            "required": ["dc_id", "block_id", "stripped_proof", "transactions"],
        },
        "proof": {
            "type": "object",
            "properties": {"scheme": {"type": "string"}, "proof": {"type": "string"}, "nonce": {"type": "integer"}},
            "required": ["scheme", "proof"],
        },
    },
    "required": ["version", "dcrn", "header", "validation", "proof"],
}


l2_search_index_schema = {
    "type": "object",
    "properties": {
        "version": {"type": "string"},
        "dcrn": {"type": "string", "enum": [DCRN.Block_L2_Search_Index.value]},
        "dc_id": {"type": "string"},
        "block_id": {"type": "integer"},
        "timestamp": {"type": "integer"},
        "prev_proof": {"type": "string"},
        "s3_object_folder": {"type": "string"},
        "s3_object_id": {"type": "string"},
    },
    "required": ["version", "dcrn", "dc_id", "block_id", "timestamp", "prev_proof", "s3_object_folder", "s3_object_id"],
}


l2_broadcast_schema_v1 = {
    "type": "object",
    "properties": {
        "version": {"type": "string"},
        "payload": {
            "type": "object",
            "properties": {
                "header": {
                    "type": "object",
                    "properties": {"dc_id": {"type": "string"}, "block_id": {"type": "string"}, "stripped_proof": {"type": "string"}},
                    "required": ["dc_id", "block_id", "stripped_proof"],
                },
                "l2-blocks": {"type": "array", "items": {"type": "object"}},
            },
            "required": ["header", "l2-blocks"],
        },
    },
    "required": ["version", "payload"],
}


l3_broadcast_schema_v1 = {
    "type": "object",
    "properties": {
        "version": {"type": "string"},
        "payload": {
            "type": "object",
            "properties": {
                "header": {
                    "type": "object",
                    "properties": {"dc_id": {"type": "string"}, "block_id": {"type": "string"}, "stripped_proof": {"type": "string"}},
                    "required": ["dc_id", "block_id", "stripped_proof"],
                },
                "l3-blocks": {"type": "array", "items": {"type": "object"}},
            },
            "required": ["header", "l3-blocks"],
        },
    },
    "required": ["version", "payload"],
}


l3_block_at_rest_schema = {
    "type": "object",
    "properties": {
        "version": {"type": "string"},
        "dcrn": {"type": "string", "enum": [DCRN.Block_L3_At_Rest.value]},
        "header": {
            "type": "object",
            "properties": {
                "dc_id": {"type": "string"},
                "level": {"type": "integer"},
                "block_id": {"type": "string"},
                "timestamp": {"type": "string"},
                "prev_proof": {"type": "string"},
            },
            "required": ["dc_id", "level", "block_id", "timestamp", "prev_proof"],
        },
        "l2-validations": {
            "type": "object",
            "properties": {
                "l1_dc_id": {"type": "string"},
                "l1_block_id": {"type": "string"},
                "l1_proof": {"type": "string"},
                "l2_proofs": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {"dc_id": {"type": "string"}, "block_id": {"type": "string"}, "proof": {"type": "string"}},
                        "required": ["dc_id", "block_id", "proof"],
                    },
                },
                "ddss": {"type": "string"},
                "count": {"type": "string"},
                "regions": {"type": "array"},
                "clouds": {"type": "array"},
            },
            "required": ["l1_dc_id", "l1_block_id", "l1_proof", "ddss", "count", "regions", "clouds"],
        },
        "proof": {
            "type": "object",
            "properties": {"scheme": {"type": "string"}, "proof": {"type": "string"}, "nonce": {"type": "integer"}},
            "required": ["scheme", "proof"],
        },
    },
    "required": ["version", "dcrn", "header", "l2-validations", "proof"],
}


l3_search_index_schema = {
    "type": "object",
    "properties": {
        "version": {"type": "string"},
        "dcrn": {"type": "string", "enum": [DCRN.Block_L3_Search_Index.value]},
        "dc_id": {"type": "string"},
        "block_id": {"type": "integer"},
        "timestamp": {"type": "integer"},
        "prev_proof": {"type": "string"},
        "s3_object_folder": {"type": "string"},
        "s3_object_id": {"type": "string"},
    },
    "required": ["version", "dcrn", "dc_id", "block_id", "timestamp", "prev_proof", "s3_object_folder", "s3_object_id"],
}


l4_broadcast_schema_v1 = {
    "type": "object",
    "properties": {
        "version": {"type": "string"},
        "payload": {"type": "object", "properties": {"l4-blocks": {"type": "array", "items": {"type": "object"}}}, "required": ["l4-blocks"]},
    },
    "required": ["version", "payload"],
}


l4_validation_schema = {
    "type": "object",
    "properties": {"l3_dc_id": {"type": "string"}, "l3_block_id": {"type": "string"}, "l3_proof": {"type": "string"}, "valid": {"type": "boolean"}},
    "required": ["l3_dc_id", "l3_block_id", "l3_proof", "valid"],
}


l4_block_at_rest_schema = {
    "type": "object",
    "properties": {
        "version": {"type": "string"},
        "dcrn": {"type": "string", "enum": [DCRN.Block_L4_At_Rest.value]},
        "header": {
            "type": "object",
            "properties": {
                "dc_id": {"type": "string"},
                "level": {"type": "integer"},
                "block_id": {"type": "string"},
                "timestamp": {"type": "string"},
                "l1_dc_id": {"type": "string"},
                "l1_block_id": {"type": "string"},
                "l1_proof": {"type": "string"},
                "prev_proof": {"type": "string"},
            },
            "required": ["dc_id", "level", "block_id", "timestamp", "l1_dc_id", "l1_block_id", "l1_proof", "prev_proof"],
        },
        "l3-validations": {"type": "array", "items": l4_validation_schema},
        "proof": {
            "type": "object",
            "properties": {"scheme": {"type": "string"}, "proof": {"type": "string"}, "nonce": {"type": "integer"}},
            "required": ["scheme", "proof"],
        },
    },
    "required": ["version", "dcrn", "header", "l3-validations", "proof"],
}


l4_search_index_schema = {
    "type": "object",
    "properties": {
        "version": {"type": "string"},
        "dcrn": {"type": "string", "enum": [DCRN.Block_L4_Search_Index.value]},
        "dc_id": {"type": "string"},
        "block_id": {"type": "integer"},
        "timestamp": {"type": "integer"},
        "prev_proof": {"type": "string"},
        "s3_object_folder": {"type": "string"},
        "s3_object_id": {"type": "string"},
    },
    "required": ["version", "dcrn", "dc_id", "block_id", "timestamp", "prev_proof", "s3_object_folder", "s3_object_id"],
}


# L5 methods


l5_block_at_rest_schema = {
    "type": "object",
    "properties": {
        "version": {"type": "string"},
        "dcrn": {"type": "string", "enum": [DCRN.Block_L5_At_Rest.value]},
        "header": {
            "type": "object",
            "properties": {
                "dc_id": {"type": "string"},
                "level": {"type": "integer"},
                "block_id": {"type": "string"},
                "timestamp": {"type": "string"},
                "prev_proof": {"type": "string"},
            },
            "required": ["dc_id", "level", "block_id", "timestamp", "prev_proof"],
        },
        "l4-blocks": {"type": "array", "items": {"type": "string"}},
        "proof": {
            "type": "object",
            "properties": {"scheme": {"type": "string"}, "proof": {"type": "string"}, "nonce": {"type": "integer"}},
            "required": ["scheme", "proof"],
        },
    },
    "required": ["version", "dcrn", "header", "l4-blocks", "proof"],
}


custom_index_items = {
    "type": "object",
    "properties": {"key": {"type": "string"}, "path": {"type": "string"}},
    "additionalProperties": False,
    "required": ["key", "path"],
}


new_transaction_type_register_request_schema_v1 = {
    "type": "object",
    "properties": {
        "version": {"type": "string", "enum": ["1"]},
        "txn_type": {"type": "string"},
        "custom_indexes": {"type": "array", "items": custom_index_items, "maxItems": MAX_CUSTOM_INDEXES},
    },
    "additionalProperties": False,
    "required": ["version", "txn_type"],
}


update_transaction_type_request_schema_v1 = {
    "type": "object",
    "properties": {
        "version": {"type": "string", "enum": ["1"]},
        "custom_indexes": {"type": "array", "items": custom_index_items, "maxItems": MAX_CUSTOM_INDEXES},
    },
    "additionalProperties": False,
    "required": ["version", "custom_indexes"],
}

set_default_interchain_schema_v1 = {
    "type": "object",
    "properties": {"version": {"type": "string", "enum": ["1"]}, "blockchain": {"type": "string"}, "name": {"type": "string"}},
}

# BITCOIN INTERCHAIN #

create_bitcoin_interchain_schema_v1 = {
    "type": "object",
    "properties": {
        "version": {"type": "string", "enum": ["1"]},
        "name": {"type": "string"},
        "testnet": {"type": "boolean"},
        "private_key": {"type": "string"},
        "utxo_scan": {"type": "boolean"},
        "rpc_address": {"type": "string"},
        "rpc_authorization": {"type": "string"},
    },
    "additionalProperties": False,
    "required": ["name", "version"],
}

# Same as create without required name field
update_bitcoin_interchain_schema_v1 = {
    "type": "object",
    "properties": {
        "version": {"type": "string", "enum": ["1"]},
        "testnet": {"type": "boolean"},
        "private_key": {"type": "string"},
        "utxo_scan": {"type": "boolean"},
        "rpc_address": {"type": "string"},
        "rpc_authorization": {"type": "string"},
    },
    "additionalProperties": False,
    "required": ["version"],
}


btc_transaction_schema_v1 = {
    "type": "object",
    "properties": {
        "outputs": {"type": "array", "items": {"type": "object", "properties": {"to": {"type": "string"}, "value": {"type": "number"}}}},
        "fee": {"type": "integer"},
        "data": {"type": "string"},
        "change": {"type": "string"},
    },
    "additionalProperties": False,
}

# ETHEREUM INTERCHAIN #

create_ethereum_interchain_schema_v1 = {
    "type": "object",
    "properties": {
        "version": {"type": "string", "enum": ["1"]},
        "name": {"type": "string"},
        "private_key": {"type": "string"},
        "rpc_address": {"type": "string"},
        "chain_id": {"type": "integer"},
    },
    "additionalProperties": False,
    "required": ["name", "version"],
}

# Same as create without required name field
update_ethereum_interchain_schema_v1 = {
    "type": "object",
    "properties": {
        "version": {"type": "string", "enum": ["1"]},
        "private_key": {"type": "string"},
        "rpc_address": {"type": "string"},
        "chain_id": {"type": "integer"},
    },
    "additionalProperties": False,
    "required": ["version"],
}


eth_transaction_schema_v1 = {
    "type": "object",
    "properties": {
        "to": {"type": "string"},
        "value": {"type": "string"},
        "data": {"type": "string"},
        "gasPrice": {"type": "string"},
        "gas": {"type": "string"},
        "nonce": {"type": "string"},
    },
    "required": ["to", "value"],
    "additionalProperties": False,
}
