"""TIGER/Line 2025 roads for Philadelphia County, primary and secondary (source ``tiger_roads``).

**Requested county-scoped, filtered at first read.** The Census Bureau
distributes the roads layer per county (``tl_2025_42101_roads.zip``, every
road feature of Philadelphia County with its MTFCC feature class), so unlike
the tract and center files there is a provider file that already carries the
county scope; it is kept byte-for-byte so ``phillysim verify`` can check the
snapshot against the provider, and it is inspected (slip, bomb) at
acquisition and at every admission. :func:`read` opens the shapefile straight
from the zip through pyogrio (nothing is extracted to disk) and keeps the
**major** roads only: MTFCC ``S1100`` (primary roads: interstates and other
limited-access highways) and ``S1200`` (secondary roads: US, state, and
county highways and the main arterials). Those two classes are what
ADR-0005's minimal basemap draws; the local streets (``S1400``), ramps,
service drives, alleys, and walkways in the same file are dropped at the
read, so the county filter of the other TIGER adapters becomes a feature
class filter here (the provider did the county part).

Coordinates are NAD 83 as delivered; the ``basemap`` stage reprojects into
the analysis CRS (ADR-0007) and the public zone carries WGS 84.
"""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd

from phillysim.adapters.base import (
    CENSUS_TERMS_FILE,
    CENSUS_TERMS_PHRASE,
    CENSUS_TERMS_URL,
    COUNTY_BOUNDS,
    COUNTY_GEOID,
    NAD83,
    PUBLIC_DOMAIN,
    Adapter,
)
from phillysim.contracts import ColumnSpec, GeometrySpec, SourceContract
from phillysim.download import Fetch, SnapshotSpec
from phillysim.guards import Limits

SOURCE = "tiger_roads"
VINTAGE = "TIGER/Line 2025"
FILE_NAME = f"tl_2025_{COUNTY_GEOID}_roads.zip"
URL = f"https://www2.census.gov/geo/tiger/TIGER2025/ROADS/{FILE_NAME}"
ALLOWLIST: tuple[str, ...] = ("www2.census.gov", "www.census.gov")
#: The 2025 Philadelphia County roads zip is about 1.4 MB with seven members (about
#: 3.5 MB uncompressed); the caps leave room for any county and later vintages.
LIMITS = Limits(
    max_file_bytes=16 * 1024**2,
    max_extracted_bytes=64 * 1024**2,
    max_compression_ratio=50.0,
    max_members=20,
)
#: The MTFCC feature classes kept: primary (S1100) and secondary (S1200) roads.
MAJOR_ROAD_CLASSES: frozenset[str] = frozenset({"S1100", "S1200"})
#: TIGER route type codes (RTTYP): C county, I interstate, M common name, O other,
#: S state recognized, U U.S.
ROUTE_TYPES: frozenset[str] = frozenset({"C", "I", "M", "O", "S", "U"})

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
        "TIGER/Line is a registered trademark of the Census Bureau. County roads file, "
        "primary and secondary roads (MTFCC S1100 / S1200) kept at read."
    ),
)

CONTRACT = SourceContract(
    name=SOURCE,
    columns=(
        ColumnSpec("LINEARID", "str", nullable=False, pattern=r"\d{10,16}"),
        ColumnSpec("FULLNAME", "str", nullable=True),
        ColumnSpec("RTTYP", "str", nullable=False, allowed=ROUTE_TYPES),
        ColumnSpec("MTFCC", "str", nullable=False, allowed=MAJOR_ROAD_CLASSES),
    ),
    key="LINEARID",
    geometry=GeometrySpec(
        types=frozenset({"LineString", "MultiLineString"}), crs=NAD83, bounds=COUNTY_BOUNDS
    ),
    license_buckets=frozenset({"A"}),
)


def read_all(snapshot_dir: Path) -> gpd.GeoDataFrame:
    """Every road feature of the county file, as delivered (NAD 83), before the class filter."""
    archive = snapshot_dir / FILE_NAME
    return gpd.read_file(f"zip://{archive.as_posix()}")


def read(snapshot_dir: Path) -> gpd.GeoDataFrame:
    """The county's primary and secondary roads from the admitted zip, as delivered (NAD 83)."""
    frame = read_all(snapshot_dir)
    keep = frame["MTFCC"].isin(MAJOR_ROAD_CLASSES)
    return frame[keep].sort_values("LINEARID").reset_index(drop=True)


ADAPTER = Adapter(
    spec=SPEC,
    contract=CONTRACT,
    read=read,
    filter_note=(
        "requested county-scoped (the provider distributes roads per county; stored as "
        "delivered, verifiable against the provider); feature-class filter MTFCC S1100 / "
        "S1200 (primary and secondary roads) applied at first read"
    ),
    citation="U.S. Census Bureau, TIGER/Line Shapefiles 2025, roads.",
)
