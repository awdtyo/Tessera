"""Auto-discovery for plug-in modules in tessera.modules.

Signal: none (infrastructure). Failure modes: broken module file must not
crash discovery — it is logged and skipped. Reliability: n/a.
"""

import importlib
import inspect
import logging
import pkgutil
from types import ModuleType

from tessera.core.module import Module

logger = logging.getLogger(__name__)


def _iter_submodules(package: ModuleType) -> list[str]:
    path = getattr(package, "__path__", None)
    if path is None:
        return []
    names: list[str] = []
    for info in pkgutil.iter_modules(path):
        names.append(info.name)
    return sorted(names)


def discover_modules(package_name: str = "tessera.modules") -> list[Module]:
    """Import every submodule of package_name and collect Module instances.

    A submodule contributes modules via either convention:
    1. a module-level ``MODULE: Module`` instance, or
    2. concrete ``Module`` subclasses defined in it (instantiated with no args).

    Import errors are logged and skipped so one broken plug-in never
    breaks a run. Results are sorted by module id for determinism.
    """
    package = importlib.import_module(package_name)
    found: dict[str, Module] = {}
    for sub in _iter_submodules(package):
        full = f"{package_name}.{sub}"
        try:
            mod = importlib.import_module(full)
        except Exception as exc:  # noqa: BLE001 - isolation is the point
            logger.warning("Skipping module %s: import failed: %s", full, exc)
            continue
        for candidate in _collect_from(mod):
            if candidate.id in found:
                logger.warning("Duplicate module id %s in %s; keeping first", candidate.id, full)
                continue
            found[candidate.id] = candidate
    return [found[k] for k in sorted(found)]


def _collect_from(mod: ModuleType) -> list[Module]:
    out: list[Module] = []
    direct = getattr(mod, "MODULE", None)
    if isinstance(direct, Module):
        out.append(direct)
    for _name, member in inspect.getmembers(mod, inspect.isclass):
        if issubclass(member, Module) and member is not Module:
            if member.__module__ != mod.__name__:
                continue  # imported, not defined here
            if inspect.isabstract(member):
                continue
            try:
                out.append(member())
            except Exception as exc:  # noqa: BLE001
                logger.warning("Skipping %s: instantiate failed: %s", member, exc)
    # De-duplicate while preserving order.
    seen: set[str] = set()
    unique: list[Module] = []
    for m in out:
        if m.id not in seen:
            seen.add(m.id)
            unique.append(m)
    return unique
