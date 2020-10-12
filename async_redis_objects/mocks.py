"""
A set of in-process pure python implementations to match the redis based objects.

The objects from this module implement the same interface as those from the
other modules, but are implemented as native python objects rather than redis calls.
Whenever possible the interface and semantics should be the same.
"""
import sys
import json
import asyncio
from asyncio import queues, wait_for, TimeoutError, Semaphore
import typing
from typing import Any, Dict

if sys.version_info[1] >= 7:
    _current_task = asyncio.current_task
else:
    _current_task = asyncio.Task.current_task


class Set:
    def __init__(self, encoder, decoder):
        self.data = set()
        self._encoder = encoder
        self._decoder = decoder

    async def add(self, *values) -> int:
        new = 0
        for item in values:
            new += int(item not in self.data)
            self.data.add(self._encoder(item))
        return new

    async def has(self, value):
        return self._encoder(value) in self.data

    async def all(self) -> typing.Set[Any]:
        return set((self._decoder(v) for v in self.data))

    async def size(self) -> int:
        return len(self.data)

    async def remove(self, value) -> bool:
        found = self._encoder(value) in self.data
        self.data.remove(self._encoder(value))
        return found

    async def clear(self):
        self.data = set()


class Queue:
    def __init__(self, encoder, decoder):
        self.queue = queues.Queue()
        self._encoder = encoder
        self._decoder = decoder

    async def push(self, data):
        await self.queue.put(self._encoder(data))

    async def pop(self, timeout: int = 1) -> Any:
        try:
            return self._decoder(await wait_for(self.queue.get(), timeout=timeout))
        except TimeoutError:
            return None

    async def pop_ready(self) -> Any:
        try:
            return self._decoder(self.queue.get_nowait())
        except queues.QueueEmpty:
            return None

    async def clear(self):
        self.queue = queues.Queue()

    async def length(self):
        return self.queue.qsize()


class PriorityQueue:
    def __init__(self, encoder, decoder):
        self.queue = []
        self.items = Semaphore(value=0)
        self._encoder = encoder
        self._decoder = decoder

    async def push(self, data, priority=0):
        self.queue.append((priority, self._encoder(data)))
        self.queue.sort()
        self.items.release()

    async def pop(self, timeout: int = 1) -> Any:
        try:
            await wait_for(self.items.acquire(), timeout)
            return self._decoder(self.queue.pop(-1)[1])
        except TimeoutError:
            return None

    async def pop_ready(self) -> Any:
        if self.items.locked():
            return None
        await self.items.acquire()
        return self._decoder(self.queue.pop(-1)[1])

    async def score(self, data):
        data = self._encoder(data)
        for priority, item in self.queue:
            if data == item:
                return priority
        return None

    async def rank(self, data):
        data = self._encoder(data)
        for index, (_, item) in enumerate(self.queue):
            if data == item:
                return len(self.queue) - index - 1
        return None

    async def clear(self):
        self.queue = []
        self.items = Semaphore(value=0)

    async def length(self):
        return len(self.queue)


class Hash:
    def __init__(self, encoder, decoder):
        self.data = {}
        self._encoder = encoder
        self._decoder = decoder

    async def keys(self) -> typing.Set[str]:
        return set(self.data.keys())

    async def size(self) -> int:
        """Get the number of items in the hash table."""
        return len(self.data)

    async def set(self, key, value) -> bool:
        """Returns if the key is new or not. Set is performed either way."""
        new = key in self.data
        self.data[key] = self._encoder(value)
        return new

    async def add(self, key, value) -> bool:
        """Returns if the key is new or not. Set only performed if key is new."""
        if key not in self.data:
            self.data[key] = self._encoder(value)
            return True
        return False

    async def get(self, key) -> Any:
        if key not in self.data:
            return None
        return self._decoder(self.data[key])

    async def mget(self, keys) -> Dict[str, Any]:
        return {
            k: self._decoder(self.data[k])
            for k in keys
        }

    async def all(self) -> Dict[str, Any]:
        return {
            k: self._decoder(v)
            for k, v in self.data.items()
        }

    async def delete(self, key) -> bool:
        if key in self.data:
            del self.data[key]
            return True
        return False

    async def clear(self):
        self.data = {}


class LockContext:
    def __init__(self, primitive, max_duration, timeout):
        self.primitive = primitive
        self.max_duration = max_duration
        self.timeout = timeout
        self.watcher = None

    async def __aenter__(self):
        await asyncio.wait_for(self.primitive.acquire(), timeout=self.timeout)
        self.watcher = asyncio.ensure_future(self._cancel_this(_current_task(), self.max_duration))

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if not self.watcher.done():
            self.watcher.cancel()
        self.primitive.release()

    @staticmethod
    async def _cancel_this(target, timeout):
        await asyncio.sleep(timeout)
        target.cancel()


class Publisher:
    def __init__(self, default_channel, encoder):
        self.default_channel = default_channel
        self._encoder = encoder

    async def send(self, message=None, json=None, channel=None):
        channel = channel or self.default_channel
        if message:
            pass
        elif json:
            pass
        else:
            raise RuntimeError("Method Publisher.send requires at least one of 'message' and 'json' parameters")

    async def listeners(self) -> int:
        return 0


class ObjectClient:
    def __init__(self, *_, encoder=None, decoder=None):
        self._queues = {}
        self._priority_queues = {}
        self._hashes = {}
        self._sets = {}
        self._locks = {}
        self._encoder = encoder or json.dumps
        self._decoder = decoder or json.loads

    def queue(self, name, encoder=None, decoder=None):
        if name not in self._queues:
            self._queues[name] = Queue(encoder=encoder or self._encoder, decoder=decoder or self._decoder)
        return self._queues[name]

    def priority_queue(self, name, encoder=None, decoder=None):
        if name not in self._priority_queues:
            self._priority_queues[name] = PriorityQueue(encoder=encoder or self._encoder,
                                                        decoder=decoder or self._decoder)
        return self._priority_queues[name]

    def hash(self, name, encoder=None, decoder=None):
        if name not in self._hashes:
            self._hashes[name] = Hash(encoder=encoder or self._encoder, decoder=decoder or self._decoder)
        return self._hashes[name]

    def set(self, name, encoder=None, decoder=None):
        if name not in self._sets:
            self._sets[name] = Set(encoder=encoder or self._encoder, decoder=decoder or self._decoder)
        return self._sets[name]

    def lock(self, name: str, max_duration: int = 60, timeout: int = None):
        """A lock within this python process

        :param name: A unique identifier for the lock
        :param max_duration: Max time to hold the lock in seconds
        :param timeout: Max time to wait to acquire the mutex
        :return:
        """
        if name not in self._locks:
            self._locks[name] = asyncio.Lock()
        return LockContext(self._locks[name], max_duration, timeout)

    def publisher(self, channel, encoder=None) -> Publisher:
        return Publisher(channel, encoder=encoder or self._encoder)
