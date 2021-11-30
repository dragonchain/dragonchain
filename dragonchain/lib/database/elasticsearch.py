import enum
import json
import logging
import os
import re
import time
from typing import Optional, TYPE_CHECKING, Iterator, Dict, Any, List, cast

import elasticsearch
from requests_aws4auth import AWS4Auth
import boto3
from elasticsearch.helpers import bulk

from dragonchain import logger, exceptions
from dragonchain.lib import namespace
from dragonchain.lib.dao import transaction_type_dao
from dragonchain.lib.database import redis
from dragonchain.lib.database.redis import get_sync, delete_sync, set_sync, sismember_sync, sadd_sync
from dragonchain.lib.dto import l1_block_model, l2_block_model, l3_block_model, l4_block_model, l5_block_model, \
    smart_contract_model, transaction_type_model, transaction_model
from dragonchain.lib.interfaces import storage

if TYPE_CHECKING:
    from dragonchain.lib.types import ESSearch

MAX_QUERY_PAGE_SIZE = 10000
DEFAULT_PAGE_SIZE = 10
ES_RETRY_COUNT = 20

_log = logger.get_logger()

LEVEL = os.environ["LEVEL"]
INTERNAL_ID = os.environ["INTERNAL_ID"]
ELASTICSEARCH_ENDPOINT = os.environ["ELASTICSEARCH_ENDPOINT"]
ENABLED = not (LEVEL != "1" and os.environ.get("USE_ELASTICSEARCH") == "false")
BROADCAST_ENABLED = os.environ["BROADCAST"].lower() != "false"

INDEX_L5_VERIFICATION_GENERATION_KEY = "dc:l5_index_generation_complete"
INDEX_GENERATION_KEY = "dc:index_generation_complete"
L5_BLOCK_MIGRATION_KEY = "dc:migrations:l5_block"
BLOCK_MIGRATION_KEY = "dc:migrations:block"
TXN_MIGRATION_KEY = "dc:migrations:txn"
L5_NODES = "dc:nodes:l5"

_es_client: elasticsearch.Elasticsearch = None

credentials = boto3.Session().get_credentials()
awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, "us-west-1", "es", session_token=credentials.token)


class Indexes(enum.Enum):
    block = "bk"
    smartcontract = "sc"
    transaction = "tx"
    verification = "ver"


def set_elastic_search_client_if_necessary() -> None:
    """
    Returns elastic search client
    """
    global _es_client
    if _es_client is None:
        _es_client = initialize_elastic_search()


def initialize_elastic_search(wait_time=60) -> elasticsearch.Elasticsearch:
    expire_time = time.time() + wait_time
    _log.debug(f"Attempting to connect to ES at: {ELASTICSEARCH_ENDPOINT}")
    client = elasticsearch.Elasticsearch(
        hosts=[{"host": ELASTICSEARCH_ENDPOINT, "port": 443}],
        http_auth=awsauth,
        use_ssl=True,
        verify_certs=True,
        connection_class=elasticsearch.RequestsHttpConnection,
    )
    sleep_time = 1
    while time.time() < expire_time:
        try:
            if client.ping():
                _log.debug(f"Successfully connected with ES at: {ELASTICSEARCH_ENDPOINT}")
                return client
        except Exception:
            pass
        time.sleep(sleep_time)
        raise RuntimeError(f"Unable to initialize and connect to the ES at: {ELASTICSEARCH_ENDPOINT}")


def create_index(index: str) -> None:
    set_elastic_search_client_if_necessary()
    result = _es_client.indices.create(index=_build_index(index))
    return result


def delete_index(index: str) -> None:
    set_elastic_search_client_if_necessary()
    result = _es_client.indices.delete(index=_build_index(index))
    return result


