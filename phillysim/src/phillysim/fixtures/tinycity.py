"""tinycity: a deterministic synthetic mini-geography for offline pipeline tests (EP-3).

Six fake census tracts on a 3 x 2 grid in the open Atlantic (nowhere near
Philadelphia, on purpose), fake destination points in all three v1 categories,
a fake ACS table with margins of error, a tiny GTFS feed and street network, a
precomputed travel-time matrix standing in for the M3 routing stage, and golden
"expected" tables for the stages that run on top. Every value is chosen by hand
or computed from those hand-chosen values with plain arithmetic; there is no
randomness and nothing is derived from real data.

Determinism is the point: :func:`write_fixture` produces byte-identical text
files on every run (stable ordering, fixed rounding, sorted JSON keys, LF line
ends) and content-identical Parquet files. ``tests/fixtures/tinycity/README.md``
documents the layout; ``docs/data-dictionary.md`` documents every column.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString, Point, Polygon, mapping

from phillysim.manifest import SCHEMA_VERSION, Manifest, canonical_bytes

FIXTURE_NAME = "tinycity"
METHODS_VERSION = "tinycity-fixture-1"
SNAPSHOT_ID = "2026-01-01"
ACQUIRED_AT = "2026-01-01T00:00:00Z"
CRS = "EPSG:4326"

# Geography: 3 columns x 2 rows of 0.01-degree cells, south-west corner at
# (-70.00, 38.00). The bottom row (tracts 1-3) is the "transit row".
LON0, LAT0, CELL = -70.00, 38.00, 0.01
COLS, ROWS = 3, 2
BOUNDS: tuple[float, float, float, float] = (LON0, LAT0, LON0 + COLS * CELL, LAT0 + ROWS * CELL)
STATE_FIPS, COUNTY_FIPS = "99", "999"  # neither exists; the GEOIDs are unmistakably fake

# Travel model stand-ins (methodology.md "Travel model"; the fixture only needs
# a deterministic, monotone stand-in until the M3 spike provides real times).
WALK_M_PER_MIN = 80.0  # 4.8 km/h
WALK_ACCESS_MIN = 1.0
WALK_P85_FACTOR = 1.15
TRANSIT_FACTOR = 0.6
TRANSIT_WAIT_MIN = 5.0
TRANSIT_P85_FACTOR = 1.25
CENSOR_MIN = 120.0
M_PER_DEG_LAT = 110_574.0
M_PER_DEG_LON_EQUATOR = 111_320.0

# Pinned analysis weeks (methodology.md "Two-tier labeling"): the first full
# Monday-to-Sunday week of June (in-season) and of February (off-season).
IN_SEASON_WEEK_START = "2026-06-01"
OFF_SEASON_WEEK_START = "2026-02-02"

# ACS 90% margin of error -> standard error, and the CV reliability tiers.
MOE_TO_SE = 1.645
CV_TIER_EDGES_PCT = (12.0, 40.0)

CATEGORIES: tuple[str, ...] = ("supermarket_format", "farmers_market", "meal_site")
MODES: tuple[str, ...] = ("walk", "walk_transit")
HOURS_STATUSES: frozenset[str] = frozenset({"parsed", "missing", "malformed", "not_in_source"})
DAYS: tuple[str, ...] = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


class Variant(StrEnum):
    """``valid`` is the golden fixture; ``invalid`` injects faults for negative tests."""

    VALID = "valid"
    INVALID = "invalid"


# --- hand-chosen inputs -----------------------------------------------------------

# Per tract (1..6): population, ACS total-population MOE, households-without-
# vehicle estimate and MOE (None = provider-suppressed, stays missing per
# ADR-0004). The MOEs are chosen so the CV tiers 1, 2, and 3 all occur.
POPULATION: tuple[int, ...] = (3200, 4100, 2750, 5100, 1900, 3600)
POPULATION_MOE: tuple[int, ...] = (210, 900, 2100, 300, 150, 260)
NO_VEHICLE_EST: tuple[int | None, ...] = (640, 1210, 400, 1500, None, 720)
NO_VEHICLE_MOE: tuple[int | None, ...] = (95, 340, 260, 210, None, 160)


@dataclass(frozen=True)
class SiteSpec:
    """One destination point plus its hand-derived Tier 2 answers.

    ``open_*`` fields are the answers an hours parser must reproduce; ``None``
    means "cannot be determined" (hours missing, malformed, or not in source).
    """

    site_id: str
    source: str
    category: str
    name: str
    tract: int
    fx: float
    fy: float
    hours_status: str
    open_weekday: bool | None
    open_weekend: bool | None
    open_in_season_week: bool | None
    open_off_season_week: bool | None
    attrs: dict[str, Any]


def _closed_week() -> dict[str, str | None]:
    return {f"{day}_{edge}": None for day in DAYS for edge in ("open", "close")}


def _week(open_days: tuple[str, ...], opens: str, closes: str) -> dict[str, str | None]:
    hours = _closed_week()
    for day in open_days:
        hours[f"{day}_open"] = opens
        hours[f"{day}_close"] = closes
    return hours


# fmt: off
SITES: tuple[SiteSpec, ...] = (
    # SNAP-like retailers: format-based store types only; the source has no hours.
    SiteSpec("R1", "snap_retailers", "supermarket_format", "Tinycity Supermarket", 1, 0.5, 0.5,
             "not_in_source", None, None, None, None,
             {"store_type": "Supermarket"}),
    SiteSpec("R2", "snap_retailers", "supermarket_format", "Corner Market", 5, 0.3, 0.7,
             "not_in_source", None, None, None, None,
             {"store_type": "Convenience Store"}),
    SiteSpec("R3", "snap_retailers", "supermarket_format", "Grid Grocery", 3, 0.6, 0.4,
             "not_in_source", None, None, None, None,
             {"store_type": "Large Grocery Store"}),
    SiteSpec("R4", "snap_retailers", "supermarket_format", "Harbor Superstore", 6, 0.8, 0.2,
             "not_in_source", None, None, None, None,
             {"store_type": "Super Store"}),
    # Farmers' markets: free-text hours, the four Tier 2 edge cases plus one plain case.
    SiteSpec("M1", "farmers_markets", "farmers_market", "Weekend Green Market", 2, 0.5, 0.6,
             "parsed", False, True, True, True,
             {"hours": "Saturday 9:00 AM - 1:00 PM", "months": "Year-round"}),
    SiteSpec("M2", "farmers_markets", "farmers_market", "Seasonal Square Market", 4, 0.4, 0.3,
             "parsed", True, False, True, False,
             {"hours": "Tuesdays 2:00 PM - 6:00 PM", "months": "May - November"}),
    SiteSpec("M3", "farmers_markets", "farmers_market", "Quiet Corner Market", 6, 0.2, 0.8,
             "missing", None, None, None, None,
             {"hours": None, "months": None}),
    SiteSpec("M4", "farmers_markets", "farmers_market", "Riverside Stand", 1, 0.9, 0.9,
             "malformed", None, None, None, None,
             {"hours": "9-1 sat&sun / call ahead ###", "months": "??"}),
    SiteSpec("M5", "farmers_markets", "farmers_market", "Midweek Market", 5, 0.6, 0.5,
             "parsed", True, False, True, True,
             {"hours": "Wednesday 10:00 AM - 2:00 PM", "months": "Year-round"}),
    # Meal sites: structured per-day hours ("HH:MM" or null).
    SiteSpec("S1", "meal_sites", "meal_site", "Central Kitchen", 3, 0.2, 0.2,
             "parsed", True, False, True, True,
             _week(("mon", "tue", "wed", "thu", "fri"), "11:30", "13:00")),
    SiteSpec("S2", "meal_sites", "meal_site", "Weekend Breakfast", 2, 0.7, 0.3,
             "parsed", False, True, True, True,
             _week(("sat", "sun"), "08:00", "10:00")),
    SiteSpec("S3", "meal_sites", "meal_site", "Unlisted Pantry", 4, 0.8, 0.7,
             "missing", None, None, None, None,
             _closed_week()),
    SiteSpec("S4", "meal_sites", "meal_site", "Typo Table", 1, 0.1, 0.6,
             "malformed", None, None, None, None,
             {**_closed_week(), "mon_open": "25:00", "mon_close": "13:00"}),
)
# fmt: on


# --- derived geography -------------------------------------------------------------


@dataclass(frozen=True)
class Tract:
    n: int
    geoid: str
    col: int
    row: int
    population: int
    polygon: Polygon
    center: tuple[float, float]  # geometric centre
    centroid: tuple[float, float]  # population-weighted (CenPop-like), deliberately off-centre


def _round6(value: float) -> float:
    return round(value, 6)


def tracts() -> list[Tract]:
    out: list[Tract] = []
    for row in range(ROWS):
        for col in range(COLS):
            n = row * COLS + col + 1
            x0, y0 = _round6(LON0 + col * CELL), _round6(LAT0 + row * CELL)
            x1, y1 = _round6(x0 + CELL), _round6(y0 + CELL)
            # Corners rounded like every other coordinate, so the polygon read back from
            # the GeoJSON snapshot equals the golden spine geometry exactly (EP-4b).
            polygon = Polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)])
            center = (_round6(x0 + CELL / 2), _round6(y0 + CELL / 2))
            dx = 0.002 if n % 2 else -0.002
            dy = -0.0015 if n % 3 else 0.0015
            centroid = (_round6(center[0] + dx), _round6(center[1] + dy))
            geoid = f"{STATE_FIPS}{COUNTY_FIPS}{n:04d}00"
            out.append(Tract(n, geoid, col, row, POPULATION[n - 1], polygon, center, centroid))
    return out


def site_point(spec: SiteSpec, by_n: dict[int, Tract]) -> tuple[float, float]:
    tract = by_n[spec.tract]
    x0, y0 = LON0 + tract.col * CELL, LAT0 + tract.row * CELL
    return _round6(x0 + spec.fx * CELL), _round6(y0 + spec.fy * CELL)


def manhattan_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat_mean = math.radians((a[1] + b[1]) / 2)
    dx = abs(a[0] - b[0]) * M_PER_DEG_LON_EQUATOR * math.cos(lat_mean)
    dy = abs(a[1] - b[1]) * M_PER_DEG_LAT
    return dx + dy


def _censor(minutes: float) -> float:
    return min(round(minutes, 1), CENSOR_MIN)


def travel_times(origin: Tract, destination: Tract, distance_m: float) -> dict[str, float]:
    walk = _censor(distance_m / WALK_M_PER_MIN + WALK_ACCESS_MIN)
    on_transit_row = origin.row == 0 and destination.row == 0 and origin.n != destination.n
    # Walk+transit is never slower than walking: the traveler takes the faster option.
    transit = (
        min(walk, _censor(TRANSIT_FACTOR * walk + TRANSIT_WAIT_MIN)) if on_transit_row else walk
    )
    return {
        "walk": walk,
        "walk_p85": _censor(walk * WALK_P85_FACTOR),
        "walk_transit": transit,
        "walk_transit_p85": _censor(transit * TRANSIT_P85_FACTOR),
    }


def cv_tier(estimate: float | None, moe: float | None) -> int | None:
    """CV reliability tier from a 90% MOE: 1 below 12%, 2 below 40%, 3 above (None if unknown)."""
    if estimate is None or moe is None or estimate == 0:
        return None
    cv_pct = (moe / MOE_TO_SE) / abs(estimate) * 100.0
    if cv_pct < CV_TIER_EDGES_PCT[0]:
        return 1
    if cv_pct < CV_TIER_EDGES_PCT[1]:
        return 2
    return 3


def reliability_action(tier: int | None) -> str:
    return "interval-only" if tier == 3 else "none"


# --- the model --------------------------------------------------------------------


@dataclass
class Model:
    """Everything the fixture writes, as plain records, before any serialization."""

    variant: Variant
    tracts: list[dict[str, Any]]
    centroids: list[dict[str, Any]]
    acs: list[dict[str, Any]]
    retailers: list[dict[str, Any]]
    markets: list[dict[str, Any]]
    meal_sites: list[dict[str, Any]]
    gtfs: dict[str, list[dict[str, Any]]]
    edges: list[dict[str, Any]]
    manifests: dict[str, dict[str, Any]]
    travel_times: list[dict[str, Any]]
    sites: list[dict[str, Any]]
    metrics: list[dict[str, Any]]
    faults: list[dict[str, str]]


def _base_manifest(source: str, license_bucket: str, note: str) -> dict[str, Any]:
    """The manifest engine's own shape (EP-4a); ``files`` is filled with digests at write time."""
    return Manifest(
        source=source,
        snapshot_id=SNAPSHOT_ID,
        acquired_at=ACQUIRED_AT,
        acquisition_url=f"https://example.invalid/{FIXTURE_NAME}/{source}",
        acquisition_url_alt=None,
        terms_archive="TERMS.txt",
        license_bucket=license_bucket,
        license_note=note,
        schema_version=SCHEMA_VERSION,
        synthetic=True,
    ).to_dict()


