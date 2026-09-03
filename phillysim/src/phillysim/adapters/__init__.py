"""Real source adapters: the three spine sources (EP-5a), the first destination
source, USDA SNAP retailers (EP-6), the basemap's TIGER roads (EP-8b), and the
two routing sources, the OpenStreetMap extract and SEPTA's GTFS feed (EP-12),
one module each.

Each module declares how its source is acquired (:class:`~phillysim.download.SnapshotSpec`
with the adapter's own allowlist and guard limits), what the loaded table must
look like (:class:`~phillysim.contracts.SourceContract`), and how an admitted
snapshot is read with the Philadelphia County filter applied (for the routing
sources, whose files are not tables, ``read`` returns the summary the
``validate`` stage checks and the ``network`` stage calls the module's clip or
unwrap). :data:`ADAPTERS` is the registry the real pipeline iterates, keyed by
source name.
"""

from __future__ import annotations

from phillysim.adapters import acs, cenpop, osm, septa_gtfs, snap, tiger, tiger_roads
from phillysim.adapters.base import Adapter

ADAPTERS: dict[str, Adapter] = {
    adapter.name: adapter
    for adapter in (
        acs.ADAPTER,
        cenpop.ADAPTER,
        snap.ADAPTER,
        tiger.ADAPTER,
        tiger_roads.ADAPTER,
        osm.ADAPTER,
        septa_gtfs.ADAPTER,
    )
}

__all__ = ["ADAPTERS", "Adapter"]
