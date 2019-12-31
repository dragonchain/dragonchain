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

import json
import unittest
from unittest.mock import patch

import fastjsonschema

from dragonchain import test_env  # noqa: F401
from dragonchain.lib.dto import schema
from dragonchain.lib.dto import model
from dragonchain.lib.dto import smart_contract_model
from dragonchain.lib.dto import transaction_model
from dragonchain.lib.dto import l1_block_model
from dragonchain.lib.dto import l2_block_model
from dragonchain.lib.dto import l3_block_model
from dragonchain.lib.dto import l4_block_model


def create_sc():
    return smart_contract_model.SmartContractModel(
        env={"a variable": "a value"},
        execution_order="serial",
        sc_id="an id",
        status={"msg": "good", "state": "active"},
        txn_type="type",
        image="docker",
        cmd="command",
        existing_secrets=[],
        secrets={},
        cron="",
        seconds=1,
    )


def create_tx():
    return transaction_model.TransactionModel(
        dc_id="dc_id",
        block_id="123",
        txn_id="txn_id",
        timestamp="12345",
        txn_type="test",
        tag="tag",
        payload="payload",
        signature="signature",
        full_hash="full_hash",
        invoker="invoker",
    )


def create_l1_block():
    return l1_block_model.L1BlockModel(
        dc_id="dc_id",
        block_id="123",
        timestamp="12345",
        prev_proof="prev_proof",
        prev_id="101",
        transactions=[create_tx()],
        scheme="trust",
        proof="proof",
    )


def create_l2_block():
    return l2_block_model.L2BlockModel(
        dc_id="dc_id",
        block_id="123",
        timestamp="12345",
        prev_proof="prev_proof",
        scheme="trust",
        proof="proof",
        l1_dc_id="l1_dc_id",
        l1_block_id="l1_block_id",
        l1_proof="l1_proof",
        validations_str='{"tx_id1":true,"tx_id2":false}',
    )


def create_l3_block():
    return l3_block_model.L3BlockModel(
        dc_id="dc_id",
        block_id="123",
        timestamp="12345",
        prev_proof="prev_proof",
        scheme="trust",
        proof="proof",
        l1_dc_id="l1_dc_id",
        l1_block_id="l1_block_id",
        l1_proof="l1_proof",
        ddss="123",
        l2_count="3",
        regions=["region"],
        clouds=["cloud"],
    )


def create_l4_block():
    return l4_block_model.L4BlockModel(
        dc_id="an id",
        block_id="123",
        timestamp="129874",
        prev_proof="the previous block proof",
        scheme="trust",
        proof="proof",
        l1_dc_id="l1 dc id",
        l1_block_id="123",
        l1_proof="l1 block proof",
        validations=[{"l3_dc_id": "l3 dc id", "l3_block_id": "123", "l3_proof": "l3 block proof", "valid": True}],
    )


class TestModel(unittest.TestCase):
    def test_abstract_model(self):
        test_model = model.Model()
        self.assertRaises(NotImplementedError, test_model.export_as_at_rest)
        self.assertRaises(NotImplementedError, test_model.export_as_search_index)


class TestBlockModel(unittest.TestCase):
    def test_abstract_block(self):
        test_model = model.BlockModel()
        self.assertRaises(NotImplementedError, test_model.get_associated_l1_block_id)
        self.assertRaises(NotImplementedError, test_model.get_associated_l1_dcid)

    def test_search_index_schema(self):
        l1block = create_l1_block()
        fastjsonschema.validate(schema.block_search_index_schema, l1block.export_as_search_index())


class TestSmartContract(unittest.TestCase):
    def test_from_input(self):
        meta = {
            "version": "3",
            "env": {"a_variable": "a value"},
            "txn_type": "an txn_type",
            "id": "an id",
            "image": "docker/image:1.0.0",
            "status": "a status",
            "cmd": "none?",
            "execution_order": "serial",
        }
        fastjsonschema.validate(schema.smart_contract_create_schema_v1, meta)
        test = smart_contract_model.new_contract_from_user(meta)
        for key in meta.keys():
            if key != "id" and key != "status" and key != "version":
                self.assertEqual(test.__dict__[key], meta[key])
        meta["version"] = "1"
        test = smart_contract_model.new_from_at_rest(meta)
        del meta["version"]
        for key in meta.keys():
            self.assertEqual(test.__dict__[key], meta[key])

    def test_seconds_low_range(self):
        meta = {
            "version": "latest",
            "env": {"a variable": "a value"},
            "txn_type": "an txn_type",
            "id": "an id",
            "image": "docker/image:1.0.0",
            "status": "a status",
            "cmd": "none?",
            "execution_order": "serial",
            "seconds": 0,
        }
        try:
            fastjsonschema.validate(schema.smart_contract_create_schema_v1, meta)
        except fastjsonschema.JsonSchemaException as e:
            self.assertEqual(str(e), "data.seconds must be bigger than or equal to 1")
            return
        self.assertFail()  # Force test failure if validation does not throw

    def test_seconds_high_range(self):
        meta = {
            "version": "latest",
            "env": {"a variable": "a value"},
            "txn_type": "an txn_type",
            "id": "an id",
            "image": "docker/image:1.0.0",
            "status": "a status",
            "cmd": "none?",
            "execution_order": "serial",
            "seconds": 61,
        }
        try:
            fastjsonschema.validate(schema.smart_contract_create_schema_v1, meta)
        except fastjsonschema.JsonSchemaException as e:
            self.assertEqual(str(e), "data.seconds must be smaller than or equal to 60")
            return
        self.assertFail()  # Force test failure if validation does not throw

    def test_export_schema(self):
        sc = create_sc()
        fastjsonschema.validate(schema.smart_contract_at_rest_schema, sc.export_as_at_rest())
        fastjsonschema.validate(schema.smart_contract_index_schema, sc.export_as_search_index())


