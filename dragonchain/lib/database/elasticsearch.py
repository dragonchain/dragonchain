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
import re
import time
from typing import cast, Optional, Iterator, Dict, Any, TYPE_CHECKING

import elasticsearch
import elasticsearch.helpers
import elasticsearch.exceptions

from dragonchain.lib.dto import schema
from dragonchain.lib.interfaces import storage
from dragonchain import exceptions
from dragonchain import logger

if TYPE_CHECKING:
    from dragonchain.lib.dto import model
    from dragonchain.lib.dto import l2_block_model  # noqa: F401
    from dragonchain.lib.types import ESSearch

MAX_QUERY_PAGE_SIZE = 50
DEFAULT_PAGE_SIZE = 10
ES_RETRY_COUNT = 20
INTERNAL_ID = os.environ["INTERNAL_ID"]
S3_OBJECT_FOLDER = "s3_object_folder"
S3_OBJECT_ID = "s3_object_id"

_log = logger.get_logger()

_es_client: elasticsearch.Elasticsearch = None


def _set_elastic_search_client_if_necessary() -> None:
    """
    Returns elastic search client
    """
    global _es_client
    if _es_client is None:
        _es_client = _initialize_elastic_search()


def _initialize_elastic_search(wait_time: int = 60) -> elasticsearch.Elasticsearch:
    """Return a connected elastic search client
    Args:
        wait_time: number of seconds to wait with a failed connection before throwing a RuntimeException
    Returns:
        An elastic search client
    """
    expire_time = time.time() + wait_time
    host = os.environ["ELASTICSEARCH_HOST"]
    _log.debug(f"Attempting to connect to ES at: {host}")
    client = elasticsearch.Elasticsearch(host, timeout=60)
    sleep_time = 1  # Number of seconds to wait after a failure to connect before retrying
    while time.time() < expire_time:
        try:
            if client.ping():
                _log.debug(f"Successfully connected with ES at: {host}")
                return client  # Connected to a working ES, return now
        except Exception:
            pass
        time.sleep(sleep_time)
    raise RuntimeError(f"Unable to initialize and connect to the ES at: {host}")


def remove_index(doc_id: str, folder: str) -> None:
    _set_elastic_search_client_if_necessary()
    _es_client.delete(index=build_index(folder=folder), doc_type="_doc", id=doc_id)


def get_count(folder: str) -> int:
    """
    Return the count of indexes at the folder path.
    """
    try:
        _set_elastic_search_client_if_necessary()
        count_obj = _es_client.count(index=build_index(folder=folder))
        return count_obj["count"]  # Return only the integer
    except elasticsearch.exceptions.NotFoundError:
        return 0


def get_index_only(  # noqa: C901 Needs a refactor
    folder: str,
    query: Optional[dict] = None,
    q: Optional[str] = None,
    get_all: bool = False,
    sort: Optional[str] = None,
    offset: Optional[int] = None,
    limit: Optional[int] = None,
) -> dict:
    """Return only the index from ElasticSearch."""
    _set_elastic_search_client_if_necessary()
    if query is not None and q is not None:
        raise exceptions.ValidationException("Both query and q can not be used at the same time.")
    if query is None and q is None:
        raise exceptions.ValidationException("Both query and q can not be be blank.")

    search_args: dict = {"index": build_index(folder=folder)}

    if query is not None:
        search_args["body"] = query
    if sort:
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
        search_args["scroll"] = "1m"
        search_args["size"] = MAX_QUERY_PAGE_SIZE
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
        return {"hits": [], "total": 0}

    total = elasticsearch_results["hits"]["total"]
    hits_pages = elasticsearch_results["hits"]["hits"]
    if get_all:
        scroll_id = elasticsearch_results["_scroll_id"]

        while len(elasticsearch_results["hits"]["hits"]) > 0:
            elasticsearch_results = _es_client.scroll(scroll_id=scroll_id, scroll="1m")

            if len(elasticsearch_results["hits"]["hits"]) > 0:
                hits_pages.append(elasticsearch_results["hits"]["hits"])
                _log.info(f"[DAO] SEARCH <= LEN: {len(elasticsearch_results['hits']['hits'])}")

        _es_client.clear_scroll(body={"scroll_id": [scroll_id]}, ignore=(404,))

    return {"hits": hits_pages, "total": total}


def put_index_in_storage(folder: str, namespace: str, data_model: "model.Model") -> None:
    """Store data model content in storage, while creating an elastic search index
    Args:
        folder: the storage folder to use
        namespace: the storage namespace to use
        data_model: the data model to export
    """
    _set_elastic_search_client_if_necessary()
    _log.info(f"[DAO] SET -> {namespace}")

    indexable_object = data_model.export_as_search_index()
    full_object = data_model.export_as_at_rest()

    _log.info(f"[DAO] ES => INDEXABLE_OBJECT: {indexable_object}")

    _log.info(f"[DAO] ES => INDEXING OBJECT: namespace: {namespace}")
    _es_client.index(index=build_index(folder=folder), doc_type="_doc", id=namespace, body=json.dumps(indexable_object, separators=(",", ":")))

    _log.info(f"[DAO] storage => UPLOADING OBJECT: {full_object}")
    try:
        key = f"{folder.upper()}/{namespace}"
        try:
            # Smart contracts use a seperate key for metadata
            if data_model.is_sc_model:  # noqa: T484 property might not exist, which is explicitly caught
                key += "/metadata.json"
        except Exception:
            pass
        storage.put_object_as_json(key, full_object)
    except Exception:
        _es_client.delete(index=build_index(folder=folder), doc_type="_doc", id=namespace)


