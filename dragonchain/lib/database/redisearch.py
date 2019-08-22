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

import re
import os
import enum
import json
from typing import cast, Dict, Any, Iterable, Optional, TYPE_CHECKING

import redis
import redisearch

from dragonchain.lib.database import redis as dragonchain_redis
from dragonchain.lib.interfaces import storage
from dragonchain.lib.dto import l1_block_model
from dragonchain.lib.dto import l2_block_model
from dragonchain.lib.dto import l3_block_model
from dragonchain.lib.dto import l4_block_model
from dragonchain.lib.dto import l5_block_model
from dragonchain.lib.dto import transaction_model
from dragonchain.lib.dto import smart_contract_model
from dragonchain.lib.dao import transaction_type_dao
from dragonchain.lib.dto import transaction_type_model
from dragonchain.lib import namespace
from dragonchain import logger

if TYPE_CHECKING:
    from dragonchain.lib.types import custom_index
    from dragonchain.lib.dto import model  # noqa: F401

_log = logger.get_logger()

LEVEL = os.environ["LEVEL"]
REDISEARCH_ENDPOINT = os.environ["REDISEARCH_ENDPOINT"]
REDIS_PORT = int(os.environ["REDIS_PORT"]) or 6379

INDEX_GENERATION_KEY = "dc:index_generation_complete"

_escape_transformation = str.maketrans(
    {
        ",": "\\,",
        ".": "\\.",
        "<": "\\<",
        ">": "\\>",
        "{": "\\{",
        "}": "\\}",
        "[": "\\[",
        "]": "\\]",
        '"': '\\"',
        "'": "\\'",
        ":": "\\:",
        ";": "\\;",
        "!": "\\!",
        "@": "\\@",
        "#": "\\#",
        "$": "\\$",
        "%": "\\%",
        "^": "\\^",
        "&": "\\&",
        "*": "\\*",
        "(": "\\(",
        ")": "\\)",
        "-": "\\-",
        "+": "\\+",
        "=": "\\=",
        "~": "\\~",
        " ": "\\ ",
    }
)


class Indexes(enum.Enum):
    block = "bk"
    smartcontract = "sc"
    transaction = "tx"


_redis_connection = None


# Until redisearch is fixed (https://github.com/RediSearch/redisearch-py/pull/37) for args, we have to use our own (fixed) tag class
class TagField(redisearch.client.Field):  # noqa: F484
    """
    TagField is a tag-indexing field with simpler compression and tokenization.
    See http://redisearch.io/Tags/
    """

    def __init__(self, name, separator=",", no_index=False):
        args = [redisearch.client.Field.TAG, redisearch.client.Field.SEPARATOR, separator]
        if no_index:
            args.append(redisearch.client.Field.NOINDEX)
        redisearch.client.Field.__init__(self, name, *args)


def _get_redisearch_index_client(index: str) -> redisearch.Client:
    """Get an initialized redisearch client for an index
    Args:
        index: Enum for the relevant index
    Returns:
        Initialized redisearch client for given index
    """
    global _redis_connection
    if _redis_connection is None:
        _redis_connection = dragonchain_redis._initialize_redis(host=REDISEARCH_ENDPOINT, port=REDIS_PORT)
    return redisearch.Client(index, conn=_redis_connection)


