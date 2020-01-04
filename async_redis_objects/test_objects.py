import uuid

import pytest
import aioredis

from . import objects, mocks
from .objects import Hash


def pytest_generate_tests(metafunc):
    if "client" in metafunc.fixturenames:
        metafunc.parametrize("client", ["mock", "live"], indirect=True)


@pytest.fixture
async def client(request):
    if request.param == 'mock':
        yield mocks.ObjectClient()
        return

    try:
        redis = aioredis.Redis(await aioredis.pool.create_connection(address='redis://localhost:6379', db=3))
        yield objects.ObjectClient(redis)
        await redis.flushdb()
        redis.close()
        await redis.wait_closed()
    except ConnectionRefusedError:
        pytest.skip("No redis server available")


@pytest.fixture
async def new_hash(client):
    return client.hash(uuid.uuid4().hex)


@pytest.mark.asyncio
async def test_hash_basics(new_hash: Hash):
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
