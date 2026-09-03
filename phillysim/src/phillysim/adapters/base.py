"""What every source adapter declares, and the Philadelphia constants they share.

An :class:`Adapter` binds a :class:`~phillysim.download.SnapshotSpec` (how the
source is acquired: URLs, allowlist, limits, terms page, license) to a
:class:`~phillysim.contracts.SourceContract` (what the loaded table must look
like) and a ``read`` function that loads an admitted snapshot and applies the
Philadelphia County filter. The adapter also records, in prose, where that
filter sits (stored as delivered and filtered at first read, or requested
county-scoped) and why, because the packet brief asks for that per source.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from pyproj import Transformer

from phillysim.contracts import SourceContract
from phillysim.download import SnapshotSpec

STATE_FIPS = "42"  # Pennsylvania
COUNTY_FIPS = "101"  # Philadelphia County
COUNTY_GEOID = STATE_FIPS + COUNTY_FIPS
COUNTY_NAME = "Philadelphia County"
TRACT_GEOID_PATTERN = rf"{COUNTY_GEOID}\d{{6}}"  # eleven digits, 2020 tracts of the county

#: TIGER/Line and CenPop coordinates are NAD 83 (EPSG:4269), as delivered.
NAD83 = "EPSG:4269"
#: Philadelphia County with a margin, in NAD 83 degrees (minx, miny, maxx, maxy).
COUNTY_BOUNDS: tuple[float, float, float, float] = (-75.30, 39.85, -74.94, 40.15)
#: WGS 84, the CRS routing inputs (OSM, GTFS) are expressed in.
WGS84 = "EPSG:4326"
#: The analysis CRS, NAD 83 / UTM zone 18N in metres (ADR-0007); :mod:`phillysim.spine`
#: re-exports it and every buffer is measured in it.
ANALYSIS_CRS = "EPSG:26918"
#: The routing extent (ADR-0008): the county bounds buffered by this many metres in the
#: analysis CRS, expressed in WGS 84 for the network clip and the GTFS stop check.
ROUTING_BUFFER_M = 5000


def buffered_bounds(
    bounds: tuple[float, float, float, float],
    buffer_m: float,
    crs: str,
    *,
    bounds_crs: str = NAD83,
    out_crs: str = WGS84,
) -> tuple[float, float, float, float]:
    """``bounds`` (degrees in ``bounds_crs``) projected into the metric ``crs``, grown by
    ``buffer_m`` on every side, and expressed back in ``out_crs`` as the box enclosing the
    buffered rectangle's four corners (ADR-0007: buffers are measured in the analysis
    CRS, never in degrees)."""
    forward = Transformer.from_crs(bounds_crs, crs, always_xy=True)
    back = Transformer.from_crs(crs, out_crs, always_xy=True)
    minx, miny, maxx, maxy = bounds
    corners = [(minx, miny), (maxx, miny), (maxx, maxy), (minx, maxy)]
    projected = [forward.transform(x, y) for x, y in corners]
    pminx = min(x for x, _ in projected) - buffer_m
    pmaxx = max(x for x, _ in projected) + buffer_m
    pminy = min(y for _, y in projected) - buffer_m
    pmaxy = max(y for _, y in projected) + buffer_m
    box = [(pminx, pminy), (pmaxx, pminy), (pmaxx, pmaxy), (pminx, pmaxy)]
    out = [back.transform(x, y) for x, y in box]
    return (
        round(min(x for x, _ in out), 6),
        round(min(y for _, y in out), 6),
        round(max(x for x, _ in out), 6),
        round(max(y for _, y in out), 6),
    )


#: The terms page in force for Census Bureau data downloads, archived beside every
#: snapshot, and the sentence it must still carry (the packet's stop condition).
CENSUS_TERMS_URL = "https://www.census.gov/about/policies/open-gov.html"
CENSUS_TERMS_FILE = "terms.html"
CENSUS_TERMS_PHRASE = (
    "publishes its data as open data, meaning it is freely available for use and "
    "re-use by the public"
)
#: The legal basis every Census source's license note cites.
PUBLIC_DOMAIN = (
    "US public domain: a work of the United States Government (17 U.S.C. section 105); "
    "the Census Bureau publishes its data as open data, freely available for use and "
    "re-use, and asks to be cited as the source"
)


@dataclass(frozen=True)
class Adapter:
    """One real source: how it is acquired, what it must look like, how it is read."""

    spec: SnapshotSpec
    contract: SourceContract
    read: Callable[[Path], pd.DataFrame]
    filter_note: str
    #: How the source is cited in published outputs (the attribution line the public
    #: manifest and every in-file license label carry; docs/DATA-LICENSES.md).
    citation: str = ""

    @property
    def name(self) -> str:
        return self.spec.source

    def __post_init__(self) -> None:
        if self.contract.name != self.spec.source:
            raise ValueError(
                f"adapter {self.spec.source!r}: contract is named {self.contract.name!r}"
            )