def _get_custom_field_from_input(custom_index_input: "custom_index") -> redisearch.client.Field:
    input_type = custom_index_input["type"]
    field_name = custom_index_input["field_name"]
    options = custom_index_input.get("options")
    if input_type == "text":
        weight = 1.0
        sortable = False
        no_stem = False
        no_index = False
        if options:
            sortable = bool(options.get("sortable"))
            no_stem = bool(options.get("no_stem"))
            no_index = bool(options.get("no_index"))
            cust_weight = options.get("weight")
            if isinstance(cust_weight, (int, float)) and cust_weight >= 0 and cust_weight <= 1:
                weight = float(cust_weight)
        return redisearch.TextField(field_name, weight=weight, sortable=sortable, no_stem=no_stem, no_index=no_index)
    elif input_type == "tag":
        separator = ","
        no_index = False
        if options:
            separator = options.get("separator") or ","
            no_index = bool(options.get("no_index"))
        return TagField(field_name, separator=separator, no_index=no_index)  # TODO: replace after redisearch is fixed
    elif input_type == "number":
        sortable = False
        no_index = False
        if options:
            sortable = bool(options.get("sortable"))
            no_index = bool(options.get("no_index"))
        return redisearch.NumericField(field_name, sortable=sortable, no_index=no_index)
    else:
        raise RuntimeError(f"Index type {input_type} is not supported")


def get_escaped_redisearch_string(unescaped_string: str) -> str:
    return unescaped_string.translate(_escape_transformation)


def force_create_transaction_index(index: str, custom_indexes: Optional[Iterable["custom_index"]] = None) -> None:
    """Create (and overwrite if necessary) index for a transaction type with optional custom_indexes"""
    # Delete the index with this name if necessary
    delete_index(index)
    client = _get_redisearch_index_client(index)
    # Set standard transaction indexes
    index_fields = [
        redisearch.TextField("tag"),
        redisearch.NumericField("timestamp", sortable=True),
        redisearch.NumericField("block_id", sortable=True),
    ]
    # Add custom indexes if they exist
    if custom_indexes:
        for idx in custom_indexes:
            index_fields.append(_get_custom_field_from_input(idx))
    # Create the actual index
    client.create_index(index_fields)


def delete_index(index: str) -> None:
    """Force delete an index (and drop all its documents)"""
    client = _get_redisearch_index_client(index)
    try:
        client.drop_index()
    except redis.exceptions.ResponseError:
        pass


# Redisearch
def search(
    index: str,
    query_str: str,
    only_id: Optional[bool] = None,
    verbatim: Optional[bool] = None,
    offset: Optional[int] = None,
    limit: Optional[int] = None,
    sort_by: Optional[str] = None,
    sort_asc: Optional[bool] = None,
) -> redisearch.Result:
    """Do a search on the redisearch indexes
    Args:
        index: The index to search
        query_str: Redisearch search query syntax: https://oss.redislabs.com/redisearch/Query_Syntax.html
        only_id: whether or not to only fetch document ids, and not their contents (default true)
        verbatim: whether or not to use stemming for query expansion in the query_str
        offset: the offset to start the query from, this can be used for pagination (defaults to 0, aka the start of the query)
        limit: the number of results to fetch from the query (can be set to 0 to simply get a count of the query results)
        sort_by: the sortable field name to sort by for this query
        sort_asc: (Only relevant if sort_by is set), sort the results in ascending order if true, descending if false
    Returns:
        redisearch result object
    """
    # Set some sensible defaults
    only_id = True if only_id is None else only_id
    verbatim = False if verbatim is None else verbatim
    offset = 0 if offset is None else offset
    limit = 10 if limit is None else limit
    sort_by = "" if sort_by is None else sort_by
    sort_asc = True if sort_asc is None else sort_asc

    client = _get_redisearch_index_client(index)
    query = redisearch.Query(query_str).paging(offset, limit)
    if only_id:
        query.no_content()
    if verbatim:
        query.verbatim()
    if sort_by:
        query.sort_by(sort_by, sort_asc)
    return client.search(query)


def get_document(index: str, doc_name: str) -> redisearch.Document:
    """Get a document by id explicitly
    Args:
        index: The index to search
        doc_name: The document to fetch
    Returns:
        A redisearch document of the fetch
    NOTE:
        This will NEVER raise any sort of not found, the returned document will simply not have any fields besides id (and .payload = None)
        If using this function to check for document existence, you MUST check yourself
    """
    client = _get_redisearch_index_client(index)
    return client.load_document(doc_name)


