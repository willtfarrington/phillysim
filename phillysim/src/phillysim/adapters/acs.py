"""ACS 5-year 2020-2024 selected tables with margins of error (source ``acs``).

**Stored as delivered, filtered at first read.** The pinned variable list is
the one the fixture and the ``demographics`` stage already name, and nothing
more (anything more is a methods-version bump, ADR-0006): ``B01003_001`` (total
population, the denominator) and ``B08201_002`` (households with no vehicle
available, the car-free context methodology.md states). Each table comes from
the Census Bureau's table-based summary file for the 2020-2024 5-year release
(``acsdt5y2024-<table>.dat``: pipe-delimited, one row per geography at every
summary level, estimate and margin-of-error columns interleaved as
``<TABLE>_E<line>`` / ``<TABLE>_M<line>``). The files are kept byte-for-byte
because they are what the provider publishes; :func:`read` keeps the county's
tracts (``GEO_ID`` prefix ``1400000US42101``), selects the pinned lines,
renames them to the data dictionary's ``<table>_<line>E`` / ``…M`` form, and
turns the provider's annotation values into nulls (ADR-0004: suppressed cells
stay null, never imputed).

Why the summary file and not the API the brief anticipated: on 2026-09-02
``api.census.gov`` redirected every key-less request to ``missing_key.html``,
so the API path would make a secret a prerequisite for reproducing the
snapshot. The summary file needs no key, comes from the same allowlisted host
as TIGER and CenPop, and is verifiable against the provider. The API remains
usable through :func:`phillysim.download.fetch_file`'s ``query_secret`` hook
if a later packet needs it.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from phillysim.adapters.base import (
    CENSUS_TERMS_FILE,
    CENSUS_TERMS_PHRASE,
    CENSUS_TERMS_URL,
    COUNTY_GEOID,
    PUBLIC_DOMAIN,
    TRACT_GEOID_PATTERN,
    Adapter,
)
from phillysim.contracts import ColumnSpec, SourceContract
from phillysim.download import Fetch, SnapshotSpec
from phillysim.guards import Limits

SOURCE = "acs"
VINTAGE = "ACS 5-year 2020-2024"
RELEASE_YEAR = 2024
DIRECTORY_URL = (
    "https://www2.census.gov/programs-surveys/acs/summary_file/2024/table-based-SF/data/5YRData/"
)
ALLOWLIST: tuple[str, ...] = ("www2.census.gov", "www.census.gov")
#: B01003 is about 18 MB and B08201 about 65 MB (every geography in the nation);
#: the cap leaves room for the largest tables. No archives.
LIMITS = Limits(
    max_file_bytes=256 * 1024**2,
    max_extracted_bytes=256 * 1024**2,
    max_compression_ratio=50.0,
    max_members=1,
)

#: The pinned variables: ``(table, line)`` -> data-dictionary column stem.
VARIABLES: tuple[tuple[str, str], ...] = (("B01003", "001"), ("B08201", "002"))
TABLES: tuple[str, ...] = tuple(dict.fromkeys(table for table, _ in VARIABLES))
#: Tract rows in the summary file: summary level 140, then ``US`` + state + county + tract.
TRACT_GEO_PREFIX = f"1400000US{COUNTY_GEOID}"
#: Annotation ("jam") values the ACS uses in place of a number; every one becomes null.
JAM_VALUES: frozenset[int] = frozenset(
    {-999999999, -888888888, -666666666, -555555555, -333333333, -222222222}
)


def file_name(table: str) -> str:
    return f"acsdt5y{RELEASE_YEAR}-{table.lower()}.dat"


def column_names() -> tuple[str, ...]:
    """The estimate / MOE columns :func:`read` returns, in the data dictionary's form."""
    return tuple(f"{table}_{line}{kind}" for table, line in VARIABLES for kind in ("E", "M"))


SPEC = SnapshotSpec(
    source=SOURCE,
    acquisition_url=DIRECTORY_URL,
    files=tuple(Fetch(DIRECTORY_URL + file_name(table), file_name(table)) for table in TABLES),
    terms=Fetch(CENSUS_TERMS_URL, CENSUS_TERMS_FILE),
    terms_must_contain=(CENSUS_TERMS_PHRASE,),
    allowlist=ALLOWLIST,
    limits=LIMITS,
    license_bucket="A",
    license_note=(
        f"{PUBLIC_DOMAIN}. {VINTAGE} table-based summary file, tables "
        f"{', '.join(TABLES)}; estimates carry 90 percent margins of error."
    ),
)

CONTRACT = SourceContract(
    name=SOURCE,
    columns=(
        ColumnSpec("geoid", "str", nullable=False, pattern=TRACT_GEOID_PATTERN),
        # Provider-suppressed or annotated cells are null by rule (ADR-0004), so the
        # value columns are nullable; the real-run handoff reports how many.
        *(ColumnSpec(name, "float", minimum=0) for name in column_names()),
    ),
    key="geoid",
    license_buckets=frozenset({"A"}),
)


def _read_table(snapshot_dir: Path, table: str) -> pd.DataFrame:
    lines = [line for t, line in VARIABLES if t == table]
    wanted = ["GEO_ID"] + [f"{table}_{kind}{line}" for line in lines for kind in ("E", "M")]
    raw = pd.read_csv(snapshot_dir / file_name(table), sep="|", dtype="string", usecols=wanted)
    rows = raw[raw["GEO_ID"].str.startswith(TRACT_GEO_PREFIX, na=False)].reset_index(drop=True)
    out = pd.DataFrame({"geoid": rows["GEO_ID"].str[-11:].astype("string")})
    for line in lines:
        for kind in ("E", "M"):
            values = pd.to_numeric(rows[f"{table}_{kind}{line}"], errors="coerce")
            values = values.mask(values.isin(JAM_VALUES))
            out[f"{table}_{line}{kind}"] = values.astype("float64")
    return out


def read(snapshot_dir: Path) -> pd.DataFrame:
    """One row per Philadelphia County tract with the pinned estimates and MOEs."""
    frames = [_read_table(snapshot_dir, table) for table in TABLES]
    frame = frames[0]
    for other in frames[1:]:
        frame = frame.merge(other, on="geoid", how="outer", validate="one_to_one")
    return frame.sort_values("geoid").reset_index(drop=True)


ADAPTER = Adapter(
    spec=SPEC,
    contract=CONTRACT,
    read=read,
    filter_note=(
        "stored as delivered (nationwide table files from the summary file, verifiable "
        "against the provider, no API key); county filter on the GEO_ID prefix, the pinned "
        "variable selection, and annotation-value nulling applied at first read"
    ),
    citation=(
        "U.S. Census Bureau, American Community Survey 5-Year Estimates 2020-2024, "
        "tables B01003 and B08201."
    ),
)
