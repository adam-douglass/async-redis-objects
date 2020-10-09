[![Actions Status](https://github.com/adam-douglass/async-redis-objects/workflows/unittests/badge.svg)](https://github.com/adam-douglass/draughts/actions)
[![codecov](https://codecov.io/gh/adam-douglass/async-redis-objects/branch/master/graph/badge.svg?token=6n3DbzkOwk)](https://codecov.io/gh/adam-douglass/async-redis-objects)

Async Redis Objects
===================

Some object orient wrappers around the redis interface provided by [`aioredis`](https://github.com/aio-libs/aioredis).

Notes
-----

 - Included:
   - hash table
   - queue (list)
   - priority queue (sorted set)
   - locks (keys)
 - Includes python implementation with matching interface for mocking. \
   `from async_redis_objects.mocks import ObjectClient`
 - tested on pypy and CPython 3.6 to 3.9
 - [API documentation on read the docs](https://async-redis-objects.readthedocs.io)

Example
-------

```python
import aioredis
import asyncio
from async_redis_objects import ObjectClient


async def main():
    # Connect with aioredis as normal
    redis = aioredis.Redis(await aioredis.pool.create_pool(address='redis://redis:6379', db=3, minsize=5))

    # Make an object client object with your redis object
    objects = ObjectClient(redis)

    # Access a hash table in redis
    table = objects.hash('hash-table-key')
    await table.set('name', 'Hello World')

    # Access a queue
    queue = objects.queue('queue-name')
    await queue.push(await table.get('name'))
    await queue.push(100000)

    # Access a priority queue
    pq = objects.priority_queue('other-queue-name')
    await pq.push({'name': 'same json serializable object'}, priority=100)
    await pq.push(await queue.pop(), priority=101)
    print(await pq.pop())  # Print Hello World

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
```
