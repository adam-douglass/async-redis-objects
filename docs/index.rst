Async Redis Objects
===================

.. toctree::
   :maxdepth: 2
   :hidden:

   Introduction <self>
   api
   Source <https://github.com/adam-douglass/async-redis-objects>

Some object orient wrappers around the redis interface provided by `aioredis <https://github.com/aio-libs/aioredis>`_.

After creating a connection with aioredis, construct an :class:`~async_redis_objects.objects.ObjectClient` which is a factory
for data structure objects. For testing there is an in process, local only, "mock" version
off all structures, with their own :class:`~async_redis_objects.mocks.ObjectClient` factory, in the ``async_redis_objects.mocks``
package.

.. note::
   If you are going to use blocking methods, you should probably use a aioredis
   pool rather than a single connection.


At the moment only a few basic structures are implemented:

- :class:`~async_redis_objects.objects.Hash`
- :class:`~async_redis_objects.objects.Queue`
- :class:`~async_redis_objects.objects.PriorityQueue`



