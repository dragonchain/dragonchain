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

import unittest
from unittest.mock import patch, MagicMock, AsyncMock

from dragonchain.lib.database import redis


class TestRedisAccess(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        redis.redis_client = MagicMock()
        redis.redis_client_lru = MagicMock()
        redis.async_redis_client = AsyncMock(multi_exec=MagicMock())

    @patch("dragonchain.lib.database.redis._initialize_redis")
    def test_set_redis_client_if_necessary(self, mock_redis):
        redis.redis_client = None
        redis._set_redis_client_if_necessary()
        mock_redis.assert_called_once()

    @patch("dragonchain.lib.database.redis._initialize_redis")
    def test_set_redis_client_lru_if_necessary(self, mock_redis):
        redis.redis_client_lru = None
        redis._set_redis_client_lru_if_necessary()
        mock_redis.assert_called_once()

    @patch("dragonchain.lib.database.redis._initialize_async_redis")
    async def test_set_redis_client_async_if_necessary(self, mock_redis):
        redis.async_redis_client = None
        await redis._set_redis_client_async_if_necessary()
        redis._initialize_async_redis.assert_called_once()

    async def test_z_range_by_score_async(self):
        await redis.z_range_by_score_async("banana", 1, 2)
        redis.async_redis_client.zrangebyscore.assert_awaited_once_with("banana", 1, 2, count=None, encoding="utf8", offset=None, withscores=False)

    async def test_get_async(self):
        await redis.get_async("banana")
        redis.async_redis_client.get.assert_awaited_once_with("banana", encoding="utf8")

    async def test_set_async(self):
        await redis.set_async("banana", "banana")
        redis.async_redis_client.set.assert_awaited_once_with("banana", "banana", expire=0, pexpire=0, exist=None)

    async def test_zadd_async(self):
        await redis.zadd_async("banana", "banana", "banana")
        redis.async_redis_client.zadd.assert_awaited_once_with("banana", "banana", "banana", exist=None)

    async def test_smembers_async(self):
        await redis.smembers_async("banana")
        redis.async_redis_client.smembers.assert_awaited_once_with("banana", encoding="utf8")

    async def test_multi_exec_async(self):
        await redis.multi_exec_async()
        redis.async_redis_client.multi_exec.assert_called_once()

    async def test_hgetall_async(self):
        await redis.hgetall_async("banana")
        redis.async_redis_client.hgetall.assert_awaited_once_with("banana", encoding="utf8")

    async def test_rpush_async(self):
        await redis.rpush_async("banana", "banana", "banana", "banana")
        redis.async_redis_client.rpush.assert_awaited_once_with("banana", "banana", "banana", "banana")

    async def test_delete_async(self):
        await redis.delete_async("banana", "banana", "banana")
        redis.async_redis_client.delete.assert_awaited_once_with("banana", "banana", "banana")

    async def test_brpop_async(self):
        await redis.brpop_async("banana", "banana", "banana")
        redis.async_redis_client.brpop.assert_awaited_once_with("banana", "banana", "banana", encoding="utf8", timeout=0)

    async def test_hset_async(self):
        await redis.hset_async("banana", "banana", "banana")
        redis.async_redis_client.hset.assert_awaited_once_with("banana", "banana", "banana")

    async def test_srem_async(self):
        await redis.srem_async("apple", "banana")
        redis.async_redis_client.srem.assert_awaited_once_with("apple", "banana")

    async def test_hdel_async(self):
        await redis.hdel_async("banana", "banana", "banana")
        redis.async_redis_client.hdel.assert_awaited_once_with("banana", "banana", "banana")

    def test_cache_put_with_cache_expire(self):
        redis.cache_put("banana", "banana", cache_expire=60)
        redis.redis_client_lru.set.assert_called_once_with("storage:banana", "banana", ex=60)

    def test_cache_put_no_cache_expire(self):
        redis.cache_put("banana", "banana")
        redis.redis_client_lru.set.assert_called_once_with("storage:banana", "banana", ex=None)

    def test_cache_get(self):
        redis.cache_get("banana")
        redis.redis_client_lru.get.assert_called_once_with("storage:banana")

    def test_cache_delete(self):
        redis.cache_delete("banana")
        redis.redis_client_lru.delete.assert_called_once_with("storage:banana")

    def test_get_key(self):
        redis._cache_key("banana", service_name="storage")
        self.assertEqual(redis._cache_key("banana", service_name="storage"), "storage:banana")

    def testcache_flush(self):
        redis.cache_flush()
        redis.redis_client_lru.flushall.assert_called_once()

    def test_hdel(self):
        redis.hdel_sync("banana", "banana")
        redis.redis_client.hdel.assert_called_once_with("banana", "banana")

    def test_lpush(self):
        redis.lpush_sync("banana", "banana", "banana")
        redis.redis_client.lpush.assert_called_once_with("banana", "banana", "banana")

    def test_rpush(self):
        redis.rpush_sync("banana", "banana")
        redis.redis_client.rpush.assert_called_once_with("banana", "banana")

    def test_delete(self):
        redis.delete_sync("banana")
        redis.redis_client.delete.assert_called_once_with("banana")

    def test_hset(self):
        redis.hset_sync("banana", "banana", "banana")
        redis.redis_client.hset.assert_called_once_with("banana", "banana", "banana")

    def test_brpop(self):
        redis.brpop_sync("banana")
        redis.redis_client.brpop.assert_called_once_with("banana", timeout=0)

    def test_brpoplpush(self):
        redis.brpoplpush_sync("banana", "apple")
        redis.redis_client.brpoplpush.assert_called_once_with("banana", "apple", 0)

    def test_get_sync(self):
        redis.get_sync("banana")
        redis.redis_client.get.assert_called_once_with("banana")

    def test_lindex(self):
        redis.lindex_sync("banana", 2)
        redis.redis_client.lindex.assert_called_once_with("banana", 2)

    def test_set_sync(self):
        redis.set_sync("banana", "banana")
        redis.redis_client.set.assert_called_once_with("banana", "banana", ex=None)

    def test_ltrim(self):
        redis.ltrim_sync("banana", 1, 2)
        redis.redis_client.ltrim.assert_called_once_with("banana", 1, 2)

    def test_hget(self):
        redis.hget_sync("banana", "banana")
        redis.redis_client.hget.assert_called_once_with("banana", "banana")

    def test_sadd(self):
        redis.sadd_sync("banana", "banana", "banana")
        redis.redis_client.sadd.assert_called_once_with("banana", "banana", "banana")

    def test_sismember(self):
        redis.sismember_sync("banana", "banana")
        redis.redis_client.sismember.assert_called_once_with("banana", "banana")

    def test_smembers(self):
        redis.smembers_sync("banana")
        redis.redis_client.smembers.assert_called_once_with("banana")

    def test_srem(self):
        redis.srem_sync("banana", "banana", "banana")
        redis.redis_client.srem.assert_called_once_with("banana", "banana", "banana")

    def test_lrange(self):
        redis.lrange_sync("banana", 1, 5)
        redis.redis_client.lrange.assert_called_once_with("banana", 1, 5)

    def test_pipeline(self):
        redis.pipeline_sync()
        redis.redis_client.pipelineassert_called_once_with(True, None)

    def test_llen(self):
        redis.llen_sync("banana")
        redis.redis_client.llen.assert_called_once_with("banana")

    def test_rpoplpush(self):
        redis.rpoplpush_sync("banana", "banana")
        redis.redis_client.rpoplpush.assert_called_once_with("banana", "banana")

    def test_lpop(self):
        redis.lpop_sync("banana")
        redis.redis_client.lpop.assert_called_once_with("banana")

    def test_hgetall(self):
        redis.hgetall_sync("banana")
        redis.redis_client.hgetall.assert_called_once_with("banana")

    def test_hexists(self):
        redis.hexists_sync("banana", "banana")
        redis.redis_client.hexists.assert_called_once_with("banana", "banana")

    def test_zadd(self):
        redis.zadd_sync("banana", "banana")
        redis.redis_client.zadd.assert_called_once_with("banana", "banana", ch=False, incr=False, nx=False, xx=False)
