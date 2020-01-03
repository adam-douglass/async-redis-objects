from setuptools import setup, find_packages

setup(
    name="async_redis_objects",
    version="0.0",
    packages=find_packages(),

    # metadata to display on PyPI
    author="Adam Douglass",
    author_email="douglass@malloc.ca",
    description="Object orient interface to aioredis.",
    keywords="utility redis oop object-oriented",
    url="https://github.com/adam-douglass/draughts/",

    extras_require={
        'test': ['pytest', 'pytest-asyncio']
    },
    install_requires=['aioredis']
)
