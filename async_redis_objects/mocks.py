import json
from asyncio import queues, wait_for, TimeoutError, Semaphore
from typing import Any, Set, Dict


class ObjectClient:
    def __init__(self, *_):
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

    async def pop(self, timeout: int = 1) -> Any:
        try:
            return json.loads(await wait_for(self.queue.get(), timeout=timeout))
        except TimeoutError:
            return None

    async def pop_ready(self) -> Any:
        try:
            return json.loads(self.queue.get_nowait())
        except queues.QueueEmpty:
            return None

    async def clear(self):
        self.queue = queues.Queue()

    async def length(self):
        return self.queue.qsize()


class PriorityQueue:
    def __init__(self):
        self.queue = []
        self.items = Semaphore(value=0)

    async def push(self, data, priority=0):
        self.queue.append((priority, json.dumps(data)))
        self.queue.sort()
        self.items.release()

    async def pop(self, timeout: int = 1) -> Any:
        try:
            await wait_for(self.items.acquire(), timeout)
            return json.loads(self.queue.pop(-1)[1])
        except TimeoutError:
            return None

    async def pop_ready(self) -> Any:
        if self.items.locked():
            return None
        await self.items.acquire()
        return json.loads(self.queue.pop(-1)[1])

    async def score(self, data):
        data = json.dumps(data)
        for priority, item in self.queue:
            if data == item:
                return priority
        return None

    async def rank(self, data):
        data = json.dumps(data)
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
    def __init__(self):
        self.data = {}

    async def keys(self) -> Set[str]:
        return set(self.data.keys())

    async def set(self, key, value) -> bool:
        """Returns if the key is new or not. Set is performed either way."""
        new = key in self.data
        self.data[key] = json.dumps(value)
        return new

    async def add(self, key, value) -> bool:
        """Returns if the key is new or not. Set only performed if key is new."""
        if key not in self.data:
            self.data[key] = json.dumps(value)
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