class TestTransaction(unittest.TestCase):
    def test_from_input(self):
        meta = {
            "txn_type": "sotmething",
            "dc_id": "an id",
            "txn_id": "another id",
            "timestamp": "123456",
            "payload": "a payload",
            "tag": "a tag",
            "invoker": "a sweet invoker id",
            "full_hash": "a full hash",
            "signature": "a signature",
        }
        # Test new_from_user_input
        create_task = {"txn_type": meta["txn_type"], "payload": meta["payload"], "tag": meta["tag"]}
        user_input = {"version": "1", "txn_type": meta["txn_type"], "payload": meta["payload"], "tag": meta["tag"]}
        test = transaction_model.new_from_user_input(user_input)
        for key in create_task.keys():
            self.assertEqual(test.__dict__[key], meta[key])
        # Test new_from_queue_input
        queue_task = {
            "version": "2",
            "header": {
                "txn_type": meta["txn_type"],
                "dc_id": meta["dc_id"],
                "txn_id": meta["txn_id"],
                "timestamp": meta["timestamp"],
                "tag": meta["tag"],
                "invoker": meta["invoker"],
            },
            "payload": meta["payload"],
        }
        test = transaction_model.new_from_queue_input(queue_task)
        for key in meta.keys():
            if key != "full_hash" and key != "signature":
                self.assertEqual(test.__dict__[key], meta[key])
        # Test new_from_stripped_block_input
        txn = transaction_model.TransactionModel(**meta)
        test = transaction_model.new_from_stripped_block_input(json.dumps(txn.export_as_stripped(), separators=(",", ":")))
        for key in meta.keys():
            if key != "payload":
                self.assertEqual(test.__dict__[key], meta[key])

    def test_export_schemas(self):
        txn = create_tx()
        txn_id = "an id"
        txn.txn_id = txn_id
        fastjsonschema.validate(schema.transaction_full_schema, txn.export_as_full())
        fastjsonschema.validate(schema.transaction_stripped_schema, txn.export_as_stripped())
        fastjsonschema.validate(schema.get_transaction_queue_task_schema(), txn.export_as_queue_task())
        fastjsonschema.validate(schema.transaction_search_index_schema, txn.export_as_search_index())

    def test_new_from_at_rest_full(self):
        txn = {
            "version": "2",
            "header": {
                "dc_id": "bananachain",
                "block_id": "1234",
                "txn_id": "4321",
                "timestamp": "no",
                "txn_type": "bananatype",
                "tag": "banana = 4",
                "invoker": "1-2-3-4",
            },
            "proof": {"full": "asdfqwerty", "stripped": "asdf"},
            "payload": "asdfqwertyproofbanana4",
        }
        model = transaction_model.new_from_at_rest_full(txn)
        self.assertEqual(model.dc_id, "bananachain")
        self.assertEqual(model.block_id, "1234")
        self.assertEqual(model.txn_id, "4321")
        self.assertEqual(model.timestamp, "no")
        self.assertEqual(model.txn_type, "bananatype")
        self.assertEqual(model.tag, "banana = 4")
        self.assertEqual(model.invoker, "1-2-3-4")
        self.assertEqual(model.full_hash, "asdfqwerty")
        self.assertEqual(model.signature, "asdf")
        self.assertEqual(model.payload, "asdfqwertyproofbanana4")


