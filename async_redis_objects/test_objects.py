import uuid
import asyncio

import pytest
import aioredis

from . import objects, mocks


def pytest_generate_tests(metafunc):
    if "client" in metafunc.fixturenames:
        metafunc.parametrize("client", ["mock", "live"], indirect=True)


@pytest.fixture
async def client(request):
    if request.param == 'mock':
        yield mocks.ObjectClient()
        return

    try:
        redis = aioredis.Redis(await aioredis.pool.create_pool(address='redis://localhost:6379', db=3, minsize=5))
        yield objects.ObjectClient(redis)
        await redis.flushdb()
        redis.close()
        await redis.wait_closed()
    except ConnectionRefusedError:  # pragma: no cover
        pytest.skip("No redis server available")


@pytest.mark.asyncio
async def test_hash_basics(client):
    new_hash = client.hash(uuid.uuid4().hex)

    # set something
    await new_hash.set('a', 10)
    await new_hash.set('b', 'abc')
    await new_hash.set('c', [1, 2, 3])
    await new_hash.set('d', {'char': 'a', 'num': 0})

    assert await new_hash.add('a2', 10) is True
    assert await new_hash.add('a2', 999) is False

    # Get them back
    assert 10 == await new_hash.get('a')
    assert 10 == await new_hash.get('a2')
    assert await new_hash.get('a3') is None
    assert 'abc' == await new_hash.get('b')
    assert [1, 2, 3] == await new_hash.get('c')
    assert {'char': 'a', 'num': 0} == await new_hash.get('d')

    # Get all the keys
    assert set(await new_hash.keys()) == {'a', 'a2', 'b', 'c', 'd'}
    assert await new_hash.delete('a2')
    assert not await new_hash.delete('a28473')
    assert set(await new_hash.keys()) == {'a', 'b', 'c', 'd'}
    assert await new_hash.all() == {
        'a': 10,
        'b': 'abc',
        'c': [1, 2, 3],
        'd': {'char': 'a', 'num': 0}
    }
    assert await new_hash.mget(['a', 'd']) == {
        'a': 10,
        'd': {'char': 'a', 'num': 0}
    }


@pytest.mark.asyncio
async def test_queue(client):
    queue = client.queue(uuid.uuid4().hex)

    await queue.push(100)
    await queue.push('cat')
    assert await queue.length() == 2

    assert await queue.pop_ready() == 100
    assert await queue.pop() == 'cat'
    assert await queue.length() == 0

    async def _then_add():
        await asyncio.sleep(0.01)
        await queue.push(999)

    asyncio.ensure_future(_then_add())
    assert await queue.pop_ready() is None
    assert await queue.pop(timeout=5) == 999
    assert await queue.pop() is None

    await queue.push(1)
    await queue.clear()
    assert await queue.length() == 0
    assert await queue.pop_ready() is None


@pytest.mark.asyncio
async def test_priority_queue(client):
    queue = client.priority_queue(uuid.uuid4().hex)

    await queue.push(100, priority=1)
    await queue.push('cat', priority=10)
    assert await queue.length() == 2

    assert await queue.score(100) == 1
    assert await queue.score('cat') == 10
    assert await queue.score('dog') is None
    assert await queue.rank(100) == 1
    assert await queue.rank('cat') == 0
    assert await queue.rank('dog') is None

    assert await queue.pop_ready() == 'cat'
    assert await queue.pop() == 100
    assert await queue.length() == 0

    async def _then_add():
        await asyncio.sleep(0.01)
        await queue.push(999)

    asyncio.ensure_future(_then_add())
    assert await queue.pop_ready() is None
    assert await queue.pop(timeout=5) == 999
    assert await queue.pop() is None

    await queue.push(1)
    await queue.clear()
    assert await queue.length() == 0
    assert await queue.pop_ready() is None