SYNTHETIC_NOTE = "wholly synthetic fixture; no real data; MIT (repository license)"


def build_model(variant: Variant = Variant.VALID) -> Model:
    grid = tracts()
    by_n = {tract.n: tract for tract in grid}
    tract_records = [
        {
            "geoid": t.geoid,
            "name": f"Tract {t.n}",
            "population": t.population,
            "geometry": t.polygon,
        }
        for t in grid
    ]
    centroids = [
        {
            "geoid": t.geoid,
            "population": t.population,
            "longitude": t.centroid[0],
            "latitude": t.centroid[1],
        }
        for t in grid
    ]
    acs = [
        {
            "geoid": t.geoid,
            "B01003_001E": t.population,
            "B01003_001M": POPULATION_MOE[t.n - 1],
            "B08201_002E": NO_VEHICLE_EST[t.n - 1],
            "B08201_002M": NO_VEHICLE_MOE[t.n - 1],
        }
        for t in grid
    ]

    points = {spec.site_id: site_point(spec, by_n) for spec in SITES}
    retailers = [
        {
            "record_id": s.site_id,
            "store_name": s.name,
            "store_type": s.attrs["store_type"],
            "street_address": f"{s.tract}00 Grid St",
            "city": "Tinycity",
            "state": "ZZ",
            "zip": "00000",
            "longitude": points[s.site_id][0],
            "latitude": points[s.site_id][1],
        }
        for s in SITES
        if s.source == "snap_retailers"
    ]
    markets = [
        {
            "market_id": s.site_id,
            "name": s.name,
            "hours": s.attrs["hours"],
            "months": s.attrs["months"],
            "geometry": Point(points[s.site_id]),
        }
        for s in SITES
        if s.source == "farmers_markets"
    ]
    meal_sites = [
        {
            "site_id": s.site_id,
            "name": s.name,
            **{key: s.attrs[key] for key in sorted(s.attrs)},
            "geometry": Point(points[s.site_id]),
        }
        for s in SITES
        if s.source == "meal_sites"
    ]

    transit_row = [t for t in grid if t.row == 0]
    gtfs = {
        "agency.txt": [
            {
                "agency_id": "TC",
                "agency_name": "Tinycity Transit",
                "agency_url": "https://example.invalid/tinycity/transit",
                "agency_timezone": "America/New_York",
            }
        ],
        "stops.txt": [
            {
                "stop_id": f"STOP{t.n}",
                "stop_name": f"Tract {t.n} Center",
                "stop_lat": _round6(t.center[1] - 0.001),
                "stop_lon": t.center[0],
            }
            for t in transit_row
        ],
        "routes.txt": [
            {
                "route_id": "T1",
                "agency_id": "TC",
                "route_short_name": "1",
                "route_long_name": "Bottom Row Line",
                "route_type": 3,
            }
        ],
        "calendar.txt": [
            {
                "service_id": "WK",
                "monday": 1,
                "tuesday": 1,
                "wednesday": 1,
                "thursday": 1,
                "friday": 1,
                "saturday": 0,
                "sunday": 0,
                "start_date": "20260101",
                "end_date": "20261231",
            }
        ],
        "trips.txt": [{"route_id": "T1", "service_id": "WK", "trip_id": "T1_0800"}],
        "stop_times.txt": [
            {
                "trip_id": "T1_0800",
                "arrival_time": f"08:{6 * i:02d}:00",
                "departure_time": f"08:{6 * i:02d}:00",
                "stop_id": f"STOP{t.n}",
                "stop_sequence": i + 1,
            }
            for i, t in enumerate(transit_row)
        ],
    }

    edges: list[dict[str, Any]] = []
    pairs = [(1, 2), (2, 3), (4, 5), (5, 6), (1, 4), (2, 5), (3, 6)]
    for i, (u, v) in enumerate(pairs, start=1):
        a, b = by_n[u].center, by_n[v].center
        edges.append(
            {
                "edge_id": f"E{i}",
                "u": f"N{u}",
                "v": f"N{v}",
                "highway": "residential",
                "length_m": round(manhattan_m(a, b), 1),
                "geometry": LineString([a, b]),
            }
        )

    manifests = {
        "tiger_tracts": _base_manifest("tiger_tracts", "A", SYNTHETIC_NOTE),
        "cenpop": _base_manifest("cenpop", "A", SYNTHETIC_NOTE),
        "acs": _base_manifest("acs", "A", SYNTHETIC_NOTE),
        "snap_retailers": _base_manifest("snap_retailers", "A", SYNTHETIC_NOTE),
        "farmers_markets": _base_manifest("farmers_markets", "A", SYNTHETIC_NOTE),
        "meal_sites": _base_manifest("meal_sites", "A", SYNTHETIC_NOTE),
        "gtfs": _base_manifest("gtfs", "A", SYNTHETIC_NOTE + "; raw feed never republished"),
        "osm_network": _base_manifest(
            "osm_network", "B", SYNTHETIC_NOTE + "; stands in for ODbL-derived content"
        ),
    }

    # Expected outputs: conflated sites, travel-time matrix, analytic table.
    sites = [
        {
            "site_id": f"{s.source}:{s.site_id}",
            "source": s.source,
            "source_record_id": s.site_id,
            "category": s.category,
            "name": s.name,
            "geoid": by_n[s.tract].geoid,
            "longitude": points[s.site_id][0],
            "latitude": points[s.site_id][1],
            "hours_status": s.hours_status,
            "open_weekday": s.open_weekday,
            "open_weekend": s.open_weekend,
            "open_in_season_week": s.open_in_season_week,
            "open_off_season_week": s.open_off_season_week,
        }
        for s in SITES
    ]
    matrix: list[dict[str, Any]] = []
    nearest: dict[tuple[str, str, str], float] = {}
    for origin in grid:
        for s in SITES:
            times = travel_times(
                origin, by_n[s.tract], manhattan_m(origin.centroid, points[s.site_id])
            )
            site_id = f"{s.source}:{s.site_id}"
            for mode in MODES:
                matrix.append(
                    {
                        "origin_geoid": origin.geoid,
                        "site_id": site_id,
                        "mode": mode,
                        "time_median_min": times[mode],
                        "time_p85_min": times[f"{mode}_p85"],
                    }
                )
                key = (origin.geoid, s.category, mode)
                nearest[key] = min(nearest.get(key, CENSOR_MIN), times[mode])
    metrics: list[dict[str, Any]] = []
    for t in grid:
        moe = float(POPULATION_MOE[t.n - 1])
        tier = cv_tier(float(t.population), moe)
        metrics.append(
            {
                "geoid": t.geoid,
                "metric_id": "population_total",
                "category": None,
                "mode": None,
                "estimate": float(t.population),
                "moe": moe,
                "cv_tier": tier,
                "reliability_action": reliability_action(tier),
            }
        )
        for category in CATEGORIES:
            for mode in MODES:
                metrics.append(
                    {
                        "geoid": t.geoid,
                        "metric_id": "time_to_nearest_min",
                        "category": category,
                        "mode": mode,
                        "estimate": nearest[(t.geoid, category, mode)],
                        "moe": None,
                        "cv_tier": None,
                        "reliability_action": "none",
                    }
                )
    for record in metrics:
        record["schema_version"] = SCHEMA_VERSION
        record["methods_version"] = METHODS_VERSION

    model = Model(
        variant=variant,
        tracts=tract_records,
        centroids=centroids,
        acs=acs,
        retailers=retailers,
        markets=markets,
        meal_sites=meal_sites,
        gtfs=gtfs,
        edges=edges,
        manifests=manifests,
        travel_times=matrix,
        sites=sites,
        metrics=metrics,
        faults=[],
    )
    if variant is Variant.INVALID:
        _inject_faults(model)
    return model