def put_many_index_only(folder: str, objects: dict) -> None:
    """Store a bunch of SearchIndex DTO as JSON content in ES with headers of a object
    Args:
        folder: the folder for the index
        objects: A dictionary where the keys are the IDs of the objects to index, and the value are the objects to index
    """
    _set_elastic_search_client_if_necessary()
    index = build_index(folder=folder)
    _log.info("[DAO] ES => BULK INDEXING")
    elasticsearch.helpers.bulk(_es_client, prepare_bulk(objects, index), index=index)
    _log.info("[DAO] ES => SET COMPLETE.")


def put_index_only(folder: str, namespace: str, object_to_index: dict) -> None:
    """Store a single SearchIndex DTO as JSON content in ES
    Args:
        folder: the folder for the index
        namespace: the namespace to store under
        object_to_index: the object to index
    """
    _set_elastic_search_client_if_necessary()
    index = build_index(folder=folder)
    _log.info(f"[DAO] ES => INDEXING SINGLE: {index}")
    _es_client.index(index=index, doc_type="_doc", id=namespace, body=json.dumps(object_to_index, separators=(",", ":")))
    _log.info("[DAO] ES => COMPLETED INDEXING")


def search(
    folder: str,
    query: Optional[dict] = None,
    q: Optional[str] = None,
    get_all: bool = False,
    sort: Optional[str] = None,
    offset: Optional[int] = None,
    limit: Optional[int] = None,
    should_parse: bool = True,
) -> "ESSearch":
    """invoke queries on elastic search indexes built with #set. Return the full storage stored object
    Args:
        query: Elastic search query. The search definition using the ES Query DSL.
        q: Query in the Lucene query string syntax
    Returns:
        storage objects matching search query
    """
    hits_pages = get_index_only(folder, query, q, get_all, sort, offset, limit)
    _log.info(f"Pages: {hits_pages}")
    storage_objects = []

    for hit in hits_pages["hits"]:
        storage_id = hit["_source"][S3_OBJECT_ID]  # get the id
        # get the folder
        storage_folder = hit["_source"][S3_OBJECT_FOLDER]
        storage_object = storage.get_json_from_object(f"{storage_folder}/{storage_id}")  # pull the object from storage
        storage_objects.append(storage_object)  # add to the result set

        #  Parse transactions if should_parse is flagged, and the transactions array exists
        if storage_object["dcrn"] == schema.DCRN.Block_L1_At_Rest.value and should_parse:
            for index, transaction in enumerate(storage_object["transactions"]):
                storage_object["transactions"][index] = json.loads(transaction)

    return {"results": storage_objects, "total": hits_pages["total"]}


def build_index(folder: str) -> str:
    """
    returns {string}
        kebab-case string combining <dragonchainId>-<folder>
    """
    return "-".join(x.lower() for x in [INTERNAL_ID, folder] if x != "")


def prepare_bulk(structured_data_obj: dict, index: str, bulk_op: str = "index") -> Iterator[Dict[str, Any]]:
    _log.info(f"preparing for bulk {structured_data_obj} ")
    for key, value in structured_data_obj.items():
        if isinstance(value, dict):
            yield {"_op_type": bulk_op, "_index": index, "_type": "_doc", "_id": key, "_source": json.dumps(value, separators=(",", ":"))}


def set_receipt_data(key: str, data_model: "model.BlockModel", l1_block_id: str, level: int) -> None:
    """Store receipt as JSON content in storage, while updating ES metadata to reflect relevant verifications
    Args:
        key: String of the storage key for the receipt block
        data_model: block data model which you want to store as JSON in storage.
        l1_block_id: the level 1 block id that this receipt corresponds to
        level: the level of the received block
    """
    _set_elastic_search_client_if_necessary()
    full_object = data_model.export_as_at_rest()

    # then get block from elastic and then send with incremented verification count.
    upscript = {"script": f"ctx._source.l{level}_verifications += 1"}
    count = 0
    elastic_success = False
    while count < ES_RETRY_COUNT:
        try:
            elastic_response = _es_client.update(index=f"{INTERNAL_ID}-block", doc_type="_doc", id=l1_block_id, body=upscript)
            if int(elastic_response["_shards"]["successful"]) > 0:
                _log.info("[DAO] Successfully indexed block verifications")
                elastic_success = True
                break
        except Exception:
            count += 1
    if not elastic_success:
        _log.error("[DAO] ES Indexing Failed, abort storage upload.")
        raise exceptions.ElasticSearchFailure("Elasticsearch Index Failure")
    # map through each transaction in l2 receipts to update metadata rejections if relevant
    if level == 2:
        bulk_rejections = {}
        upscript = {"script": "ctx._source.l2_rejections += 1"}
        data_model = cast("l2_block_model.L2BlockModel", data_model)  # if L2, we know this is an L2 block model
        for txn in data_model.validations_dict:
            if not data_model.validations_dict[txn]:
                bulk_rejections.update({txn: upscript})
        if len(bulk_rejections.keys()) != 0:
            _log.info("[DAO] Level 2 block had rejections, bulk updating rejections for transactions")
            bulk_index = prepare_bulk(bulk_rejections, index=f"{data_model.get_associated_l1_dcid()}-transaction", bulk_op="update")
            elasticsearch.helpers.bulk(_es_client, bulk_index)
    _log.info("[DAO] STORAGE => Uploading receipt to storage")
    storage.put_object_as_json(key, full_object)
