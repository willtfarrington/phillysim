"""USDA SNAP Retailer Locator historical data (source ``snap_retailers``).

**Stored as delivered, filtered at first read.** USDA's Food and Nutrition
Administration (FNA; the Food and Nutrition Service until 2026-06-01, hence
the dual URLs) publishes one nationwide zipped CSV of every retailer
authorized to accept SNAP benefits at any point in the past twenty calendar
years (``snap-retailer-locator-data2005-2025.zip``, one member,
``Historical SNAP Retailer Locator Data 2005-2025.csv``): record ID, store
name, USDA store type, address, latitude / longitude, authorization date,
and end date (blank while the authorization is open). The file is kept
byte-for-byte and read from the zip in place; :func:`read` keeps
Philadelphia County only (``State == "PA"`` and ``County == "PHILADELPHIA"``,
the provider's own county attribution) **and only authorization spells open
at the file's as-of date** (:data:`AS_OF`; a blank end date), so one row per
record ID remains and the table is the set of SNAP-authorized retailers as
of that date, which is the universe M5's SRAM comparison needs and the
input the supermarket-format layer classifies.

Coordinates are the provider's geocodes with no stated datum; they are
treated as WGS 84 (:data:`COORDINATE_CRS`), which in Philadelphia differs
from NAD 83 by less than the geocoding error. The download redirects from the
FNA host to its content-delivery host, which the allowlist therefore names.

There is no USDA terms page the guarded path can archive: the department's
"Policies and Links" page, which states that USDA web content is in the
public domain, refuses non-browser clients (HTTP 403, 2026-09-02). The page
archived beside the data is therefore the provider's own data page in force
(:data:`PAGE_URL`), and the wording the download path checks is its official
US-government banner and its **as-of date** sentence, so a provider refresh
that changes the vintage stops acquisition (the controlled-refresh rule)
rather than silently delivering a different file. The license basis is the
statute (17 U.S.C. section 105), as for every federal source.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import geopandas as gpd
import pandas as pd

from phillysim.adapters.base import COUNTY_BOUNDS, Adapter
from phillysim.classify import store_format
from phillysim.contracts import ColumnSpec, GeometrySpec, SourceContract
from phillysim.download import Fetch, SnapshotSpec
from phillysim.guards import Limits

SOURCE = "snap_retailers"
VINTAGE = "SNAP Retailer Locator Historical Data 2005-2025"
#: The date the provider states the file is current as of (its page: "Dec. 31, 2025").
AS_OF = "2025-12-31"
FILE_NAME = "snap-retailer-locator-data2005-2025.zip"
MEMBER = "Historical SNAP Retailer Locator Data 2005-2025.csv"
_PATH = f"/sites/default/files/resource-files/{FILE_NAME}"
URL = f"https://www.fna.usda.gov{_PATH}"
URL_ALT = f"https://www.fns.usda.gov{_PATH}"
PAGE_URL = "https://www.fna.usda.gov/snap/retailer-locator/data"
PAGE_URL_ALT = "https://www.fns.usda.gov/snap/retailer/historical-data"
PAGE_FILE = "source-page.html"
PAGE_PHRASES: tuple[str, ...] = (
    "An official website of the United States government",
    "This data is current as of Dec. 31, 2025",
)
#: The FNA host, the pre-rename FNS host (redirects to FNA), and the content-delivery host
#: the FNA file URL redirects to (observed 2026-09-02); redirect targets are allowlisted too.
ALLOWLIST: tuple[str, ...] = (
    "www.fna.usda.gov",
    "www.fns.usda.gov",
    "fna-bwbufwdzbabpezgc.z01.azurefd.us",
)
#: The 2005-2025 zip is about 24 MB holding one 95 MB CSV (ratio about 4).
LIMITS = Limits(
    max_file_bytes=64 * 1024**2,
    max_extracted_bytes=512 * 1024**2,
    max_compression_ratio=50.0,
    max_members=4,
)
#: The provider's geocodes carry no stated datum; treated as WGS 84 (see the docstring).
COORDINATE_CRS = "EPSG:4326"
STATE = "PA"
COUNTY = "PHILADELPHIA"
DATE_FORMAT = "%m/%d/%Y"
PUBLIC_DOMAIN = (
    "US public domain: a work of the United States Government (17 U.S.C. section 105), "
    "published by USDA's Food and Nutrition Administration as public data on authorized "
    "SNAP retailers; USDA asks to be cited as the source"
)

#: The provider's column names, verbatim; :func:`read` returns exactly these.
COLUMNS: tuple[str, ...] = (
    "Record ID",
    "Store Name",
    "Store Type",
    "Street Number",
    "Street Name",
    "Additional Address",
    "City",
    "State",
    "Zip Code",
    "Zip4",
    "County",
    "Latitude",
    "Longitude",
    "Authorization Date",
    "End Date",
)

SPEC = SnapshotSpec(
    source=SOURCE,
    acquisition_url=URL,
    acquisition_url_alt=URL_ALT,
    files=(Fetch(URL, FILE_NAME, url_alt=URL_ALT),),
    terms=Fetch(PAGE_URL, PAGE_FILE, url_alt=PAGE_URL_ALT),
    terms_must_contain=PAGE_PHRASES,
    allowlist=ALLOWLIST,
    limits=LIMITS,
    license_bucket="A",
    license_note=(
        f"{PUBLIC_DOMAIN}. {VINTAGE}, current as of {AS_OF}; no terms page beyond the "
        "provider's data page exists on a host the guarded path can reach."
    ),
)

CONTRACT = SourceContract(
    name=SOURCE,
    columns=(
        ColumnSpec("Record ID", "str", nullable=False, pattern=r"\d+"),
        ColumnSpec("Store Name", "str", nullable=False),
        # Every label must be one the published mapping knows: a new provider label is
        # the packet's stop condition and surfaces here as a contract violation.
        ColumnSpec(
            "Store Type", "str", nullable=False, allowed=frozenset(store_format.store_types())
        ),
        ColumnSpec("Street Number", "str"),
        ColumnSpec("Street Name", "str"),
        ColumnSpec("Additional Address", "str"),
        ColumnSpec("City", "str", nullable=False),
        ColumnSpec("State", "str", nullable=False, allowed=frozenset({STATE})),
        ColumnSpec("Zip Code", "str", nullable=False, pattern=r"\d{5}"),
        ColumnSpec("Zip4", "str"),
        ColumnSpec("County", "str", nullable=False, allowed=frozenset({COUNTY})),
        ColumnSpec("Latitude", "float", nullable=False),
        ColumnSpec("Longitude", "float", nullable=False),
        ColumnSpec("Authorization Date", "str", nullable=False, pattern=r"\d{1,2}/\d{1,2}/\d{4}"),
        # Open authorizations only, so the end date is null on every row.
        ColumnSpec("End Date", "str"),
    ),
    key="Record ID",
    geometry=GeometrySpec(types=frozenset({"Point"}), crs=COORDINATE_CRS, bounds=COUNTY_BOUNDS),
    license_buckets=frozenset({"A"}),
)


def read_all(snapshot_dir: Path) -> pd.DataFrame:
    """Every row of the admitted file as text (whitespace stripped, blank cells null)."""
    with zipfile.ZipFile(snapshot_dir / FILE_NAME) as archive, archive.open(MEMBER) as handle:
        table = pd.read_csv(handle, dtype="string", encoding="utf-8-sig", keep_default_na=False)
    if tuple(table.columns) != COLUMNS:
        raise ValueError(f"{MEMBER}: columns {tuple(table.columns)} != expected {COLUMNS}")
    for column in COLUMNS:
        stripped = table[column].str.strip()
        table[column] = stripped.mask(stripped == "")
    return table


def read(snapshot_dir: Path) -> gpd.GeoDataFrame:
    """Philadelphia County's SNAP-authorized retailers as of :data:`AS_OF` (WGS 84 points)."""
    table = read_all(snapshot_dir)
    keep = (
        (table["State"] == STATE)
        & (table["County"].str.upper() == COUNTY)
        & table["End Date"].isna()
    )
    table = table[keep].copy()
    for column in ("Latitude", "Longitude"):
        table[column] = pd.to_numeric(table[column], errors="raise").astype("float64")
    order = table["Record ID"].astype("int64")
    table = table.iloc[order.argsort(kind="stable").to_numpy()].reset_index(drop=True)
    return gpd.GeoDataFrame(
        table,
        geometry=gpd.points_from_xy(table["Longitude"], table["Latitude"]),
        crs=COORDINATE_CRS,
    )


ADAPTER = Adapter(
    spec=SPEC,
    contract=CONTRACT,
    read=read,
    filter_note=(
        "stored as delivered (nationwide zipped CSV, verifiable against the provider, read "
        "from the zip in place); at first read: State PA and County PHILADELPHIA (the "
        f"provider's attribution), authorization spells open at the file's as-of date {AS_OF} "
        "(blank end date), blank cells null, coordinates as float"
    ),
)
