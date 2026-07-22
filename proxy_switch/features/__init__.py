"""Feature module registry.

Each feature module exports:
    NAME: str                         — unique identifier
    DESCRIPTION: str                  — human-readable description
    CONFIG_FILES: list[str]           — config file paths (for display)

    detect(executor=None) -> bool                 — is this tool available?
    enable(config_dict, executor=None) -> Result   — apply proxy config
    disable(executor=None) -> Result               — remove proxy config
    status(executor=None) -> StatusInfo            — check current state
    validate(executor=None) -> list[str]           — return configuration issues
"""

from __future__ import annotations

import importlib
import pkgutil
from types import ModuleType
from typing import Dict, List, Optional

_registry: Dict[str, ModuleType] = {}

# Explicit list for PyInstaller bundles where pkgutil.iter_modules won't work.
_FEATURE_PATHS = [
    "proxy_switch.features.system_proxy",
    "proxy_switch.features.apt",
    "proxy_switch.features.docker",
    "proxy_switch.features.npm",
    "proxy_switch.features.git",
    "proxy_switch.features.maven",
]


def discover() -> Dict[str, ModuleType]:
    """Discover all feature modules, keyed by NAME.

    Tries pkgutil first (source / editable install), then falls back
    to explicit imports for PyInstaller bundles.
    """
    if _registry:
        return _registry

    # Try pkgutil discovery first (works in source trees)
    found_modules = set()
    for importer, modname, ispkg in pkgutil.iter_modules(__path__):
        if modname.startswith("_"):
            continue
        module = importlib.import_module(f".{modname}", __package__)
        name = getattr(module, "NAME", modname)
        _registry[name] = module
        found_modules.add(name)

    # Fallback for PyInstaller: no modules found via pkgutil
    if not found_modules:
        for modpath in _FEATURE_PATHS:
            try:
                module = importlib.import_module(modpath)
                name = getattr(module, "NAME", modpath.rsplit(".", 1)[-1])
                _registry[name] = module
            except (ImportError, AttributeError):
                continue

    return _registry


def get_all() -> Dict[str, ModuleType]:
    """Return all discovered feature modules."""
    return dict(discover())


def get(name: str) -> Optional[ModuleType]:
    """Get a feature module by name, or None."""
    return discover().get(name)


def list_names() -> List[str]:
    """Return sorted feature module names."""
    return sorted(discover().keys())


def detect_installed(executor=None) -> Dict[str, bool]:
    """Return {name: is_installed} for all features."""
    result = {}
    for name, mod in discover().items():
        try:
            result[name] = mod.detect(executor)
        except Exception:
            result[name] = False
    return result
