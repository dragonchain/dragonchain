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
import unittest
from unittest.mock import patch, MagicMock

import redis

from dragonchain import test_env  # noqa: F401
from dragonchain.lib.database import redisearch


class TestRedisearch(unittest.TestCase):
    def test_get_custom_field_from_input_tag_with_opts(self):
        index = redisearch._get_custom_field_from_input(
            {"path": "ba/na/na", "field_name": "banana", "type": "tag", "options": {"separator": ".", "no_index": "true"}}
        )
        self.assertEqual(index.name, "banana")
        self.assertTrue(index.NOINDEX)
        self.assertEqual(index.args[index.args.index("SEPARATOR") + 1], ".")

    def test_get_custom_field_from_input_text_with_opts(self):
        index = redisearch._get_custom_field_from_input(
            {
                "path": "ba/na/na",
                "field_name": "banana",
                "type": "text",
                "options": {"weight": 0.4, "sortable": "true", "no_stem": "true", "no_index": "true"},
            }
        )
        self.assertEqual(index.name, "banana")
        self.assertTrue(index.SORTABLE)
        self.assertTrue(index.NOSTEM)
        self.assertTrue(index.NOINDEX)
        self.assertEqual(index.args[index.args.index("WEIGHT") + 1], 0.4)

    def test_get_custom_field_from_input_number_with_opts(self):
        index = redisearch._get_custom_field_from_input(
            {"path": "ba/na/na", "field_name": "banana", "type": "number", "options": {"sortable": "true", "no_index": "true"}}
        )
        self.assertEqual(index.name, "banana")
        self.assertTrue(index.NOINDEX)
        self.assertTrue(index.SORTABLE)

    def test_get_custom_field_from_input_throws_runtimeerror(self):
        self.assertRaises(RuntimeError, redisearch._get_custom_field_from_input, {"field_name": "banana", "type": "banana"})

    def test_get_escaped_redisearch_string(self):
        output = redisearch.get_escaped_redisearch_string(",.<>{}[]\"':;!@#$%^&*()-+=~ ")
        self.assertEqual(output, "\\,\\.\\<\\>\\{\\}\\[\\]\\\"\\'\\:\\;\\!\\@\\#\\$\\%\\^\\&\\*\\(\\)\\-\\+\\=\\~\\ ")

    @patch("dragonchain.lib.database.redisearch.delete_index")
    def test_create_transaction_index(self, mock_delete_index):
        mock_create_index = MagicMock()
        redisearch._get_redisearch_index_client = MagicMock(return_value=MagicMock(create_index=mock_create_index))
        redisearch.create_transaction_index("banana", [{"path": "ba/na/na", "field_name": "banana", "type": "number"}])
        mock_delete_index.assert_called_once_with("banana")
        redisearch._get_redisearch_index_client.assert_called_once_with("banana")
        mock_create_index.assert_called_once()

    def test_delete_index_exists(self):
        mock_drop_index = MagicMock()
        redisearch._get_redisearch_index_client = MagicMock(return_value=MagicMock(drop_index=mock_drop_index))
        redisearch.delete_index("banana")
        redisearch._get_redisearch_index_client.assert_called_once_with("banana")
        mock_drop_index.assert_called_once()

    def test_delete_index_doesnt_exist(self):
        mock_drop_index = MagicMock(side_effect=redis.exceptions.ResponseError("Unknown Index name"))
        redisearch._get_redisearch_index_client = MagicMock(return_value=MagicMock(drop_index=mock_drop_index))
        redisearch.delete_index("banana")
        redisearch._get_redisearch_index_client.assert_called_once_with("banana")
        mock_drop_index.assert_called_once()

    @patch("dragonchain.lib.database.redisearch.redisearch.Query")
    def test_search_all_options(self, mock_query):
        mock_search = MagicMock()
        redisearch._get_redisearch_index_client = MagicMock(return_value=MagicMock(search=mock_search))
        mock_query_params = MagicMock()
        mock_query.return_value = MagicMock(paging=MagicMock(return_value=mock_query_params))
        redisearch.search(index="banana", query_str="100", only_id=True, verbatim=True, offset=5, limit=100, sort_by="timestamp", sort_asc=False)
        redisearch._get_redisearch_index_client.assert_called_once_with("banana")
        mock_query.assert_called_once_with("100")
        mock_search.assert_called_once_with(mock_query_params)

    def test_get_document(self):
        mock_load_document = MagicMock()
        redisearch._get_redisearch_index_client = MagicMock(return_value=MagicMock(load_document=mock_load_document))
        redisearch.get_document("banana", "document1")
        redisearch._get_redisearch_index_client.assert_called_once_with("banana")
        mock_load_document.assert_called_once_with("document1")

    def test_get_document_count(self):
        mock_info = MagicMock(return_value={"num_docs": "10"})
        redisearch._get_redisearch_index_client = MagicMock(return_value=MagicMock(info=mock_info))
        count = redisearch.get_document_count("banana")
        self.assertEqual(count, 10)
        redisearch._get_redisearch_index_client.assert_called_once_with("banana")
        mock_info.assert_called_once_with()

    def test_put_document_success(self):
        mock_add_document = MagicMock()
        redisearch._get_redisearch_index_client = MagicMock(return_value=MagicMock(add_document=mock_add_document))
        redisearch.put_document(index="banana", doc_name="doc1", fields={"fruit": "apple"})
        mock_add_document.assert_called_once_with("doc1", replace=False, fruit="apple", partial=False)

    def test_put_document_upsert(self):
        mock_add_document = MagicMock()
        redisearch._get_redisearch_index_client = MagicMock(return_value=MagicMock(add_document=mock_add_document))
        redisearch.put_document(index="banana", doc_name="doc1", fields={"fruit": "apple"}, upsert=True)
        mock_add_document.assert_called_once_with("doc1", replace=True, fruit="apple", partial=False)

    def test_put_document_partial_update(self):
        mock_add_document = MagicMock()
        redisearch._get_redisearch_index_client = MagicMock(return_value=MagicMock(add_document=mock_add_document))
        redisearch.put_document(index="banana", doc_name="doc1", fields={"fruit": "apple"}, partial_update=True)
        mock_add_document.assert_called_once_with("doc1", replace=True, fruit="apple", partial=True)

    def test_put_document_mutually_exclusive_options(self):
        redisearch._get_redisearch_index_client = MagicMock()
        self.assertRaises(
            RuntimeError, redisearch.put_document, index="banana", doc_name="doc1", fields={"fruit": "apple"}, upsert=True, partial_update=True
        )

    def test_put_many_documents(self):
        mock_indexer = MagicMock(return_value=MagicMock(add_document=MagicMock(), commit=MagicMock()))
        redisearch._get_redisearch_index_client = MagicMock(return_value=MagicMock(batch_indexer=mock_indexer))
        redisearch.put_many_documents(index="banana", documents={"doc1": {"fruit": "apple"}, "doc2": {"vegetable": "avocado"}})
        mock_indexer.assert_called_once_with(chunk_size=1000)
        mock_indexer.return_value.add_document.assert_any_call("doc1", fruit="apple", replace=False, partial=False)
        mock_indexer.return_value.add_document.assert_any_call("doc2", vegetable="avocado", replace=False, partial=False)
        self.assertEqual(2, mock_indexer.return_value.add_document.call_count)
        mock_indexer.return_value.commit.assert_called_once()

    def test_put_many_documents_respects_params(self):
        mock_indexer = MagicMock(return_value=MagicMock(add_document=MagicMock(), commit=MagicMock()))
        redisearch._get_redisearch_index_client = MagicMock(return_value=MagicMock(batch_indexer=mock_indexer))
        redisearch.put_many_documents(index="banana", documents={"doc1": {"fruit": "apple"}, "doc2": {"vegetable": "avocado"}}, partial_update=True)
        mock_indexer.assert_called_once_with(chunk_size=1000)
        mock_indexer.return_value.add_document.assert_any_call("doc1", fruit="apple", replace=True, partial=True)
        mock_indexer.return_value.add_document.assert_any_call("doc2", vegetable="avocado", replace=True, partial=True)
        self.assertEqual(2, mock_indexer.return_value.add_document.call_count)
        mock_indexer.return_value.commit.assert_called_once()

    def test_put_many_documents_mutually_exclusive_options(self):
        mock_indexer = MagicMock(return_value=MagicMock(add_document=MagicMock(), commit=MagicMock()))
        redisearch._get_redisearch_index_client = MagicMock(return_value=MagicMock(batch_indexer=mock_indexer))
        self.assertRaises(
            RuntimeError,
            redisearch.put_many_documents,
            index="banana",
            documents={"doc1": {"fruit": "apple"}, "doc2": {"vegetable": "avocado"}},
            upsert=True,
            partial_update=True,
        )
        mock_indexer.assert_called_once_with(chunk_size=1000)

    def test_delete_document(self):
        mock_delete_document = MagicMock()
        redisearch._get_redisearch_index_client = MagicMock(return_value=MagicMock(delete_document=mock_delete_document))
        redisearch.delete_document("banana", "doc1")
        redisearch._get_redisearch_index_client.assert_called_once_with("banana")
        mock_delete_document.assert_called_once_with("doc1")

    @patch("dragonchain.lib.database.redisearch.put_document")
    @patch("dragonchain.lib.database.redisearch.storage.list_objects", return_value=["BLOCK/12345"])
    @patch("dragonchain.lib.database.redisearch.storage.get_json_from_object")
    @patch("dragonchain.lib.database.redisearch.l1_block_model.new_from_stripped_block")
    @patch(
        "dragonchain.lib.database.redisearch.transaction_type_model.new_from_at_rest",
        return_value=MagicMock(txn_type="banana", custom_indexes=[], active_since_block=1),
    )
    def test_generate_indexes_if_necessary(self, mock_put_document, mock_list, mock_get_json, mock_new_l1, mock_new_txn_type):
        os.environ["LEVEL"] = "1"
        mock_redis = MagicMock(get=MagicMock(return_value=False))
        redisearch._get_redisearch_index_client = MagicMock(return_value=MagicMock(redis=mock_redis))
        redisearch.generate_indexes_if_necessary()
        redisearch._get_redisearch_index_client.assert_any_call("")
        redisearch._get_redisearch_index_client.assert_any_call("bk")
        redisearch._get_redisearch_index_client.assert_any_call("sc")
        redisearch._get_redisearch_index_client.assert_any_call("tx")
        mock_redis.get.assert_called_once_with("dc:index_generation_complete")
        mock_redis.set.assert_called_once()
        mock_put_document.assert_called()
