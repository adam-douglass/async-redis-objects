import time
import sys
import json
import uuid
import typing
from typing import Any, Dict, Iterable
import aioredis
import asyncio

if sys.version_info[1] >= 7:
    _current_task = asyncio.current_task
else:
    _current_task = asyncio.Task.current_task


class Set:
    """Interface to a redis set.

    Can be constructed directly, or from an :class:`ObjectClient` factory.
    """
    def __init__(self, key: str, client: aioredis.Redis):
        """
        :param key: key in the redis server that is empty, or pointing to an existing set
        :param client:
        """
        self.key = key
        self.client = client

    async def add(self, *values) -> int:
        """Add one or more values to the set.

        :param values: All arguments are treated as items to add.
        :returns: Number of items added to the set
        """
        return await self.client.sadd(self.key, *(json.dumps(_v) for _v in values))

    async def has(self, value):
        """Test if a value is in the set already

        :param value: Possible value within the set.
        :returns: boolean, true if value is in set.
        """
        return bool(await self.client.sismember(self.key, json.dumps(value)))

    async def all(self) -> typing.Set[Any]:
        """Load the entire set."""
        values = await self.client.smembers(self.key)
        return set((json.loads(v) for v in values))

    async def size(self) -> int:
        """Get the number of items in the set."""
        return await self.client.scard(self.key)

    async def remove(self, value) -> bool:
        """Remove value from the set

        :param value: Possible value in the set.
        :returns: True if the field was removed.
        """
        return await self.client.srem(self.key, json.dumps(value)) == 1

    async def clear(self):
        """Clear all values in the set.

        Removes the top level key from the redis database.
        """
        return await self.client.delete(self.key)


class Hash:
    """Interface to a redis hash.

    Can be constructed directly, or from an :class:`ObjectClient` factory.
    """
    def __init__(self, key: str, client: aioredis.Redis):
        """
        :param key: key in the redis server that is empty, or pointing to an existing hash
        :param client:
        """
        self.key = key
        self.client = client

    async def set(self, key: str, value) -> bool:
        """Set the value of a field in the hash.

        :param key: Key within the hash table.
        :param value: Unserialized value to write to the hash table.
        :return: True if the key is new.
        """
        return await self.client.hset(self.key, key, json.dumps(value)) == 1

    async def add(self, key: str, value) -> bool:
        """Add a field to the hash table.

        If a field with that key already exists, this operation does nothing.

        :param key: Key within the hash table.
        :param value: Unserialized value to write to the hash table.
        :returns: True if the value has been inserted.
        """
        return await self.client.hsetnx(self.key, key, json.dumps(value)) == 1

    async def get(self, key: str):
        """Read a field from the hash.

        :param key: Possible key within the hash table.
        :returns: Value if found, None otherwise.
        """
        value = await self.client.hget(self.key, key)
        if not value:
            return None
        return json.loads(value)

    async def mget(self, keys: Iterable[str]) -> Dict[str, Any]:
        """Read a set of fields from the hash.

        :param keys: Sequence of potential keys to load from the hash.
        """
        values = await self.client.hmget(self.key, *keys)
        return {
            k: json.loads(v)
            for k, v in zip(keys, values)
        }

    async def all(self) -> Dict[str, Any]:
        """Load the entire hash as a dict."""
        values = await self.client.hgetall(self.key)
        return {
            k.decode(): json.loads(v)
            for k, v in values.items()
        }

    async def keys(self) -> typing.Set[str]:
        """Read all the keys in the hash."""
        return {k.decode() for k in await self.client.hkeys(self.key)}

    async def size(self) -> int:
        """Get the number of items in the hash table."""
        return await self.client.hlen(self.key)

    async def delete(self, key) -> bool:
        """Remove a field from the hash.

        :param key: Possible key within the hash table.
        :returns: True if the field was removed.
        """
        return await self.client.hdel(self.key, key) == 1

    async def clear(self):
        """Clear all values in the hash.

        Removes the top level key from the redis database.
        """
        return await self.client.delete(self.key)


class Queue:
    """A queue interface to a redis list.

    Can be constructed directly, or from an :class:`ObjectClient` factory.
    """
    def __init__(self, key: str, client: aioredis.Redis):
        self.key = key
        self.client = client

    async def push(self, data):
        """Push an item to the queue.

        :param data: Item to push into queue.
        """
        await self.client.lpush(self.key, json.dumps(data))

    async def pop(self, timeout: int = 1) -> Any:
        """Pop an item from the front of the queue.

        :param timeout: Maximum time to wait for an item to become available in seconds.
        """
        message = await self.client.brpop(self.key, timeout=timeout)
        if message is None:
            return None
        return json.loads(message[1])

    async def pop_ready(self) -> Any:
        """Pop an item from the front of the queue if it is immediately available."""
        message = await self.client.rpop(self.key)
        if message is None:
            return None
        return json.loads(message)

    async def clear(self):
        """Drop all items from the queue."""
        await self.client.delete(self.key)

    async def length(self):
        """Number of items in the queue."""
        return await self.client.llen(self.key)