def search(
    index: str,
    query: Optional[dict] = None,
    q: Optional[str] = None,
    get_all: bool = False,
    sort: Optional[str] = None,
    offset: Optional[int] = None,
    limit: Optional[int] = None,
) -> "ESSearch":
    """invoke queries on elastic search indexes built with #set. Return the full storage stored object
    Args:
        index: The index to search under
        query: Elastic search query. The search definition using the ES Query DSL.
        q: Query in the Lucene query string syntax
        get_all: Return all documents under index
        sort: A comma-separated list of <field>:<direction> pairs
        offset: the offset to start the query from, this can be used for pagination (defaults to 0, aka the start of the query)
        limit: Number of hits to return (default: 10)
    Returns:
        indexed documents matching search query
    """
    set_elastic_search_client_if_necessary()
    if query is not None and q is not None:
        raise exceptions.ValidationException("Both query and q can not be used at the same time.")
    if query is None and q is None:
        raise exceptions.ValidationException("Both query and q can not be be blank.")

    search_args: dict = {"index": _build_index(index)}
    pit = None

    if query is not None:
        search_args["body"] = query
    if sort is not None:
        search_args["sort"] = sort

    if q is not None:
        is_limit_specified = re.search(r"limit=([\d]*)", q)
        if is_limit_specified is not None:
            limit = int(is_limit_specified.group(1))
            if limit > MAX_QUERY_PAGE_SIZE:
                _log.info(f"[QUERY REQUEST TO LARGE] limit requested: {limit}, replacing with max allowed {MAX_QUERY_PAGE_SIZE}")
                q = q.replace(f"limit={limit}", f"limit={MAX_QUERY_PAGE_SIZE}")
        search_args["q"] = q
    if get_all:
        search_args["size"] = MAX_QUERY_PAGE_SIZE
        pit = _es_client.open_point_in_time(index=index, keep_alive="1m")
        search_args["pit"] = pit
        if sort is None:
            search_args["sort"] = [
                {"@timestamp": {"order": "asc", "format": "strict_date_optional_time_nanos"}},
            ]
    elif offset or limit:
        if limit and int(limit) > MAX_QUERY_PAGE_SIZE:
            limit = MAX_QUERY_PAGE_SIZE
        search_args["size"] = limit or DEFAULT_PAGE_SIZE
        search_args["from_"] = offset or 0
    try:
        _log.info(f"[DAO] SEARCH => {search_args}")
        elasticsearch_results = _es_client.search(**search_args)
        _log.info(f"[DAO] SEARCH <= LEN: {len(elasticsearch_results['hits']['hits'])}")
    except elasticsearch.exceptions.NotFoundError:
        return {"results": [], "total": 0}

    hits_pages = elasticsearch_results["hits"]["hits"]
    if get_all:
        hit_count = elasticsearch_results["hits"]["total"]
        while hit_count > 0:
            search_args["search_after"] = elasticsearch_results["hits"]["hits"][hit_count - 1]["sort"]
            elasticsearch_results = _es_client.search(**search_args)
            hit_count = elasticsearch_results["hits"]["total"]

            if hit_count > 0:
                hits_pages.append(elasticsearch_results["hits"]["hits"])
                _log.info(f"[DAO] SEARCH <= LEN: {len(elasticsearch_results['hits']['hits'])}")

        _es_client.close_point_in_time(body=pit)

    return {"results": hits_pages, "total": len(hits_pages)}


def list_document_ids(index: str) -> List[str]:
    set_elastic_search_client_if_necessary()
    res = _es_client.search(
        index=_build_index(index),
        body={"query": {"match_all": {}}, "size": 10000, "fields": ["_id"]})

    ids = [d['_id'] for d in res['hits']['hits']]
    return ids


def get_document_by_id(doc_id: str):
    set_elastic_search_client_if_necessary()
    result = _es_client.search(body={"query": {"ids": {"values": [doc_id]}}})
    return result["hits"]["hits"][0]["_source"]


def get_document_count(index: str) -> int:
    set_elastic_search_client_if_necessary()
    count_obj = _es_client.count(index=_build_index(index))
    _log.info(f"COUNT RESULT: {count_obj}")
    return count_obj


def put_document(index: str, object_to_index: dict, doc_id: str = None) -> None:
    set_elastic_search_client_if_necessary()
    _es_client.index(index=_build_index(index), id=doc_id, body=json.dumps(object_to_index, separators=(",", ":")))


