"""CenPop2020 population-weighted tract centroids for Pennsylvania (source ``cenpop``).

**Stored as delivered, filtered at first read.** The Census Bureau publishes
the 2020 centers of population per state (``CenPop2020_Mean_TR42.txt``, one
row per 2020 tract: FIPS codes, 2020 Census population, and the mean center's
latitude and longitude in NAD 83). The state file is kept byte-for-byte so it
stays verifiable against the provider; :func:`read` keeps Philadelphia County
only, derives the eleven-digit ``geoid`` from the FIPS columns, and builds the
point geometry. These centroids are the routing origins methodology.md pins;
they are never recomputed from tract geometry.
"""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd

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

SOURCE = "cenpop"
VINTAGE = "CenPop2020"
FILE_NAME = "CenPop2020_Mean_TR42.txt"
URL = f"https://www2.census.gov/geo/docs/reference/cenpop2020/tract/{FILE_NAME}"
ALLOWLIST: tuple[str, ...] = ("www2.census.gov", "www.census.gov")
#: The Pennsylvania tract file is about 145 KB; the cap covers any state.
LIMITS = Limits(
    max_file_bytes=16 * 1024**2,
    max_extracted_bytes=16 * 1024**2,
    max_compression_ratio=50.0,
    max_members=1,
)
FIPS_COLUMNS = ("STATEFP", "COUNTYFP", "TRACTCE")

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
        f"{PUBLIC_DOMAIN}. {VINTAGE} centers of population by census tract, "
        "2020 Census counts (no sampling margin of error)."
    ),
)

CONTRACT = SourceContract(
    name=SOURCE,
    columns=(
        ColumnSpec("geoid", "str", nullable=False, pattern=TRACT_GEOID_PATTERN),
        ColumnSpec("STATEFP", "str", nullable=False, allowed=frozenset({STATE_FIPS})),
        ColumnSpec("COUNTYFP", "str", nullable=False, allowed=frozenset({COUNTY_FIPS})),
        ColumnSpec("TRACTCE", "str", nullable=False, pattern=r"\d{6}"),
        ColumnSpec("POPULATION", "int", nullable=False, minimum=0),
        ColumnSpec("LATITUDE", "float", nullable=False),
        ColumnSpec("LONGITUDE", "float", nullable=False),
    ),
    key="geoid",
    geometry=GeometrySpec(types=frozenset({"Point"}), crs=NAD83, bounds=COUNTY_BOUNDS),
    license_buckets=frozenset({"A"}),
)


def read(snapshot_dir: Path) -> gpd.GeoDataFrame:
    """Philadelphia County's tract centers from the admitted state file (NAD 83 points)."""
    table = pd.read_csv(
        snapshot_dir / FILE_NAME, dtype=dict.fromkeys(FIPS_COLUMNS, "string"), encoding="utf-8-sig"
    )
    keep = (table["STATEFP"] == STATE_FIPS) & (table["COUNTYFP"] == COUNTY_FIPS)
    table = table[keep].reset_index(drop=True)
    table.insert(0, "geoid", table["STATEFP"] + table["COUNTYFP"] + table["TRACTCE"])
    table = table.sort_values("geoid").reset_index(drop=True)
    return gpd.GeoDataFrame(
        table,
        geometry=gpd.points_from_xy(table["LONGITUDE"], table["LATITUDE"]),
        crs=NAD83,
    )


ADAPTER = Adapter(
    spec=SPEC,
    contract=CONTRACT,
    read=read,
    filter_note=(
        "stored as delivered (state-level text file, verifiable against the provider); "
        "county filter STATEFP/COUNTYFP applied at first read; geoid derived from the FIPS columns"
    ),
    citation="U.S. Census Bureau, Centers of Population by Census Tract, 2020.",
)
