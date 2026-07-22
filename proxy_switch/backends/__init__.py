"""Backend auto-discovery.

Walks all modules in the backends directory, finds Backend subclasses,
and registers them in a dict keyed by backend name.
"""

import importlib
import pkgutil
from typing import Dict, Type

from .base import Backend


_backend_registry: Dict[str, Type[Backend]] = {}


def _discover_backends():
    """Import all backend modules and register Backend subclasses."""
    for importer, modname, ispkg in pkgutil.iter_modules(__path__):
        if modname == "base" or modname.startswith("_"):
            continue
        module = importlib.import_module(f"{__name__}.{modname}")
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, type) and issubclass(attr, Backend) and attr is not Backend:
                _backend_registry[attr.name()] = attr


def get_all_backends() -> Dict[str, Type[Backend]]:
    """Return dict of all discovered backends: {name: class}."""
    if not _backend_registry:
        _discover_backends()
    return dict(_backend_registry)


def get_backends(names=None):
    """Return filtered backends.

    Args:
        names: List of backend names to include, or None for all.

    Returns:
        Dict of {name: class} for matching backends.
    """
    all_backends = get_all_backends()
    if names is None:
        return all_backends
    return {n: all_backends[n] for n in names if n in all_backends}