def put_many_documents(index: str, documents: Dict) -> None:
    set_elastic_search_client_if_necessary()
    _log.info("[DAO] ES => BULK INDEXING")
    _log.info(f"INDEXING ITEMS: {_build_index(index)}: {documents}")
    response = bulk(_es_client, actions=_prepare_bulk(index, documents))
    _log.info(f"RESPONSE: {response}")
    _log.info("[DAO] ES => SET COMPLETE.")


def delete_document(index: str, doc_id: str) -> None:
    set_elastic_search_client_if_necessary()
    _es_client.delete(index=_build_index(index), doc_type="_doc", id=doc_id)


def _build_index(index: str) -> str:
    """
    returns {string}
        kebab-case string combining <dragonchainId>-<index>
    """
    return "-".join(x.lower() for x in [INTERNAL_ID, index] if x != "")


def _prepare_bulk(index: str, structured_data_obj: dict, bulk_op: str = "index") -> Iterator[Dict[str, Any]]:
    _log.info(f"preparing for bulk {structured_data_obj} ")
    for key, value in structured_data_obj.items():
        if isinstance(value, dict):
            yield {
                "_op_type": bulk_op,
                "_index": _build_index(index),
                "_type": "_doc",
                "_id": key,
                "_source": json.dumps(value, separators=(",", ":")),
            }


def generate_indexes_if_necessary() -> None:
    """Initialize elasticsearch with necessary indexes and fill them from storage if migration has not been marked as complete"""
    needs_generation = not bool(get_sync(INDEX_GENERATION_KEY))
    needs_l5_generation = not bool(get_sync(INDEX_L5_VERIFICATION_GENERATION_KEY))
    # No-op if indexes are marked as already generated
    if not needs_generation and not needs_l5_generation:
        return

    if needs_l5_generation:
        # Create L5 verification indexes
        _generate_l5_verification_indexes()
        # Mark index generation as complete
        delete_sync(L5_BLOCK_MIGRATION_KEY)
        set_sync(INDEX_L5_VERIFICATION_GENERATION_KEY, "a")

    if needs_generation:
        # Create block index
        _log.info("Creating block indexes")
        _generate_block_indexes()
        # Create indexes for transactions
        _log.info("Creating transaction indexes")
        _generate_transaction_indexes()
        # Create smart contract index
        _log.info("Creating smart contract indexes")
        _generate_smart_contract_indexes()
        # Mark index generation as complete
        _log.info("Marking redisearch index generation complete")
        delete_sync(BLOCK_MIGRATION_KEY)
        delete_sync(TXN_MIGRATION_KEY)
        set_sync(INDEX_GENERATION_KEY, "a")


def _generate_l5_verification_indexes() -> None:
    try:
        create_index(Indexes.verification.value)
    except elasticsearch.exceptions.RequestError as e:
        if e.error != "resource_already_exists_exception":
            raise
    _log.info("Listing all blocks in storage")
    block_paths = storage.list_objects("BLOCK/")
    pattern = re.compile(r"BLOCK\/([0-9]+)-([Ll])5(.*)$")
    for block_path in block_paths:
        if LEVEL == "1" and BROADCAST_ENABLED and re.search(pattern, block_path):
            if not sismember_sync(L5_BLOCK_MIGRATION_KEY, block_path):
                raw_block = storage.get_json_from_object(block_path)
                block = l5_block_model.new_from_at_rest(raw_block)
                storage_location = block_path.split("/")[1]
                try:
                    put_document(Indexes.verification.value, block.export_as_search_index(), block.block_id)
                except elasticsearch.exceptions.ElasticsearchException as e:
                    if not str(e).startswith("Document already exists"):
                        raise
                    else:
                        _log.info(f"Document {storage_location} already exists")
                sadd_sync(L5_NODES, block.dc_id)
                sadd_sync(L5_BLOCK_MIGRATION_KEY, block_path)
            else:
                _log.info(f"Skipping already indexed L5 block {block_path}")


