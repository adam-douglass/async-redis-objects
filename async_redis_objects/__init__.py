"""
In most cases it is sufficient to import only ``ObjectClient``, then construct
whatever objects you need from it.
"""

from .objects import ObjectClient
from . import mocks, objects
__all__ = ['ObjectClient', 'mocks', 'objects']
