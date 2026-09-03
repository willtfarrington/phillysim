"""TIGER/Line 2025 census tracts for Pennsylvania (source ``tiger_tracts``).

**Stored as delivered, filtered at first read.** The Census Bureau distributes
the tract layer per state (``tl_2025_42_tract.zip``, 2020-vintage tracts as of
2025-01-01); there is no county file to request. Keeping the provider's zip
byte-for-byte lets ``phillysim verify`` and anyone else check the snapshot
against the provider, and the zip is inspected (slip, bomb) at acquisition and
at every admission. :func:`read` opens the shapefile straight from the zip
through pyogrio (nothing is extracted to disk) and keeps Philadelphia County
only (``STATEFP == "42"`` and ``COUNTYFP == "101"``): architecture.md's early
county filter sits at the first read.

Coordinates are NAD 83 as delivered; EP-5b reprojects into the analysis CRS.
"""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd

from phillysim.adapters.base import (
    CENSUS_TERMS_FILE,
    CENSUS_TERMS_PHRASE,
    CENSUS_TERMS_URL,
    COUNTY_BOUNDS,
    COUNTY_FIPS,
    NAD83,
    PUBLIC_DOMAIN,
    STATE_FIPS,
    TRACT_GEOID_PATTERN,
    Adapter,
)
from phillysim.contracts import ColumnSpec, GeometrySpec, SourceContract
from phillysim.download import Fetch, SnapshotSpec
from phillysim.guards import Limits

SOURCE = "tiger_tracts"
VINTAGE = "TIGER/Line 2025"
FILE_NAME = "tl_2025_42_tract.zip"
URL = f"https://www2.census.gov/geo/tiger/TIGER2025/TRACT/{FILE_NAME}"
ALLOWLIST: tuple[str, ...] = ("www2.census.gov", "www.census.gov")
#: The 2025 Pennsylvania tract zip is about 13 MB with six members (about 60 MB
#: uncompressed); the caps leave room for every state and later vintages.
LIMITS = Limits(
    max_file_bytes=64 * 1024**2,
    max_extracted_bytes=512 * 1024**2,
    max_compression_ratio=50.0,
    max_members=20,
)

SPEC = SnapshotSpec(
    source=SOURCE,
    acquisition_url=URL,
    files=(Fetch(URL, FILE_NAME),),
    terms=Fetch(CENSUS_TERMS_URL, CENSUS_TERMS_FILE),
    terms_must_contain=(CENSUS_TERMS_PHRASE,),
    allowlist=ALLOWLIST,
    limits=LIMITS,
    license_bucket="A",
    license_note=(
        f"{PUBLIC_DOMAIN}. {VINTAGE} technical documentation section 1.2: copyright "
        "protection is not available for any work of the United States Government; "
        "TIGER/Line is a registered trademark of the Census Bureau."
    ),
)

CONTRACT = SourceContract(
    name=SOURCE,
    columns=(
        ColumnSpec("GEOID", "str", nullable=False, pattern=TRACT_GEOID_PATTERN),
        ColumnSpec("STATEFP", "str", nullable=False, allowed=frozenset({STATE_FIPS})),
        ColumnSpec("COUNTYFP", "str", nullable=False, allowed=frozenset({COUNTY_FIPS})),
        ColumnSpec("TRACTCE", "str", nullable=False, pattern=r"\d{6}"),
        ColumnSpec("NAME", "str", nullable=False),
        ColumnSpec("NAMELSAD", "str", nullable=False),
        ColumnSpec("ALAND", "int", nullable=False, minimum=0),
        ColumnSpec("AWATER", "int", nullable=False, minimum=0),
    ),
    key="GEOID",
    geometry=GeometrySpec(
        types=frozenset({"Polygon", "MultiPolygon"}), crs=NAD83, bounds=COUNTY_BOUNDS
    ),
    license_buckets=frozenset({"A"}),
)


def read(snapshot_dir: Path) -> gpd.GeoDataFrame:
    """Philadelphia County's tracts from the admitted state zip, as delivered (NAD 83)."""
    archive = snapshot_dir / FILE_NAME
    frame = gpd.read_file(f"zip://{archive.as_posix()}")
    keep = (frame["STATEFP"] == STATE_FIPS) & (frame["COUNTYFP"] == COUNTY_FIPS)
    return frame[keep].sort_values("GEOID").reset_index(drop=True)


ADAPTER = Adapter(
    spec=SPEC,
    contract=CONTRACT,
    read=read,
    filter_note=(
        "stored as delivered (state-level zip, verifiable against the provider); "
        "county filter STATEFP/COUNTYFP applied at first read"
    ),
    citation="U.S. Census Bureau, TIGER/Line Shapefiles 2025.",
)