class TestL1Block(unittest.TestCase):
    def test_setting_validations(self):
        l1block = l1_block_model.L1BlockModel(dc_id="a", block_id="b")
        self.assertEqual(l1block.get_associated_l1_dcid(), "a")
        self.assertEqual(l1block.get_associated_l1_block_id(), {"b"})

    def test_stripped_schema(self):
        l1block = create_l1_block()
        fastjsonschema.validate(schema.l1_block_at_rest_schema, l1block.export_as_at_rest())

    def test_create_from_at_rest(self):
        first_block = create_l1_block()
        second_block = l1_block_model.new_from_stripped_block(first_block.export_as_at_rest())
        # Need to remove transactions from original block (only stripped exist) for verification
        first_block.transactions = []
        self.assertDictEqual(first_block.__dict__, second_block.__dict__)

    @patch("dragonchain.lib.dto.l1_block_model.keys.get_public_id")
    @patch("dragonchain.lib.dto.l1_block_model.get_current_block_id", return_value="123")
    def test_create_from_transactions(self, mock_current_block_id, mock_get_id):
        self.assertRaises(TypeError, l1_block_model.new_from_full_transactions, "a string", "123", "1", "proof")
        self.assertRaises(TypeError, l1_block_model.new_from_full_transactions, ["not a txn"], "123", "1", "proof")
        txn = create_tx()
        test = l1_block_model.new_from_full_transactions([txn], "123", "prev_id", "prev_proof")
        self.assertEqual(test.prev_proof, "prev_proof")
        self.assertEqual(test.prev_id, "prev_id")
        self.assertDictEqual(txn.__dict__, test.transactions[0].__dict__)

    def test_nd_json_export(self):
        tx_id_1 = "a cool id"
        tx_id_2 = "another cool id"
        tx1 = create_tx()
        tx2 = create_tx()
        tx1.txn_id = tx_id_1
        tx2.txn_id = tx_id_2
        l1block = create_l1_block()
        l1block.transactions = [tx1, tx2]
        to_validate = l1block.export_as_full_transactions().splitlines()
        self.assertEqual(json.loads(to_validate[0])["txn_id"], tx_id_1)
        self.assertDictEqual(json.loads(to_validate[0])["txn"], tx1.export_as_full())
        self.assertEqual(json.loads(to_validate[1])["txn_id"], tx_id_2)
        self.assertDictEqual(json.loads(to_validate[1])["txn"], tx2.export_as_full())


class TestL2Block(unittest.TestCase):
    def test_setting_validations(self):
        l2block = l2_block_model.L2BlockModel()
        test_dict = {"tx_id1": True, "tx_id2": False}
        test_string = json.dumps(test_dict, separators=(",", ":"))
        l2block.set_validations_dict(test_dict)
        self.assertEqual(l2block.validations_str, test_string)
        l2block.set_validations_str(test_string)
        self.assertDictEqual(l2block.validations_dict, test_dict)
        l2block = l2_block_model.L2BlockModel(validations_dict=test_dict)
        self.assertEqual(l2block.validations_str, test_string)
        l2block = l2_block_model.L2BlockModel(l1_block_id="l1_block_id", l1_dc_id="l1_dc_id")
        self.assertEqual(l2block.get_associated_l1_block_id(), {"l1_block_id"})
        self.assertEqual(l2block.get_associated_l1_dcid(), "l1_dc_id")

    def test_at_rest_schema(self):
        l2block = create_l2_block()
        fastjsonschema.validate(schema.l2_block_at_rest_schema, l2block.export_as_at_rest())
        l2block.nonce = 1
        l2block.scheme = "work"
        fastjsonschema.validate(schema.l2_block_at_rest_schema, l2block.export_as_at_rest())

    def test_create_from_at_rest(self):
        first_block = create_l2_block()
        second_block = l2_block_model.new_from_at_rest(first_block.export_as_at_rest())
        self.assertDictEqual(first_block.__dict__, second_block.__dict__)


class TestL3Block(unittest.TestCase):
    def test_setting_validations(self):
        l3block = l3_block_model.L3BlockModel(l1_block_id="l1_block_id", l1_dc_id="l1_dc_id")
        self.assertEqual(l3block.get_associated_l1_block_id(), {"l1_block_id"})
        self.assertEqual(l3block.get_associated_l1_dcid(), "l1_dc_id")

    def test_at_rest_schema(self):
        l3block = create_l3_block()
        fastjsonschema.validate(schema.l3_block_at_rest_schema, l3block.export_as_at_rest())
        l3block.nonce = 1
        l3block.scheme = "work"
        fastjsonschema.validate(schema.l3_block_at_rest_schema, l3block.export_as_at_rest())

    def test_create_from_at_rest(self):
        first_block = create_l3_block()
        second_block = l3_block_model.new_from_at_rest(first_block.export_as_at_rest())
        self.assertDictEqual(first_block.__dict__, second_block.__dict__)


class TestL4Block(unittest.TestCase):
    def test_setting_validations(self):
        l4 = l4_block_model.L4BlockModel(l1_block_id="l1_block_id", l1_dc_id="l1_dc_id")
        self.assertEqual(l4.get_associated_l1_block_id(), {"l1_block_id"})
        self.assertEqual(l4.get_associated_l1_dcid(), "l1_dc_id")

    def test_at_rest_schema(self):
        l4block = create_l4_block()
        fastjsonschema.validate(schema.l4_block_at_rest_schema, l4block.export_as_at_rest())
        l4block.nonce = 1
        l4block.scheme = "work"
        fastjsonschema.validate(schema.l4_block_at_rest_schema, l4block.export_as_at_rest())

    def test_create_from_at_rest(self):
        first_block = create_l4_block()
        second_block = l4_block_model.new_from_at_rest(first_block.export_as_at_rest())
        self.assertDictEqual(first_block.__dict__, second_block.__dict__)
