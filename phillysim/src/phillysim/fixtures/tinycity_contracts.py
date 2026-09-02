"""Source contracts for the tinycity fake sources (the EP-3 contract-harness proof).

Each entry describes what :func:`phillysim.fixtures.tinycity.load_raw` must hand
back for one raw source, using the same :class:`~phillysim.contracts.SourceContract`
type real adapters will declare from EP-5 on. Bounds are the fixture's own grid;
the real adapters will pin Philadelphia County instead.
"""

from __future__ import annotations

from phillysim.contracts import ColumnSpec, GeometrySpec, SourceContract
from phillysim.fixtures.tinycity import BOUNDS, CRS, DAYS

GEOID_PATTERN = r"\d{11}"
_HHMM = r"([01]\d|2[0-3]):[0-5]\d"

_POINT = GeometrySpec(types=frozenset({"Point"}), crs=CRS, bounds=BOUNDS)
_POLYGON = GeometrySpec(types=frozenset({"Polygon", "MultiPolygon"}), crs=CRS, bounds=BOUNDS)
_LINE = GeometrySpec(types=frozenset({"LineString"}), crs=CRS, bounds=BOUNDS)

_geoid = ColumnSpec("geoid", "str", nullable=False, pattern=GEOID_PATTERN)

CONTRACTS: dict[str, SourceContract] = {
    "tiger_tracts": SourceContract(
        name="tiger_tracts",
        columns=(_geoid, ColumnSpec("name", "str"), ColumnSpec("population", "int", minimum=0)),
        key="geoid",
        geometry=_POLYGON,
        license_buckets=frozenset({"A"}),
        min_rows=6,
        max_rows=6,
    ),
    "cenpop": SourceContract(
        name="cenpop",
        columns=(
            _geoid,
            ColumnSpec("population", "int", nullable=False, minimum=0),
            ColumnSpec("longitude", "float", nullable=False),
            ColumnSpec("latitude", "float", nullable=False),
        ),
        key="geoid",
        geometry=_POINT,
        license_buckets=frozenset({"A"}),
        min_rows=6,
        max_rows=6,
    ),
    "acs": SourceContract(
        name="acs",
        columns=(
            _geoid,
            ColumnSpec("B01003_001E", "float", nullable=False, minimum=0),
            ColumnSpec("B01003_001M", "float", nullable=False, minimum=0),
            ColumnSpec("B08201_002E", "float", minimum=0),  # provider-suppressed cells stay null
            ColumnSpec("B08201_002M", "float", minimum=0),
        ),
        key="geoid",
        license_buckets=frozenset({"A"}),
        min_rows=6,
        max_rows=6,
    ),
    "snap_retailers": SourceContract(
        name="snap_retailers",
        columns=(
            ColumnSpec("record_id", "str", nullable=False),
            ColumnSpec("store_name", "str", nullable=False),
            ColumnSpec("store_type", "str", nullable=False),
            ColumnSpec("longitude", "float", nullable=False),
            ColumnSpec("latitude", "float", nullable=False),
        ),
        key="record_id",
        geometry=_POINT,
        license_buckets=frozenset({"A"}),
    ),
    "farmers_markets": SourceContract(
        name="farmers_markets",
        columns=(
            ColumnSpec("market_id", "str", nullable=False),
            ColumnSpec("name", "str", nullable=False),
            ColumnSpec("hours", "str"),  # free text; missing and malformed are data, not errors
            ColumnSpec("months", "str"),
        ),
        key="market_id",
        geometry=_POINT,
        license_buckets=frozenset({"A"}),
    ),
    "meal_sites": SourceContract(
        name="meal_sites",
        columns=(
            ColumnSpec("site_id", "str", nullable=False),
            ColumnSpec("name", "str", nullable=False),
            # Structured hours are strings the parser validates; the contract only
            # requires the columns to exist, so "25:00" is a parser case, not a
            # contract failure.
            *(ColumnSpec(f"{day}_{edge}", "str") for day in DAYS for edge in ("open", "close")),
        ),
        key="site_id",
        geometry=_POINT,
        license_buckets=frozenset({"A"}),
    ),
    "gtfs": SourceContract(
        name="gtfs",
        columns=(
            ColumnSpec("stop_id", "str", nullable=False),
            ColumnSpec("stop_name", "str", nullable=False),
            ColumnSpec("stop_lat", "float", nullable=False),
            ColumnSpec("stop_lon", "float", nullable=False),
        ),
        key="stop_id",
        geometry=_POINT,
        license_buckets=frozenset({"A"}),
    ),
    "osm_network": SourceContract(
        name="osm_network",
        columns=(
            ColumnSpec("edge_id", "str", nullable=False),
            ColumnSpec("u", "str", nullable=False),
            ColumnSpec("v", "str", nullable=False),
            ColumnSpec("highway", "str", nullable=False),
            ColumnSpec("length_m", "float", nullable=False, minimum=0),
        ),
        key="edge_id",
        geometry=_LINE,
        license_buckets=frozenset({"B"}),  # OSM-derived content ships ODbL (ADR-0003)
    ),
}

#: Structured meal-site hours, once parsed, must look like this (used by the
#: hours-parser known-answer tests from M4 on; recorded here so the pattern is
#: pinned beside the fixture that exercises it).
HOURS_PATTERN = _HHMM
