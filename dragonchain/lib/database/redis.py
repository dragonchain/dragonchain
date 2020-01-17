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
import time
import asyncio
from typing import Dict, Mapping, Iterable, Optional, Any, Union, cast

import aioredis
import aioredis.util
import redis

from dragonchain import logger

_log = logger.get_logger()

REDIS_ENDPOINT = os.environ["REDIS_ENDPOINT"]
LRU_REDIS_ENDPOINT = os.environ["LRU_REDIS_ENDPOINT"]
REDIS_PORT = int(os.environ["REDIS_PORT"]) or 6379

redis_client: redis.Redis = cast(redis.Redis, None)
redis_client_lru: redis.Redis = cast(redis.Redis, None)
async_redis_client: aioredis.Redis = cast(aioredis.Redis, None)


def _set_redis_client_if_necessary() -> None:
    global redis_client
    if redis_client is None:
        redis_client = _initialize_redis(host=REDIS_ENDPOINT, port=REDIS_PORT)


def _set_redis_client_lru_if_necessary() -> None:
    global redis_client_lru
    if redis_client_lru is None:
        redis_client_lru = _initialize_redis(host=LRU_REDIS_ENDPOINT, port=REDIS_PORT)


async def _set_redis_client_async_if_necessary() -> None:
    global async_redis_client
    if async_redis_client is None:
        async_redis_client = await _initialize_async_redis(host=REDIS_ENDPOINT, port=REDIS_PORT)


def _decode_response(response: Any, decode: bool) -> Any:
    if decode and isinstance(response, bytes):
        return response.decode("utf-8")
    return response


def _decode_dict_response(response: Mapping[Any, Any], decode: bool) -> Any:
    if decode is True:
        new_response = {}
        for key, value in response.items():
            if isinstance(key, bytes):
                key = key.decode("utf-8")
            if isinstance(value, bytes):
                value = value.decode("utf-8")
            new_response[key] = value
        return new_response
    return response


def _decode_list_response(response: Iterable[Any], decode: bool) -> Any:
    if decode is True:
        new_response = []
        for val in response:
            if isinstance(val, bytes):
                val = val.decode("utf-8")
            new_response.append(val)
        return new_response
    return response


def _decode_tuple_response(response: Iterable[Any], decode: bool) -> Any:
    if decode is True:
        new_list = _decode_list_response(response, True)
        return tuple(new_list)
    return response


def _decode_set_response(response: Iterable[Any], decode: bool) -> Any:
    if decode is True:
        new_response = set()
        for val in response:
            if isinstance(val, bytes):
                val = val.decode("utf-8")
            new_response.add(val)
        return new_response
    return response


def _initialize_redis(host: str, port: int, wait_time: int = 30) -> redis.Redis:
    """Initialize a redis, but ensure that the redis is up and connectable, otherwise throw an error
    Args:
        host: host of the redis to initialize a connection
        port: port of the redis to initialize a connection
        wait_time: number of seconds to wait with a failed connection before throwing a RuntimeException
    Returns:
        Redis-py (https://redis-py.readthedocs.io/en/latest/) client that is connected and available
    """
    expire_time = time.time() + wait_time
    _log.debug(f"Attempting to connect to redis at {host}:{port}")
    client = redis.Redis(host=host, port=port)
    sleep_time = 1  # Number of seconds to wait after a failure to connect before retrying
    while time.time() < expire_time:
        try:
            if client.ping():
                _log.debug(f"Successfully connected with redis at {host}:{port}")
                return client  # Connected to a working redis, return now
        except Exception:  # nosec (We want to retry for truly any exception)
            pass
        time.sleep(sleep_time)
    raise RuntimeError(f"Unable to initialize and connect to the redis at {host}:{port}")


async def _initialize_async_redis(host: str, port: int, wait_time: int = 30) -> aioredis.Redis:
    """Initiailize an aioredis, but ensure that the redis is up and connectable, otherwise throw an error
    Args:
        host: host of the redis to initialize a connection
        port: port of the redis to initialize a connection
        wait_time: number of seconds to wait with a failed connection before throwing a RuntimeException
    Returns:
        aioredis (https://aioredis.readthedocs.io/en/latest/) client (with a connection pool) that is connected and available
    """
    expire_time = time.time() + wait_time
    _log.debug(f"Attempting to connect to redis at {host}:{port}")
    sleep_time = 1  # Number of seconds to wait after a failure to connect before retrying
    while time.time() < expire_time:
        try:
            client = await aioredis.create_redis_pool((host, port))
            if await client.ping():
                _log.debug(f"Successfully connected with redis at {host}:{port}")
                return client  # Connected to a working redis, return now
        except Exception:  # nosec (We want to retry for truly any exception)
            pass
        await asyncio.sleep(sleep_time)
    raise RuntimeError(f"Unable to initialize and connect to the redis at {host}:{port}")