def _generate_block_indexes() -> None:
    try:
        create_index(Indexes.block.value)
    except elasticsearch.exceptions.RequestError as e:
        if e.error != "resource_already_exists_exception":
            raise
    _log.info("Listing all blocks in storage")
    block_paths = storage.list_objects("BLOCK/")
    pattern = re.compile(r"BLOCK\/[0-9]+$")
    for block_path in block_paths:
        if re.search(pattern, block_path):
            # do a check to see if this block was already marked as indexed
            if not sismember_sync(BLOCK_MIGRATION_KEY, block_path):
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
                put_document(Indexes.block.value, block.export_as_search_index(), block.block_id)
                sadd_sync(BLOCK_MIGRATION_KEY, block_path)
            else:
                _log.info(f"Skipping already indexed block {block_path}")


def _generate_smart_contract_indexes() -> None:
    try:
        delete_index(Indexes.smartcontract.value)  # Always generate smart contract indexes from scratch by dropping existing ones
    except elasticsearch.exceptions.NotFoundError as e:
        if e.error != "index_not_found_exception":
            raise
    create_index(Indexes.smartcontract.value)
    # Find what smart contracts exist in storage
    _log.info("Listing all smart contracts in storage")
    sc_object_paths = storage.list_objects("SMARTCONTRACT/")
    pattern = re.compile(r"SMARTCONTRACT\/.{36}\/metadata\.json$")
    for sc in sc_object_paths:
        if re.search(pattern, sc):
            sc_model = smart_contract_model.new_from_at_rest(storage.get_json_from_object(sc))
            _log.info(f"Adding index for smart contract {sc_model.id} ({sc_model.txn_type})")
            put_document(Indexes.smartcontract.value, sc_model.export_as_search_index(), sc_model.id)


def _generate_transaction_indexes() -> None:  # noqa: C901
    # -- CREATE INDEXES FOR TRANSACTIONS --
    try:
        create_index(Indexes.transaction.value)
    except elasticsearch.exceptions.RequestError as e:
        if e.error != "resource_already_exists_exception":
            raise
    try:
        create_index(namespace.Namespaces.Contract.value)  # Create the reserved txn type index
    except elasticsearch.exceptions.RequestError as e:
        if e.error != "resource_already_exists_exception":
            raise
    txn_types_to_watch = {namespace.Namespaces.Contract.value: 1}  # Will be use when going through all stored transactions
    txn_type_models = {
        namespace.Namespaces.Contract.value: transaction_type_model.TransactionTypeModel(namespace.Namespaces.Contract.value, active_since_block="1")
    }
    for txn_type in transaction_type_dao.list_registered_transaction_types():
        txn_type_model = transaction_type_model.new_from_at_rest(txn_type)
        txn_type_models[txn_type_model.txn_type] = txn_type_model
        _log.info(f"Adding index for {txn_type_model.txn_type}")
        put_document(txn_type_model.txn_type, txn_type_model.custom_indexes)
        txn_types_to_watch[txn_type_model.txn_type] = int(txn_type_model.active_since_block)

    # -- LIST AND INDEX ACTUAL TRANSACTIONS FROM STORAGE
    _log.info("Listing all full transactions")
    transaction_blocks = storage.list_objects("TRANSACTION/")
    for txn_path in transaction_blocks:
        # do a check to see if this block's transactions were already marked as indexed
        if not sismember_sync(TXN_MIGRATION_KEY, txn_path):
            _log.info(f"Indexing transactions for {txn_path}")
            for txn in storage.get(txn_path).split(b"\n"):
                if txn:
                    txn_model = transaction_model.new_from_at_rest_full(json.loads(txn)["txn"])
                    # Add general transaction index
                    put_document(_build_index(Indexes.transaction.value), {"block_id": txn_model.block_id}, txn_model.txn_id)
                    watch_block = txn_types_to_watch.get(txn_model.txn_type)
                    # Extract custom indexes if necessary
                    if watch_block and int(txn_model.block_id) >= watch_block:
                        txn_model.extract_custom_indexes(txn_type_models[txn_model.txn_type])
                        put_document(txn_model.txn_type, txn_model.export_as_search_index(), txn_model.txn_id)
            sadd_sync(TXN_MIGRATION_KEY, txn_path)
        else:
            _log.info(f"Skipping already indexed transaction {txn_path}")
