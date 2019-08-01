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

import json
import unittest
from unittest.mock import patch, ANY, MagicMock

from dragonchain import test_env  # noqa: F401
from dragonchain.lib.database import elasticsearch
from dragonchain.lib.dto import l1_block_model
from dragonchain import exceptions


def fake_es_search(self):
    return "whocares"


@patch("dragonchain.lib.database.elasticsearch.elasticsearch.helpers")
@patch("dragonchain.lib.database.elasticsearch.storage.put_object_as_json")
@patch("dragonchain.lib.database.elasticsearch.storage.get_json_from_object")
@patch("dragonchain.lib.database.elasticsearch._set_elastic_search_client_if_necessary")
class TestElasticIndexedStorage(unittest.TestCase):
    @patch("dragonchain.lib.database.elasticsearch._set_elastic_search_client_if_necessary")
    def setUp(self, get_elastic_client_mock):
        self.elasticsearch = elasticsearch
        self.elasticsearch._set_elastic_search_client_if_necessary = MagicMock()
        self.elasticsearch._es_client = MagicMock()
        self.elasticsearch.INTERNAL_ID = "MixedCase-Internal-ID"

    # get_index_only
    def test_get_index_only_throws_error_when_both_q_qnd_query_are_none(self, get_elastic_client_mock, storage_get_mock, storage_put_mock, helpers):
        self.assertRaises(exceptions.ValidationException, elasticsearch.get_index_only, None, None)

    def test_get_index_only_calls_elastic_search_with_correct_index(self, get_elastic_client_mock, storage_get_mock, storage_put_mock, helpers):
        self.elasticsearch.get_index_only("BananaFolder", q="foo")
        self.elasticsearch._es_client.search.assert_called_with(index="mixedcase-internal-id-bananafolder", q="foo")

        self.elasticsearch.get_index_only("BananaFolder", query="foo.bar:banana")
        self.elasticsearch._es_client.search.assert_called_with(index="mixedcase-internal-id-bananafolder", body="foo.bar:banana")

    # put_index
    def test_put_index_raises_error_when_structured_data_is_not_data_model(
        self, get_elastic_client_mock, storage_get_mock, storage_put_mock, helpers
    ):
        self.assertRaises(AttributeError, self.elasticsearch.put_index_in_storage, "BananaFolder", "MyNameSpace", "A string! OhNoes!")

    def test_put_index_creates_index_correctly(self, get_elastic_client_mock, storage_get_mock, storage_put_mock, helpers):
        model = l1_block_model.L1BlockModel(dc_id="one", block_id="2", timestamp="123", prev_id="0", prev_proof="apple")
        self.elasticsearch.put_index_in_storage("BananaFolder", "", model)
        self.elasticsearch._es_client.index.assert_called_with(
            body=json.dumps(
                {
                    "version": "1",
                    "dcrn": "Block::L1::SearchIndex",
                    "dc_id": "one",
                    "block_id": 2,
                    "timestamp": 123,
                    "prev_id": 0,
                    "prev_proof": "apple",
                    "s3_object_folder": "BLOCK",
                    "s3_object_id": "2",
                    "l2_verifications": 0,
                    "l3_verifications": 0,
                    "l4_verifications": 0,
                    "l5_verifications": 0,
                },
                separators=(",", ":"),
            ),
            doc_type="_doc",
            id="",
            index="mixedcase-internal-id-bananafolder",
        )

        # ...if a subclass adds a folder
        self.elasticsearch.put_index_in_storage("BananaFolder", "", model)
        self.elasticsearch._es_client.index.assert_called_with(
            body=json.dumps(
                {
                    "version": "1",
                    "dcrn": "Block::L1::SearchIndex",
                    "dc_id": "one",
                    "block_id": 2,
                    "timestamp": 123,
                    "prev_id": 0,
                    "prev_proof": "apple",
                    "s3_object_folder": "BLOCK",
                    "s3_object_id": "2",
                    "l2_verifications": 0,
                    "l3_verifications": 0,
                    "l4_verifications": 0,
                    "l5_verifications": 0,
                },
                separators=(",", ":"),
            ),
            doc_type="_doc",
            id="",
            index="mixedcase-internal-id-bananafolder",
        )

    def test_put_index_calls_es_index_correctly(self, get_elastic_client_mock, storage_get_mock, storage_put_mock, helpers):
        model = l1_block_model.L1BlockModel(dc_id="one", block_id="2", timestamp="123", prev_id="0", prev_proof="apple")
        model2 = l1_block_model.L1BlockModel(dc_id="one", block_id="3", timestamp="123", prev_id="2", prev_proof="banana")
        self.elasticsearch.put_many_index_only("BananaFolder", {model, model2})
        helpers.bulk.assert_called_with(ANY, ANY, index="mixedcase-internal-id-bananafolder")

    def test_custom_index_with_header(self, get_elastic_client_mock, storage_get_mock, storage_put_mock, helpers):
        model = l1_block_model.L1BlockModel(dc_id="one", block_id="2", timestamp="123", prev_id="0", prev_proof="apple")
        self.elasticsearch.put_index_in_storage("BananaFolder", "MyUniqueId", model)
        self.elasticsearch._es_client.index.assert_called_with(
            body=json.dumps(
                {
                    "version": "1",
                    "dcrn": "Block::L1::SearchIndex",
                    "dc_id": "one",
                    "block_id": 2,
                    "timestamp": 123,
                    "prev_id": 0,
                    "prev_proof": "apple",
                    "s3_object_folder": "BLOCK",
                    "s3_object_id": "2",
                    "l2_verifications": 0,
                    "l3_verifications": 0,
                    "l4_verifications": 0,
                    "l5_verifications": 0,
                },
                separators=(",", ":"),
            ),
            doc_type="_doc",
            id="MyUniqueId",
            index="mixedcase-internal-id-bananafolder",
        )