# ASYNC REDIS
async def z_range_by_score_async(
    key: str, min_num: int, max_num: int, withscores: bool = False, offset: Optional[int] = None, count: Optional[int] = None, *, decode: bool = True
) -> list:
    await _set_redis_client_async_if_necessary()
    return await async_redis_client.zrangebyscore(
        key, min_num, max_num, withscores=withscores, offset=offset, count=count, encoding="utf8" if decode else aioredis.util._NOTSET
    )


async def srem_async(key: str, value: str) -> int:
    await _set_redis_client_async_if_necessary()
    return await async_redis_client.srem(key, value)


async def get_async(key: str, *, decode: bool = True) -> Optional[str]:
    await _set_redis_client_async_if_necessary()
    return await async_redis_client.get(key, encoding="utf8" if decode else aioredis.util._NOTSET)


async def set_async(key: str, value: str, *, expire: int = 0, pexpire: int = 0, exist: Optional[bool] = None) -> bool:
    await _set_redis_client_async_if_necessary()
    return await async_redis_client.set(key, value, expire=expire, pexpire=pexpire, exist=exist)


async def zadd_async(key: str, score: int, member: str, exist: Optional[bool] = None) -> int:
    await _set_redis_client_async_if_necessary()
    return await async_redis_client.zadd(key, score, member, exist=exist)


async def smembers_async(key: str, *, decode: bool = True) -> set:
    await _set_redis_client_async_if_necessary()
    return set(await async_redis_client.smembers(key, encoding="utf8" if decode else aioredis.util._NOTSET))


async def multi_exec_async() -> aioredis.commands.transaction.MultiExec:
    await _set_redis_client_async_if_necessary()
    return async_redis_client.multi_exec()


async def hgetall_async(key: str, *, decode: bool = True) -> dict:
    await _set_redis_client_async_if_necessary()
    return await async_redis_client.hgetall(key, encoding="utf8" if decode else aioredis.util._NOTSET)


async def rpush_async(key: str, value: str, *values: str) -> int:
    await _set_redis_client_async_if_necessary()
    return await async_redis_client.rpush(key, value, *values)


async def delete_async(key: str, *keys: str) -> int:
    await _set_redis_client_async_if_necessary()
    return await async_redis_client.delete(key, *keys)


async def brpop_async(key: str, *keys: str, timeout: int = 0, decode: bool = True) -> list:
    await _set_redis_client_async_if_necessary()
    return await async_redis_client.brpop(key, *keys, timeout=timeout, encoding="utf8" if decode else aioredis.util._NOTSET)


async def hset_async(key: str, field: str, value: str) -> Optional[int]:
    await _set_redis_client_async_if_necessary()
    return await async_redis_client.hset(key, field, value)


async def hdel_async(key: str, field: str, *fields: str) -> int:
    await _set_redis_client_async_if_necessary()
    return await async_redis_client.hdel(key, field, *fields)


# LRU REDIS
def _cache_key(key: str, service_name: str) -> str:
    return f"{service_name}:{key}"


def cache_put(key: str, value: Union[str, bytes], cache_expire: Optional[int] = None, service_name: str = "storage") -> bool:
    _set_redis_client_lru_if_necessary()
    # ex has 'or None' here because 0 for cache expire must be set as none
    return redis_client_lru.set(_cache_key(key, service_name), value, ex=(cache_expire or None)) or False


def cache_get(key: str, service_name: str = "storage") -> Optional[bytes]:
    _set_redis_client_lru_if_necessary()
    return redis_client_lru.get(_cache_key(key, service_name))


def cache_delete(key: str, service_name: str = "storage") -> int:
    _set_redis_client_lru_if_necessary()
    return redis_client_lru.delete(_cache_key(key, service_name))


def cache_flush() -> bool:
    _set_redis_client_lru_if_necessary()
    return redis_client_lru.flushall()


# PESISTENT REDIS
def hdel_sync(name: str, *keys: str) -> int:
    _set_redis_client_if_necessary()
    return redis_client.hdel(name, *keys)


def lpush_sync(name: str, *values: str) -> int:
    _set_redis_client_if_necessary()
    return redis_client.lpush(name, *values)


def sadd_sync(name: str, *values: str) -> int:
    _set_redis_client_if_necessary()
    return redis_client.sadd(name, *values)


def sismember_sync(name: str, value: str) -> bool:
    _set_redis_client_if_necessary()
    return redis_client.sismember(name, value)