# --- the invalid variant ---------------------------------------------------------


def _inject_faults(model: Model) -> None:
    """Break the raw sources in ways the contract harness must catch (one per check kind)."""
    # fmt: off
    faults = model.faults
    bowtie = Polygon([(-69.98, 38.00), (-69.97, 38.01), (-69.97, 38.00), (-69.98, 38.01)])
    model.tracts[2]["geometry"] = bowtie
    faults.append({"id": "tract_invalid_geometry", "source": "tiger_tracts", "check": "geometry",
                   "detail": "tract 000300 polygon replaced by a self-intersecting bowtie"})
    model.tracts[5]["geoid"] = model.tracts[5]["geoid"][:-1]
    faults.append({"id": "tract_geoid_length", "source": "tiger_tracts", "check": "schema",
                   "detail": "tract 000600 GEOID truncated to 10 characters"})
    for record in model.retailers:
        del record["store_type"]
    faults.append({"id": "retailers_missing_column", "source": "snap_retailers", "check": "schema",
                   "detail": "store_type column dropped"})
    model.retailers[1]["latitude"] = 38.9
    faults.append({"id": "retailer_out_of_bounds", "source": "snap_retailers", "check": "geometry",
                   "detail": "R2 moved outside the fixture bounds"})
    model.manifests["snap_retailers"]["license_bucket"] = "Z"
    faults.append({"id": "retailers_license_bucket", "source": "snap_retailers", "check": "license",
                   "detail": "manifest license_bucket set to 'Z'"})
    model.markets.append(dict(model.markets[0]))
    faults.append({"id": "market_duplicate_key", "source": "farmers_markets", "check": "key",
                   "detail": "M1 appears twice"})
    model.acs[1]["B01003_001M"] = -900
    faults.append({"id": "acs_negative_moe", "source": "acs", "check": "schema",
                   "detail": "tract 000200 total-population MOE set negative"})
    model.meal_sites.clear()
    faults.append({"id": "meal_sites_empty", "source": "meal_sites", "check": "rows",
                   "detail": "meal-site layer emptied"})
    # fmt: on


