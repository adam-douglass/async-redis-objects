import json
from asyncio import queues, wait_for, TimeoutError
from typing import Any, Set, Dict


class ObjectClient:
    def __init__(self):
        self._queues = {}
        self._priority_queues = {}
        self._hashes = {}

    def queue(self, name):
        if name not in self._queues:
            self._queues[name] = Queue()
        return self._queues[name]

    def priority_queue(self, name):
        if name not in self._priority_queues:
            self._priority_queues[name] = PriorityQueue()
        return self._priority_queues[name]

    def hash(self, name):
        if name not in self._hashes:
            self._hashes[name] = Hash()
        return self._hashes[name]


class Queue:
    def __init__(self):
        self.queue = queues.Queue()

    async def push(self, data):
        await self.queue.put(json.dumps(data))

    async def pop(self, timeout: int = 1, blocking: bool = True) -> Any:
        if blocking:
            message = await self.queue.get()
        else:
            message = await self.queue.get_nowait()
        if message is None:
            return None
        return json.loads(message)

    async def clear(self):
        self.queue = queues.Queue()

    async def qsize(self):
        return self.queue.qsize()


class PriorityQueue:
    def __init__(self):
        self.queue = queues.PriorityQueue()

    async def push(self, data, priority=0):
        await self.queue.put((-priority, json.dumps(data)))

    async def pop(self, timeout: int = 1, blocking: bool = True) -> Any:
        if blocking:
            try:
                message = await wait_for(self.queue.get(), timeout)
            except TimeoutError:
                return None
        else:
            message = self.queue.get_nowait()

        if message is None:
            return None

        return json.loads(message[1])

    async def score(self, data):
        return 1

    async def clear(self):
        self.queue = queues.PriorityQueue()


class Hash:
    def __init__(self):
        self.data = {}

    async def keys(self) -> Set[str]:
        return set(self.data.keys())

    async def set(self, key, value) -> bool:
        """Returns if the key is new or not. Set is performed either way."""
        new = key in self.data
        self.data[key] = value
        return new

    async def add(self, key, value) -> bool:
        """Returns if the key is new or not. Set only performed if key is new."""
        if key in self.data:
            self.data[key] = value
            return True
        return False

    async def get(self, key) -> Any:
        if key not in self.data:
            return None
        return json.loads(self.data[key])

    async def mget(self, keys) -> Dict[str, Any]:
        return {
            k: json.loads(self.data[k])
            for k in keys
        }

    async def all(self) -> Dict[str, Any]:
        return {
            k: json.loads(v)
            for k, v in self.data.items()
        }

    async def delete(self, key) -> bool:
        if key in self.data:
            del self.data[key]
            return True
        return False

