import os
from setuptools import setup, find_packages
from pkg_resources import parse_version

setup(
    name="async_redis_objects",
    version=str(parse_version(os.environ.get('GITHUB_REF', "v0.0.0"))),
    packages=find_packages(),

    # metadata to display on PyPI
    author="Adam Douglass",
    author_email="douglass@malloc.ca",
    description="Object orient interface to aioredis.",
    long_description=open(os.path.join(os.path.dirname(__file__), 'readme.md')).read(),
    long_description_content_type='text/markdown',
    keywords="utility redis oop object-oriented",
    url="https://github.com/adam-douglass/async-redis-objects/",

    extras_require={
        'test': ['pytest', 'pytest-asyncio']
    },
    install_requires=['aioredis'],
)