# --- serialization ----------------------------------------------------------------


def _csv_bytes(records: list[dict[str, Any]], columns: list[str]) -> bytes:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    for record in records:
        writer.writerow({key: ("" if record.get(key) is None else record[key]) for key in columns})
    return buffer.getvalue().encode("utf-8")


_json_bytes = canonical_bytes  # manifests and every other JSON file share one canonical form


def _round_coords(value: Any) -> Any:
    if isinstance(value, (list, tuple)):
        return [_round_coords(item) for item in value]
    if isinstance(value, float):
        return _round6(value)
    return value


def _geojson_bytes(records: list[dict[str, Any]], id_key: str) -> bytes:
    features = []
    for record in records:
        properties = {key: value for key, value in record.items() if key != "geometry"}
        geometry = mapping(record["geometry"])
        geometry = {"type": geometry["type"], "coordinates": _round_coords(geometry["coordinates"])}
        features.append(
            {
                "type": "Feature",
                "id": record[id_key],
                "properties": properties,
                "geometry": geometry,
            }
        )
    return _json_bytes({"type": "FeatureCollection", "features": features})


def _parquet_bytes(frame: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    frame.to_parquet(buffer, index=False, engine="pyarrow")
    return buffer.getvalue()


def _sites_frame(records: list[dict[str, Any]]) -> pd.DataFrame:
    frame = pd.DataFrame.from_records(records)
    for column in ("open_weekday", "open_weekend", "open_in_season_week", "open_off_season_week"):
        frame[column] = frame[column].astype("boolean")
    return frame


def _metrics_frame(records: list[dict[str, Any]]) -> pd.DataFrame:
    frame = pd.DataFrame.from_records(records)
    frame["estimate"] = frame["estimate"].astype("float64")
    frame["moe"] = frame["moe"].astype("float64")
    frame["cv_tier"] = frame["cv_tier"].astype("Int64")
    frame["schema_version"] = frame["schema_version"].astype("int64")
    return frame


def _spine_frame(model: Model) -> gpd.GeoDataFrame:
    by_geoid = {record["geoid"]: record for record in model.centroids}
    records = [
        {
            "geoid": record["geoid"],
            "name": record["name"],
            "population": record["population"],
            "centroid_lon": by_geoid[record["geoid"]]["longitude"],
            "centroid_lat": by_geoid[record["geoid"]]["latitude"],
            "geometry": record["geometry"],
        }
        for record in model.tracts
    ]
    return gpd.GeoDataFrame(records, geometry="geometry", crs=CRS)


def render(model: Model) -> dict[str, bytes]:
    """Serialize the model to ``{relative path: bytes}`` with manifests' file digests filled in."""
    raw = "raw"
    files: dict[str, bytes] = {}
    per_source: dict[str, dict[str, bytes]] = {
        "tiger_tracts": {"tracts.geojson": _geojson_bytes(model.tracts, "geoid")},
        "cenpop": {
            "centroids.csv": _csv_bytes(
                model.centroids, ["geoid", "population", "longitude", "latitude"]
            )
        },
        "acs": {
            "acs.csv": _csv_bytes(
                model.acs, ["geoid", "B01003_001E", "B01003_001M", "B08201_002E", "B08201_002M"]
            )
        },
        "snap_retailers": {
            "retailers.csv": _csv_bytes(
                model.retailers,
                [column for column in RETAILER_COLUMNS if column in model.retailers[0]],
            )
        },
        "farmers_markets": {"markets.geojson": _geojson_bytes(model.markets, "market_id")},
        "meal_sites": {"meal_sites.geojson": _geojson_bytes(model.meal_sites, "site_id")},
        "gtfs": {
            name: _csv_bytes(records, list(records[0])) for name, records in model.gtfs.items()
        },
        "osm_network": {"edges.geojson": _geojson_bytes(model.edges, "edge_id")},
    }
    for source, contents in per_source.items():
        manifest = dict(model.manifests[source])
        terms = f"{FIXTURE_NAME} synthetic source {source!r}: {SYNTHETIC_NOTE}.\n".encode()
        contents = {**contents, "TERMS.txt": terms}
        manifest["files"] = {
            name: hashlib.sha256(data).hexdigest() for name, data in sorted(contents.items())
        }
        base = f"{raw}/{source}/{SNAPSHOT_ID}"
        for name, data in contents.items():
            files[f"{base}/{name}"] = data
        files[f"{base}/manifest.json"] = _json_bytes(manifest)

    parameters = {
        "fixture": FIXTURE_NAME,
        "variant": model.variant.value,
        "schema_version": SCHEMA_VERSION,
        "methods_version": METHODS_VERSION,
        "crs": CRS,
        "bounds": list(BOUNDS),
        "grid": {"cols": COLS, "rows": ROWS, "cell_deg": CELL},
        "categories": list(CATEGORIES),
        "modes": list(MODES),
        "analysis_weeks": {
            "in_season_start": IN_SEASON_WEEK_START,
            "off_season_start": OFF_SEASON_WEEK_START,
        },
        "travel_model": {
            "walk_m_per_min": WALK_M_PER_MIN,
            "walk_access_min": WALK_ACCESS_MIN,
            "walk_p85_factor": WALK_P85_FACTOR,
            "transit_factor": TRANSIT_FACTOR,
            "transit_wait_min": TRANSIT_WAIT_MIN,
            "transit_p85_factor": TRANSIT_P85_FACTOR,
            "censor_min": CENSOR_MIN,
        },
        "cv_tier_edges_pct": list(CV_TIER_EDGES_PCT),
        "moe_to_se": MOE_TO_SE,
        "injected_faults": model.faults,
    }
    files["fixture.json"] = _json_bytes(parameters)

    if model.variant is Variant.VALID:
        files["expected/tracts_spine.parquet"] = _parquet_bytes(_spine_frame(model))
        files["expected/sites.parquet"] = _parquet_bytes(_sites_frame(model.sites))
        files["expected/travel_times.parquet"] = _parquet_bytes(
            pd.DataFrame.from_records(model.travel_times)
        )
        files["expected/tract_metrics.parquet"] = _parquet_bytes(_metrics_frame(model.metrics))
    return files


RETAILER_COLUMNS: tuple[str, ...] = (
    "record_id",
    "store_name",
    "store_type",
    "street_address",
    "city",
    "state",
    "zip",
    "longitude",
    "latitude",
)

CHECKSUMS_FILE = "CHECKSUMS.txt"


def checksums_of(files: dict[str, bytes]) -> dict[str, str]:
    return {path: hashlib.sha256(data).hexdigest() for path, data in sorted(files.items())}


def read_checksums(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in text.splitlines():
        if line.strip():
            digest, path = line.split("  ", 1)
            out[path] = digest
    return out


def write_fixture(out_dir: Path, variant: Variant = Variant.VALID) -> dict[str, str]:
    """Write the fixture under ``out_dir`` and return ``{relative path: sha256}``.

    Existing files at the same paths are overwritten; nothing else is touched, and
    the hand-written README in the committed fixture directory is never generated.
    """
    files = render(build_model(variant))
    digests = checksums_of(files)
    for relative, data in files.items():
        target = out_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    listing = "".join(f"{digest}  {path}\n" for path, digest in digests.items())
    (out_dir / CHECKSUMS_FILE).write_bytes(listing.encode("utf-8"))
    return digests


# --- loading the raw zone back (what an adapter would hand to the harness) ---------

#: source -> (data file, loader kind, key column)
RAW_SOURCES: dict[str, tuple[str, str]] = {
    "tiger_tracts": ("tracts.geojson", "geojson"),
    "cenpop": ("centroids.csv", "csv_points"),
    "acs": ("acs.csv", "csv"),
    "snap_retailers": ("retailers.csv", "csv_points"),
    "farmers_markets": ("markets.geojson", "geojson"),
    "meal_sites": ("meal_sites.geojson", "geojson"),
    "gtfs": ("stops.txt", "gtfs_stops"),
    "osm_network": ("edges.geojson", "geojson"),
}

_STRING_COLUMNS = ("geoid", "record_id", "zip", "stop_id")


def load_raw(fixture_dir: Path, source: str) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Load one raw source as a (Geo)DataFrame plus its manifest.

    CSV point sources become GeoDataFrames from their longitude/latitude columns
    (``stop_lon``/``stop_lat`` for GTFS stops); GeoJSON goes through pyogrio.
    """
    filename, kind = RAW_SOURCES[source]
    base = fixture_dir / "raw" / source / SNAPSHOT_ID
    manifest = json.loads((base / "manifest.json").read_text("utf-8"))
    path = base / filename
    if kind == "geojson":
        frame: pd.DataFrame = gpd.read_file(path)
    else:
        table = pd.read_csv(path, dtype=dict.fromkeys(_STRING_COLUMNS, "string"))
        if kind == "csv":
            frame = table
        else:
            lon, lat = (
                ("stop_lon", "stop_lat") if kind == "gtfs_stops" else ("longitude", "latitude")
            )
            frame = gpd.GeoDataFrame(
                table, geometry=gpd.points_from_xy(table[lon], table[lat]), crs=CRS
            )
    return frame, manifest
