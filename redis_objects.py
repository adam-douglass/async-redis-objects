import json
from typing import Any, List, Dict, Set

import aioredis
# from tenacity import retry


class ObjectClient:
    def __init__(self, redis_client):
        self.client = redis_client

    def queue(self, name):
        return Queue(name, self.client)

    def hash(self, name):
        return Hash(name, self.client)


class Hash:
    def __init__(self, key: str, client: aioredis.Redis):
        self.key = key
        self.client = client

    async def keys(self) -> Set[str]:
        return {k.decode() for k in await self.client.hkeys(self.key)}

    async def set(self, key, value) -> bool:
        """Returns if the key is new or not. Set is performed either way."""
        return await self.client.hset(self.key, key, json.dumps(value)) == 1

    async def add(self, key, value) -> bool:
        """Returns if the key is new or not. Set only performed if key is new."""
        return await self.client.hsetnx(self.key, key, json.dumps(value)) == 1

    async def get(self, key) -> Any:
        value = await self.client.hget(self.key, key)
        if not value:
            return None
        return json.loads(value)

    async def mget(self, keys) -> Dict[str, Any]:
        values = await self.client.hmget(self.key, *keys)
        return {
            k: json.loads(v)
            for k, v in zip(keys, values)
        }

    async def all(self) -> Dict[str, Any]:
        values = await self.client.hgetall(self.key)
        return {
            k.decode(): json.loads(v)
            for k, v in values.items()
        }

    async def delete(self, key) -> bool:
        return await self.client.hdel(self.key, key) == 1


class Queue:
    def __init__(self, key: str, client: aioredis.Redis):
        self.key = key
        self.client = client

    async def push(self, data):
        await self.client.lpush(self.key, json.dumps(data))

    async def pop(self, timeout: int = 1, blocking: bool = True) -> Any:
        if blocking:
            message = await self.client.blpop(self.key, timeout=timeout)
        else:
            message = await self.client.lpop(self.key)
        if message is None:
            return None
        return json.loads(message)

    async def clear(self):
        await self.client.delete(self.key)


class PriorityQueue:
    def __init__(self, key: str, client: aioredis.Redis):
        self.key = key
        self.client = client

    async def push(self, data, priority=0):
        await self.client.zadd(self.key, priority, json.dumps(data))

    async def pop(self, timeout: int = 1, blocking: bool = True) -> Any:
        if blocking:
            message = await self.client.bzpopmax(self.key, timeout=timeout)
        else:
            message = await self.client.zpopmax(self.key)
        if message is None:
            return None
        return json.loads(message)

    async def clear(self):
        await self.client.delete(self.key)