def rpush_sync(name: str, *values: str) -> int:
    _set_redis_client_if_necessary()
    return redis_client.rpush(name, *values)


def delete_sync(*names: str) -> int:
    _set_redis_client_if_necessary()
    return redis_client.delete(*names)


def hset_sync(name: str, key: str, value: str) -> int:
    _set_redis_client_if_necessary()
    return redis_client.hset(name, key, value)


def brpop_sync(keys: str, timeout: int = 0, decode: bool = True) -> Optional[tuple]:
    """Perform a blocking pop against redis list(s)
    Args:
        keys: Can be a single key (bytes, string, int, etc), or an array of keys to wait on
        timeout: Number of seconds to wait before 'timing out' and returning None. If 0, it will block indefinitely (default)
    Returns:
        None when no element could be popped and the timeout expired. This is only possible when timeout is not 0
        A tuple with the first element being the key where the element was popped, and the second element being the value of the popped element.
    """
    _set_redis_client_if_necessary()
    response = redis_client.brpop(keys, timeout=timeout)
    if not response:
        return None
    return _decode_tuple_response(response, decode)


def brpoplpush_sync(pop_key: str, push_key: str, timeout: int = 0, decode: bool = True) -> Optional[str]:
    """Perform a blocking pop against redis list(s)
    Args:
        pop_key: Can be a single key (bytes, string, int, etc), or an array of keys to wait on popping from
        push_key: key to push currently processing items to
        timeout: Number of seconds to wait before 'timing out' and returning None. If 0, it will block indefinitely (default)
    Returns:
        None when no element could be popped and the timeout expired. This is only possible when timeout is not 0
        The element that was moved between the lists
    """
    _set_redis_client_if_necessary()
    response = redis_client.brpoplpush(pop_key, push_key, timeout)
    if response is None:
        return None
    return _decode_response(response, decode)


def get_sync(name: str, decode: bool = True) -> Optional[str]:
    _set_redis_client_if_necessary()
    response = redis_client.get(name)
    return _decode_response(response, decode)


def lindex_sync(name: str, index: int, decode: bool = True) -> Optional[str]:
    _set_redis_client_if_necessary()
    response = redis_client.lindex(name, index)
    return _decode_response(response, decode)


def set_sync(key: str, value: str, ex: Optional[int] = None) -> bool:
    _set_redis_client_if_necessary()
    return redis_client.set(key, value, ex=ex) or False


def ltrim_sync(key: str, start: int, end: int) -> bool:
    _set_redis_client_if_necessary()
    return redis_client.ltrim(key, start, end)


def hget_sync(name: str, key: str, decode: bool = True) -> Optional[str]:
    _set_redis_client_if_necessary()
    response = redis_client.hget(name, key)
    return _decode_response(response, decode)


def smembers_sync(name: str, decode: bool = True) -> set:
    _set_redis_client_if_necessary()
    response = redis_client.smembers(name)
    return _decode_set_response(response, decode)


def srem_sync(name: str, *values: str) -> int:
    _set_redis_client_if_necessary()
    return redis_client.srem(name, *values)


def lrange_sync(name: str, start: int, end: int, decode: bool = True) -> list:
    _set_redis_client_if_necessary()
    response = redis_client.lrange(name, start, end)
    return _decode_list_response(response, decode)


def pipeline_sync(transaction: bool = True) -> redis.client.Pipeline:
    _set_redis_client_if_necessary()
    return redis_client.pipeline(transaction=transaction)


def llen_sync(name: str) -> int:
    _set_redis_client_if_necessary()
    return redis_client.llen(name)


def rpoplpush_sync(src: str, dst: str, decode: bool = True) -> Optional[str]:
    _set_redis_client_if_necessary()
    response = redis_client.rpoplpush(src, dst)
    return _decode_response(response, decode)


def lpop_sync(name: str, decode: bool = True) -> Optional[str]:
    _set_redis_client_if_necessary()
    response = redis_client.lpop(name)
    return _decode_response(response, decode)


def hgetall_sync(name: str, decode: bool = True) -> dict:
    _set_redis_client_if_necessary()
    response = redis_client.hgetall(name)
    return _decode_dict_response(response, decode)


def hexists_sync(name: str, key: str) -> bool:
    _set_redis_client_if_necessary()
    return redis_client.hexists(name, key)


def zadd_sync(name: str, mapping: Dict[str, int], nx: bool = False, xx: bool = False, ch: bool = False, incr: bool = False) -> int:
    _set_redis_client_if_necessary()
    return redis_client.zadd(name, mapping, nx=nx, xx=xx, ch=ch, incr=incr)