def get_document_count(index: str) -> int:
    """Get the number of documents for an index
    Args:
        index: The index to search
    Returns:
        Number of documents in the index
    """
    client = _get_redisearch_index_client(index)
    return int(client.info()["num_docs"])


def put_document(index: str, doc_name: str, fields: Dict[str, Any], upsert: bool = False, partial_update: bool = False) -> None:
    """Add a document to an index
    Args:
        index: The index to add the document to
        doc_name: the name of the document to add. NOTE: This must be GLOBALLY unique for all indexes
        fields: Dictionary of fields to add (according to the index). i.e. {'block_id':1234,'timestamp':54321,'tag':'sometag'} for transactions
        upsert: If false, an exception will be thrown if the document already exists. If true, existing documents will be completely overwritten
        partial_update: If true and the document already exists, only update the provided fields, merging with the index's existing fields
            Note: upsert and partial_update are mutually exclusive
    """
    client = _get_redisearch_index_client(index)
    if upsert and partial_update:
        raise RuntimeError("Upsert and partial_update are mutually exclusive")
    client.add_document(doc_name, replace=upsert or partial_update, partial=partial_update, **fields)


def put_many_documents(index: str, documents: Dict[str, Dict[str, Any]], upsert: bool = False, partial_update: bool = False) -> None:
    """Add many documents to an index at once. This should be used for efficiency when many documents will be created at once
    Args:
        index: The index to add the documents to
        documents: dictionary of document names, with a value of their field/value dictionaries.
            i.e. {'bad04998-e028-4cde-b807-4feaea4efdb8':{'block_id':1234,'timestamp':54321,'tag':'sometag'}} for a transaction
        upsert: If false, an exception will be thrown if the document already exists. If true, existing documents will be completely overwritten
        partial_update: If true and the document already exists, only update the provided fields, merging with the index's existing fields
            Note: upsert and partial_update are mutually exclusive
    """
    client = _get_redisearch_index_client(index)
    batch_indexer = client.batch_indexer(chunk_size=1000)
    if upsert and partial_update:
        raise RuntimeError("Upsert and partial_update are mutually exclusive")
    for key, value in documents.items():
        batch_indexer.add_document(key, replace=upsert or partial_update, partial=partial_update, **value)
    batch_indexer.commit()


def delete_document(index: str, doc_name: str) -> None:
    """Remove an existing document from an index
    Args:
        index: The index to remove the document from
        doc_name: The document to remove
    """
    client = _get_redisearch_index_client(index)
    client.delete_document(doc_name)


def generate_indexes_if_necessary() -> None:
    """Initialize redisearch with necessary indexes and fill them from storage if migration has not been marked as complete"""
    redisearch_redis_client = _get_redisearch_index_client("").redis
    needs_generation = not bool(redisearch_redis_client.get(INDEX_GENERATION_KEY))
    # No-op if indexes are marked as already generated
    if not needs_generation:
        return
    # First flush the entire index database to generate from scratch
    redisearch_redis_client.flushall()
    # Create block index from scratch
    _log.info("Creating block indexes from scratch")
    _generate_block_indexes_from_scratch()
    # Create smart contract index from scratch
    _log.info("Creating smart contract indexes from scratch")
    _generate_smart_contract_indexes_from_scratch()
    # Create indexes for transaction types from scratch
    _log.info("Creating transaction indexes from scratch")
    _generate_transaction_indexes_from_scratch()
    # Mark index generation as complete (value doesn't matter)
    _log.info("Marking redisearch index generation complete")
    redisearch_redis_client.set(INDEX_GENERATION_KEY, "a")


