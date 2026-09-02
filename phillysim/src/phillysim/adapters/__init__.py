"""Real source adapters (EP-5a): the three spine sources, one module each.

Each module declares how its source is acquired (:class:`~phillysim.download.SnapshotSpec`
with the adapter's own allowlist and guard limits), what the loaded table must
look like (:class:`~phillysim.contracts.SourceContract`), and how an admitted
snapshot is read with the Philadelphia County filter applied. :data:`ADAPTERS`
is the registry the real pipeline iterates, keyed by source name.
"""

from __future__ import annotations

from phillysim.adapters import acs, cenpop, tiger
from phillysim.adapters.base import Adapter

ADAPTERS: dict[str, Adapter] = {
    adapter.name: adapter for adapter in (acs.ADAPTER, cenpop.ADAPTER, tiger.ADAPTER)
}

__all__ = ["ADAPTERS", "Adapter"]