class PriorityQueue:
    """A priority queue interface to a redis sorted set.

    Can be constructed directly, or from an :class:`ObjectClient` factory.
    """
    def __init__(self, key: str, client: aioredis.Redis):
        self.key = key
        self.client = client

    async def push(self, data, priority=0):
        """Push an item to the queue.

        If `data` is already in the queue, reset its priority.

        :param data: Item to push into queue.
        :param priority: Sorting priority within the queue.
        """
        await self.client.zadd(self.key, priority, json.dumps(data))

    async def pop(self, timeout: int = 1) -> Any:
        """Pop the highest priority item from the queue.

        :param timeout: Maximum time to wait in seconds for an item to become available.
        """
        message = await self.client.bzpopmax(self.key, timeout=timeout)
        if message is None:
            return None
        return json.loads(message[1])

    async def pop_ready(self) -> Any:
        """Pop the highest priority item from the queue if one is available immediately."""
        message = await self.client.zpopmax(self.key)
        if not message:
            return None
        return json.loads(message[0])

    async def clear(self):
        """Drop all items from the queue."""
        await self.client.delete(self.key)

    async def score(self, item):
        """Get the current priority of `item`."""
        return await self.client.zscore(self.key, json.dumps(item))

    async def rank(self, item):
        """Get the distance of `item` from the front of the queue."""
        return await self.client.zrevrank(self.key, json.dumps(item))

    async def length(self):
        """Number of items in the queue."""
        return await self.client.zcount(self.key)


class LockContext:
    _delete_if_equal = """
    local key = KEYS[1]
    local value = ARGV[1]

    if redis.call('get', key) == value then
        redis.call('del', key)
        return true
    end

    return false
    """
    _delete_if_equal_sha = None

    def __init__(self, name, client, max_duration, timeout):
        self.name = name
        self.client = client
        self.max_duration = max_duration
        self.timeout = timeout or -float('inf')
        self.watcher = None
        self.unique_value = uuid.uuid4().hex

    async def __aenter__(self):
        # Make sure our script is loaded
        if not LockContext._delete_if_equal_sha:
            LockContext._delete_if_equal_sha = await self.client.script_load(LockContext._delete_if_equal)

        # Rather than do something clever, polling on the lock should be fine for now
        start = time.time()
        while not await self.client.setnx(self.name, self.unique_value):
            wait = min(0.1, time.time() - start - self.timeout)
            if wait < 0:
                raise asyncio.TimeoutError()
            await asyncio.sleep(wait)

        # Once we have the lock, set expiry and a local timeout
        await self.client.expire(self.name, int(self.max_duration))
        self.watcher = asyncio.ensure_future(self._cancel_this(_current_task(), self.max_duration))

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Clear up the lock
        if not self.watcher.done():
            self.watcher.cancel()
        await self.client.evalsha(self._delete_if_equal_sha, keys=[self.name], args=[self.unique_value])

    @staticmethod
    async def _cancel_this(target, timeout):
        await asyncio.sleep(timeout)
        target.cancel()


class Publisher:
    def __init__(self, default_channel, client):
        self.default_channel = default_channel
        self.client = client

    async def send(self, message=None, json=None, channel=None):
        channel = channel or self.default_channel
        if message:
            await self.client.publish(channel, message)
        elif json:
            await self.client.publish_json(channel, json)
        else:
            raise RuntimeError("Method Publisher.send requires at least one of 'message' and 'json' parameters")

    async def listeners(self) -> int:
        """Number of subscribers listening on the default channel of this publisher.

        Note: A significant caveat of this from redis is this is only those subscribed to the
              channel directly. An unknown number of additional listeners on patterns that
              include this channel may also exist.
        """
        return (await self.client.pubsub_numsub(self.default_channel))[self.default_channel.encode()]


class ObjectClient:
    """A client object to represent a redis server.

    Can be used as a factory to access data structures in the server as python objects.
    """
    def __init__(self, redis_client: aioredis.Redis):
        self._client = redis_client

    def queue(self, name: str) -> Queue:
        """Load a list to be used as a queue."""
        return Queue(name, self._client)

    def priority_queue(self, name: str) -> PriorityQueue:
        """Load a stateful-set to be used as a priority queue."""
        return PriorityQueue(name, self._client)

    def hash(self, name: str) -> Hash:
        """Load a hashtable."""
        return Hash(name, self._client)

    def set(self, name: str) -> Set:
        """Load a set."""
        return Set(name, self._client)

    def lock(self, name: str, max_duration: int = 60, timeout: int = None):
        """A redis resident lock to create mutex blocks across devices.

        :param name: A unique identifier for the lock
        :param max_duration: Max time to hold the lock in seconds
        :param timeout: Max time to wait to acquire the mutex
        :return:
        """
        name = '~~lock~~:' + name
        return LockContext(name, self._client, max_duration, timeout)

    def publisher(self, channel) -> Publisher:
        """Generate a publisher for redis' PUBSUB system.

        :param channel: Channel this publisher writes to by default.
        """
        return Publisher(channel, self._client)