def _generate_block_indexes_from_scratch() -> None:
    client = _get_redisearch_index_client(Indexes.block.value)
    client.create_index(
        [
            redisearch.NumericField("block_id", sortable=True),
            redisearch.NumericField("prev_id", sortable=True),
            redisearch.NumericField("timestamp", sortable=True),
        ]
    )
    _log.info("Listing all blocks in storage")
    block_paths = storage.list_objects("BLOCK/")
    pattern = re.compile(r"BLOCK\/[0-9]+$")
    for block_path in block_paths:
        if re.search(pattern, block_path):
            _log.info(f"Adding index for {block_path}")
            raw_block = storage.get_json_from_object(block_path)
            block = cast("model.BlockModel", None)
            if LEVEL == "1":
                block = l1_block_model.new_from_stripped_block(raw_block)
            elif LEVEL == "2":
                block = l2_block_model.new_from_at_rest(raw_block)
            elif LEVEL == "3":
                block = l3_block_model.new_from_at_rest(raw_block)
            elif LEVEL == "4":
                block = l4_block_model.new_from_at_rest(raw_block)
            elif LEVEL == "5":
                block = l5_block_model.new_from_at_rest(raw_block)
            put_document(Indexes.block.value, block.block_id, block.export_as_search_index())


def _generate_smart_contract_indexes_from_scratch() -> None:
    client = _get_redisearch_index_client(Indexes.smartcontract.value)
    client.create_index([TagField("sc_name")])  # TODO: replace after redisearch is fixed
    # Find what smart contracts exist in storage
    _log.info("Listing all smart contracts in storage")
    sc_object_paths = storage.list_objects("SMARTCONTRACT/")
    pattern = re.compile(r"SMARTCONTRACT\/.{36}\/metadata\.json$")
    for sc in sc_object_paths:
        if re.search(pattern, sc):
            sc_model = smart_contract_model.new_from_at_rest(storage.get_json_from_object(sc))
            _log.info(f"Adding index for smart contract {sc_model.id} ({sc_model.txn_type})")
            put_document(Indexes.smartcontract.value, sc_model.id, sc_model.export_as_search_index())


def _generate_transaction_indexes_from_scratch() -> None:
    client = _get_redisearch_index_client(Indexes.transaction.value)
    # TODO: replace after redisearch is fixed
    client.create_index([TagField("block_id")])  # Used for reverse-lookup of transactions by id (with no txn_type)
    force_create_transaction_index(namespace.Namespaces.Contract.value)  # Create the reserved txn type index
    txn_types_to_watch = {namespace.Namespaces.Contract.value: 1}  # Will be use when going through all stored transactions
    txn_type_models = {
        namespace.Namespaces.Contract.value: transaction_type_model.TransactionTypeModel(namespace.Namespaces.Contract.value, active_since_block="1")
    }
    for txn_type in transaction_type_dao.list_registered_transaction_types():
        txn_type_model = transaction_type_model.new_from_at_rest(txn_type)
        txn_type_models[txn_type_model.txn_type] = txn_type_model
        _log.info(f"Adding index for {txn_type_model.txn_type}")
        force_create_transaction_index(txn_type_model.txn_type, txn_type_model.custom_indexes)
        txn_types_to_watch[txn_type_model.txn_type] = int(txn_type_model.active_since_block)
    _log.info("Listing all full transactions")
    transaction_blocks = storage.list_objects("TRANSACTION/")
    for txn_path in transaction_blocks:
        _log.info(f"Indexing transactions for {txn_path}")
        for txn in storage.get(txn_path).split(b"\n"):
            if txn:
                txn_model = transaction_model.new_from_at_rest_full(json.loads(txn)["txn"])
                # Add general transaction index
                put_document(Indexes.transaction.value, f"txn-{txn_model.txn_id}", {"block_id": txn_model.block_id})
                watch_block = txn_types_to_watch.get(txn_model.txn_type)
                # Extract custom indexes if necessary
                if watch_block and int(txn_model.block_id) >= watch_block:
                    txn_model.extract_custom_indexes(txn_type_models[txn_model.txn_type])
                    put_document(txn_model.txn_type, txn_model.txn_id, txn_model.export_as_search_index())
