"""The fixture pipeline: eleven stages carrying tinycity from raw snapshots to the expected tables.

This is the pipeline ``phillysim run --fixture`` executes, and the M1 proof that
the stage runner works end to end. The stage names and the zones their outputs
land in are the pipeline skeleton architecture.md describes; the stage *logic*
is fixture-scale, and where the real logic belongs to a later packet the stage
is an explicit stub that takes its answers from the fixture generator's oracle
(the same tables committed under ``tests/fixtures/tinycity/expected/``):

1.  ``acquire`` -> ``raw/<source>/2026-01-01/`` (x 8): generates tinycity and
    admits each snapshot through the EP-4a guards.
2.  ``validate`` -> ``intermediate/validation.json``: every raw source checked
    against its EP-3 contract.
3.  ``spine`` -> ``curated/tracts_spine.parquet``: tracts + population-weighted
    centroids (computed).
4.  ``demographics`` -> ``intermediate/acs_tracts.parquet``: ACS estimates + MOE
    on the spine (computed).
5.  ``destinations`` -> ``intermediate/destinations.parquet``: the three point
    sources normalized and assigned to tracts (computed).
6.  ``conflate`` -> ``intermediate/sites_conflated.parquet``: cross-source
    de-duplication; identity on the fixture (M4 stub).
7.  ``hours`` -> ``curated/sites.parquet``: hours parsing; answers from the
    oracle (M4 stub).
8.  ``network`` -> ``intermediate/network.json``: GTFS + street network
    summarized for routing (computed).
9.  ``travel_times`` -> ``curated/travel_times.parquet``: routing; the oracle's
    matrix, censored by parameter (M3 stub).
10. ``metrics`` -> ``curated/tract_metrics.parquet``: population + CV tiers and
    time to nearest (computed).
11. ``publish`` -> ``public/`` (the whole zone, one atomic install): the public
    zone through :mod:`phillysim.publish` (EP-7; the basemap file with the
    boundary only since EP-8b, the fixture having no roads source): the analytic table widened
    onto the tracts with build-time bins, the sites as points, per-file license
    labels derived from the eight fixture manifests (Bucket B, because
    ``osm_network`` is Bucket B), CSV escaping, and the publish gate run on the
    staged zone before it is installed.

Every stage writes through its :class:`~phillysim.stages.StageContext` and calls
``checkpoint()`` between units of work, so cancellation is honoured inside a
stage as well as between stages. Nothing here touches the network.
"""

from __future__ import annotations

import io
import json
import shutil
from typing import Any

import geopandas as gpd
import pandas as pd

from phillysim.contracts import check_frame
from phillysim.fixtures.tinycity import (
    CATEGORIES,
    CELL,
    CENSOR_MIN,
    COLS,
    CRS,
    CV_TIER_EDGES_PCT,
    IN_SEASON_WEEK_START,
    LAT0,
    LON0,
    METHODS_VERSION,
    MODES,
    MOE_TO_SE,
    OFF_SEASON_WEEK_START,
    RAW_SOURCES,
    ROWS,
    SNAPSHOT_ID,
    Variant,
    build_model,
    load_raw,
    render,
    write_fixture,
)
from phillysim.fixtures.tinycity_contracts import CONTRACTS
from phillysim.guards import Limits
from phillysim.manifest import SCHEMA_VERSION
from phillysim.publish import bins, export
from phillysim.quarantine import admit
from phillysim.stages import Pipeline, Stage, StageContext, StageError

PIPELINE_NAME = "fixture"
FIXTURE_ROOT_NAME = "fixture"  # <data root>/fixture/ is the fixture pipeline's own data root

#: The fixture's manifests point at example.invalid; admission checks that host.
ALLOWLIST: tuple[str, ...] = ("example.invalid",)
#: Fixture-scale guard limits (the defaults are sized for a regional OSM extract).
LIMITS = Limits(max_file_bytes=8 * 1024**2, max_extracted_bytes=32 * 1024**2, max_members=100)

SOURCES: tuple[str, ...] = tuple(sorted(RAW_SOURCES))
RAW_SNAPSHOTS: tuple[str, ...] = tuple(f"raw/{source}/{SNAPSHOT_ID}" for source in SOURCES)

SPINE = "curated/tracts_spine.parquet"
ACS_TRACTS = "intermediate/acs_tracts.parquet"
DESTINATIONS = "intermediate/destinations.parquet"
SITES_CONFLATED = "intermediate/sites_conflated.parquet"
SITES = "curated/sites.parquet"
NETWORK = "intermediate/network.json"
TRAVEL_TIMES = "curated/travel_times.parquet"
TRACT_METRICS = "curated/tract_metrics.parquet"
VALIDATION = "intermediate/validation.json"
PUBLIC_ZONE = export.PUBLIC_ZONE

#: The fixture grid's extent in its own CRS (the publish stage's ``bounds`` parameter, which
#: the gate holds every published coordinate to).
FIXTURE_BOUNDS: tuple[float, float, float, float] = (
    LON0,
    LAT0,
    round(LON0 + COLS * CELL, 6),
    round(LAT0 + ROWS * CELL, 6),
)
FIXTURE_CITATION = "phillysim tinycity synthetic fixture (no real provider; synthetic data)."
#: What the fixture's basemap calls its dissolved tract grid (the real pipeline says
#: "Philadelphia County").
FIXTURE_BOUNDARY_NAME = "tinycity (synthetic)"
#: What the fixture's published metrics are (the manifest carries a description per metric).
DESCRIPTIONS: dict[str, str] = {
    "population_total": (
        "Synthetic fixture: ACS-shaped total population estimate with its 90 % margin of "
        "error and CV reliability tier."
    ),
    "time_to_nearest_min": (
        "Synthetic fixture: typical travel time in minutes (median departure) to the nearest "
        "site of the category by the mode, from the fixture's stand-in matrix, censored at "
        f"{CENSOR_MIN:g} minutes."
    ),
}

CATEGORY_OF_SOURCE = {
    "snap_retailers": "supermarket_format",
    "farmers_markets": "farmers_market",
    "meal_sites": "meal_site",
}
HOURS_COLUMNS = (
    "hours_status",
    "open_weekday",
    "open_weekend",
    "open_in_season_week",
    "open_off_season_week",
)


def _raw(source: str) -> str:
    return f"raw/{source}/{SNAPSHOT_ID}"


def _oracle(name: str) -> pd.DataFrame:
    """One of the generator's expected tables, read back from its Parquet bytes."""
    data = render(build_model(Variant.VALID))[f"expected/{name}.parquet"]
    return pd.read_parquet(io.BytesIO(data))


def _write_parquet(frame: pd.DataFrame, ctx: StageContext, rel: str) -> None:
    frame.to_parquet(ctx.output(rel), index=False, engine="pyarrow")


# --- 1. acquire ------------------------------------------------------------------------


def acquire(ctx: StageContext) -> None:
    """Generate tinycity and admit each raw snapshot through the download guards."""
    scratch = ctx.staging / "_generated"
    write_fixture(scratch, Variant(ctx.params["variant"]))
    quarantine_zone = ctx.root / "quarantine"
    for source in SOURCES:
        ctx.checkpoint()
        target = ctx.output(_raw(source))
        shutil.move(str(scratch / "raw" / source / SNAPSHOT_ID), str(target))
        admit(target, quarantine_zone, allowlist=ALLOWLIST, limits=LIMITS)  # QuarantinedError
    shutil.rmtree(scratch)


# --- 2. validate -------------------------------------------------------------------------


def validate(ctx: StageContext) -> None:
    """Check every raw source against its contract; any violation fails the stage."""
    report: dict[str, Any] = {}
    failures: list[str] = []
    for source in SOURCES:
        ctx.checkpoint()
        frame, manifest = load_raw(ctx.root, source)
        violations = check_frame(CONTRACTS[source], frame, manifest)
        report[source] = {
            "snapshot_id": manifest["snapshot_id"],
            "license_bucket": manifest["license_bucket"],
            "schema_version": manifest["schema_version"],
            "rows": int(len(frame)),
            "violations": [str(v) for v in violations],
        }
        failures.extend(str(v) for v in violations)
    ctx.output(VALIDATION).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", "utf-8")
    if failures:
        raise StageError(f"{len(failures)} contract violation(s): " + "; ".join(failures))


# --- 3. spine ----------------------------------------------------------------------------


def spine(ctx: StageContext) -> None:
    """Tract polygons plus population-weighted centroids, keyed by GEOID."""
    tracts = gpd.read_file(ctx.input(_raw("tiger_tracts")) / "tracts.geojson")
    centroids = pd.read_csv(
        ctx.input(_raw("cenpop")) / "centroids.csv", dtype={"geoid": str}
    ).set_index("geoid")
    ctx.checkpoint()
    missing = sorted(set(tracts["geoid"]) - set(centroids.index))
    if missing:
        raise StageError(f"no population-weighted centroid for tract(s) {missing}")
    frame = gpd.GeoDataFrame(
        {
            "geoid": tracts["geoid"].astype(str),
            "name": tracts["name"].astype(str),
            "population": tracts["population"].astype("int64"),
            "centroid_lon": tracts["geoid"].map(centroids["longitude"]).astype("float64"),
            "centroid_lat": tracts["geoid"].map(centroids["latitude"]).astype("float64"),
        },
        geometry=tracts.geometry.values,
        crs=CRS,
    )
    frame = frame.sort_values("geoid").reset_index(drop=True)
    frame.to_parquet(ctx.output(SPINE), index=False)


# --- 4. demographics ------------------------------------------------------------------------


def demographics(ctx: StageContext) -> None:
    """ACS estimates and margins of error, one row per spine tract (suppressed cells stay null)."""
    spine_geoids = pd.read_parquet(ctx.input(SPINE), columns=["geoid"])["geoid"]
    acs = pd.read_csv(ctx.input(_raw("acs")) / "acs.csv", dtype={"geoid": str})
    ctx.checkpoint()
    missing = sorted(set(spine_geoids) - set(acs["geoid"]))
    if missing:
        raise StageError(f"ACS has no row for tract(s) {missing}")
    frame = acs[acs["geoid"].isin(set(spine_geoids))].sort_values("geoid").reset_index(drop=True)
    for column in frame.columns:
        if column != "geoid":
            frame[column] = frame[column].astype("float64")
    _write_parquet(frame, ctx, ACS_TRACTS)


# --- 5. destinations ----------------------------------------------------------------------


def destinations(ctx: StageContext) -> None:
    """The three destination sources as one point table with a source-scoped ID and tract."""
    spine_frame = gpd.read_parquet(ctx.input(SPINE))[["geoid", "geometry"]]
    parts: list[pd.DataFrame] = []
    retailers = pd.read_csv(
        ctx.input(_raw("snap_retailers")) / "retailers.csv", dtype={"record_id": str}
    )
    parts.append(
        pd.DataFrame(
            {
                "source": "snap_retailers",
                "source_record_id": retailers["record_id"].astype(str),
                "name": retailers["store_name"].astype(str),
                "longitude": retailers["longitude"].astype("float64"),
                "latitude": retailers["latitude"].astype("float64"),
            }
        )
    )
    ctx.checkpoint()
    for source, filename, key in (
        ("farmers_markets", "markets.geojson", "market_id"),
        ("meal_sites", "meal_sites.geojson", "site_id"),
    ):
        layer = gpd.read_file(ctx.input(_raw(source)) / filename)
        parts.append(
            pd.DataFrame(
                {
                    "source": source,
                    "source_record_id": layer[key].astype(str),
                    "name": layer["name"].astype(str),
                    "longitude": layer.geometry.x.astype("float64"),
                    "latitude": layer.geometry.y.astype("float64"),
                }
            )
        )
        ctx.checkpoint()
    table = pd.concat(parts, ignore_index=True)
    table.insert(0, "site_id", table["source"] + ":" + table["source_record_id"])
    table.insert(3, "category", table["source"].map(CATEGORY_OF_SOURCE))
    points = gpd.GeoDataFrame(
        table, geometry=gpd.points_from_xy(table["longitude"], table["latitude"]), crs=CRS
    )
    joined = gpd.sjoin(points, spine_frame, how="left", predicate="within")
    unassigned = sorted(joined.loc[joined["geoid"].isna(), "site_id"])
    if unassigned:
        raise StageError(f"destination(s) outside every spine tract: {unassigned}")
    if joined["site_id"].duplicated().any():
        raise StageError("a destination falls inside more than one tract (overlapping spine)")
    table = pd.DataFrame(joined.drop(columns=["geometry", "index_right"]))
    table.insert(5, "geoid", table.pop("geoid").astype(str))
    _write_parquet(table.reset_index(drop=True), ctx, DESTINATIONS)


# --- 6. conflate --------------------------------------------------------------------------


def conflate(ctx: StageContext) -> None:
    """Cross-source de-duplication. Each fixture site appears once, so this is the identity
    (M4 builds the real conflation); the stage still enforces the unique-key contract."""
    table = pd.read_parquet(ctx.input(DESTINATIONS))
    ctx.checkpoint()
    duplicates = sorted(table.loc[table["site_id"].duplicated(), "site_id"])
    if duplicates:
        raise StageError(f"duplicate site id(s) after conflation: {duplicates}")
    _write_parquet(table, ctx, SITES_CONFLATED)


# --- 7. hours ----------------------------------------------------------------------------


def hours(ctx: StageContext) -> None:
    """Hours parsing (Tier 2 labels). STUB: the answers come from the fixture oracle, joined
    by site id; M4's parser replaces this stage's body and keeps its contract."""
    table = pd.read_parquet(ctx.input(SITES_CONFLATED))
    answers = _oracle("sites").set_index("site_id")[list(HOURS_COLUMNS)]
    ctx.checkpoint()
    unknown = sorted(set(table["site_id"]) - set(answers.index))
    if unknown:
        raise StageError(f"no hours oracle for site(s) {unknown}")
    for column in HOURS_COLUMNS:
        table[column] = table["site_id"].map(answers[column])
    for column in HOURS_COLUMNS[1:]:
        table[column] = table[column].astype("boolean")
    _write_parquet(table, ctx, SITES)


# --- 8. network ---------------------------------------------------------------------------


def network(ctx: StageContext) -> None:
    """Summarize the routing inputs (GTFS stops, street edges) the M3 router will consume."""
    stops = pd.read_csv(ctx.input(_raw("gtfs")) / "stops.txt", dtype={"stop_id": str})
    ctx.checkpoint()
    edges = gpd.read_file(ctx.input(_raw("osm_network")) / "edges.geojson")
    summary = {
        "gtfs_stops": int(len(stops)),
        "street_edges": int(len(edges)),
        "street_length_m": round(float(edges["length_m"].sum()), 1),
        "crs": CRS,
    }
    ctx.output(NETWORK).write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", "utf-8")


# --- 9. travel_times -------------------------------------------------------------------


def travel_times(ctx: StageContext) -> None:
    """Travel-time matrix. STUB: the fixture's precomputed matrix, restricted to the spine's
    tracts and the conflated sites and censored at ``censor_min``; M3 replaces the body."""
    geoids = set(pd.read_parquet(ctx.input(SPINE), columns=["geoid"])["geoid"])
    site_ids = set(pd.read_parquet(ctx.input(SITES), columns=["site_id"])["site_id"])
    json.loads(ctx.input(NETWORK).read_text("utf-8"))  # the router's inputs must be present
    ctx.checkpoint()
    matrix = _oracle("travel_times")
    matrix = matrix[matrix["origin_geoid"].isin(geoids) & matrix["site_id"].isin(site_ids)]
    matrix = matrix[matrix["mode"].isin(ctx.params["modes"])].reset_index(drop=True)
    censor = float(ctx.params["censor_min"])
    for column in ("time_median_min", "time_p85_min"):
        matrix[column] = matrix[column].clip(upper=censor).astype("float64")
    _write_parquet(matrix, ctx, TRAVEL_TIMES)


# --- 10. metrics ---------------------------------------------------------------------------


def _cv_tier(
    estimate: float, moe: float, moe_to_se: float, edges: tuple[float, float]
) -> int | None:
    if pd.isna(estimate) or pd.isna(moe) or estimate == 0:
        return None
    cv_pct = (moe / moe_to_se) / abs(estimate) * 100.0
    if cv_pct < edges[0]:
        return 1
    if cv_pct < edges[1]:
        return 2
    return 3


def metrics(ctx: StageContext) -> None:
    """The analytic table: population with CV tiers, and time to the nearest site per
    tract x category x mode (the locked {estimate, moe, cv_tier, reliability_action} shape)."""
    params = ctx.params
    acs = pd.read_parquet(ctx.input(ACS_TRACTS)).set_index("geoid")
    sites = pd.read_parquet(ctx.input(SITES), columns=["site_id", "category"])
    matrix = pd.read_parquet(ctx.input(TRAVEL_TIMES))
    ctx.checkpoint()
    matrix = matrix.assign(category=matrix["site_id"].map(sites.set_index("site_id")["category"]))
    nearest = matrix.groupby(["origin_geoid", "category", "mode"])["time_median_min"].min()
    edges = (float(params["cv_tier_edges_pct"][0]), float(params["cv_tier_edges_pct"][1]))
    rows: list[dict[str, Any]] = []
    for geoid in sorted(acs.index):
        estimate, moe = float(acs.at[geoid, "B01003_001E"]), float(acs.at[geoid, "B01003_001M"])
        tier = _cv_tier(estimate, moe, float(params["moe_to_se"]), edges)
        rows.append(
            {
                "geoid": geoid,
                "metric_id": "population_total",
                "category": None,
                "mode": None,
                "estimate": estimate,
                "moe": moe,
                "cv_tier": tier,
                "reliability_action": "interval-only" if tier == 3 else "none",
            }
        )
        for category in params["categories"]:
            for mode in params["modes"]:
                key = (geoid, category, mode)
                rows.append(
                    {
                        "geoid": geoid,
                        "metric_id": "time_to_nearest_min",
                        "category": category,
                        "mode": mode,
                        "estimate": float(nearest[key]) if key in nearest.index else None,
                        "moe": None,
                        "cv_tier": None,
                        "reliability_action": "none",
                    }
                )
        ctx.checkpoint()
    frame = pd.DataFrame.from_records(rows)
    frame["estimate"] = frame["estimate"].astype("float64")
    frame["moe"] = frame["moe"].astype("float64")
    frame["cv_tier"] = frame["cv_tier"].astype("Int64")
    frame["schema_version"] = pd.Series([int(params["schema_version"])] * len(frame), dtype="int64")
    frame["methods_version"] = str(params["methods_version"])
    _write_parquet(frame, ctx, TRACT_METRICS)


# --- 11. publish ---------------------------------------------------------------------------


def publish(ctx: StageContext) -> None:
    """The public zone (EP-7): the analytic table widened onto the tracts with build-time
    bins, the conflated sites as points, license labels derived from every fixture
    manifest, CSV escaping, and the gate run on the staged zone before install."""
    frame = pd.read_parquet(ctx.input(TRACT_METRICS))
    spine_frame = gpd.read_parquet(ctx.input(SPINE))
    table = pd.read_parquet(ctx.input(SITES))
    ctx.checkpoint()
    sites = gpd.GeoDataFrame(
        table[["site_id", "source", "category", "name", "geoid"]].copy(),
        geometry=gpd.points_from_xy(table["longitude"], table["latitude"]),
        crs=CRS,
    )
    export.publish_zone(
        ctx,
        pipeline=PIPELINE_NAME,
        metrics=frame,
        spine=spine_frame,
        sites=sites,
        raw_snapshots={source: _raw(source) for source in SOURCES},
        citations=dict.fromkeys(SOURCES, FIXTURE_CITATION),
        descriptions=DESCRIPTIONS,
        # The fixture has no roads source (EP-8b decided against a synthetic one), so its
        # basemap is the boundary only; the page handles both shapes.
        boundary_name=FIXTURE_BOUNDARY_NAME,
        roads=None,
    )


# --- the pipeline ---------------------------------------------------------------------------


def fixture_pipeline() -> Pipeline:
    """The eleven fixture stages, wired as a DAG over data-root paths."""
    return Pipeline(
        PIPELINE_NAME,
        [
            Stage(
                "acquire",
                acquire,
                outputs=RAW_SNAPSHOTS,
                params={"variant": Variant.VALID.value, "generator": "tinycity"},
                description="generate tinycity and admit its snapshots into the raw zone",
            ),
            Stage(
                "validate",
                validate,
                inputs=RAW_SNAPSHOTS,
                outputs=(VALIDATION,),
                params={"schema_version": SCHEMA_VERSION},
                description="check every raw source against its contract",
            ),
            Stage(
                "spine",
                spine,
                inputs=(_raw("tiger_tracts"), _raw("cenpop")),
                outputs=(SPINE,),
                params={"crs": CRS},
                description="tract spine with population-weighted centroids",
            ),
            Stage(
                "demographics",
                demographics,
                inputs=(_raw("acs"), SPINE),
                outputs=(ACS_TRACTS,),
                params={"tables": ["B01003_001", "B08201_002"]},
                description="ACS estimates and MOE on the spine",
            ),
            Stage(
                "destinations",
                destinations,
                inputs=(_raw("snap_retailers"), _raw("farmers_markets"), _raw("meal_sites"), SPINE),
                outputs=(DESTINATIONS,),
                params={"categories": list(CATEGORIES)},
                description="destination points normalized and assigned to tracts",
            ),
            Stage(
                "conflate",
                conflate,
                inputs=(DESTINATIONS,),
                outputs=(SITES_CONFLATED,),
                params={"key": "site_id"},
                description="cross-source de-duplication (identity on the fixture)",
            ),
            Stage(
                "hours",
                hours,
                inputs=(SITES_CONFLATED,),
                outputs=(SITES,),
                params={
                    "in_season_week_start": IN_SEASON_WEEK_START,
                    "off_season_week_start": OFF_SEASON_WEEK_START,
                },
                description="hours parsing (stub: oracle answers)",
            ),
            Stage(
                "network",
                network,
                inputs=(_raw("gtfs"), _raw("osm_network")),
                outputs=(NETWORK,),
                params={"crs": CRS},
                description="routing inputs summarized",
            ),
            Stage(
                "travel_times",
                travel_times,
                inputs=(SPINE, SITES, NETWORK),
                outputs=(TRAVEL_TIMES,),
                params={"censor_min": CENSOR_MIN, "modes": list(MODES)},
                description="travel-time matrix (stub: precomputed, censored)",
            ),
            Stage(
                "metrics",
                metrics,
                inputs=(ACS_TRACTS, SITES, TRAVEL_TIMES),
                outputs=(TRACT_METRICS,),
                params={
                    "categories": list(CATEGORIES),
                    "modes": list(MODES),
                    "moe_to_se": MOE_TO_SE,
                    "cv_tier_edges_pct": list(CV_TIER_EDGES_PCT),
                    "schema_version": SCHEMA_VERSION,
                    "methods_version": METHODS_VERSION,
                },
                description="analytic table with CV tiers and time to nearest",
            ),
            Stage(
                "publish",
                publish,
                # Provenance: every raw snapshot upstream of the analytic table and the
                # sites (all eight; the test suite checks this list against the DAG).
                inputs=(TRACT_METRICS, SPINE, SITES, *RAW_SNAPSHOTS),
                outputs=(PUBLIC_ZONE,),
                params={
                    "public_schema_version": export.PUBLIC_SCHEMA_VERSION,
                    "bounds": list(FIXTURE_BOUNDS),
                    "coordinate_decimals": export.COORDINATE_DECIMALS,
                    "bin_classes": bins.BIN_CLASSES,
                    "bin_method": bins.BIN_METHOD,
                },
                description="public zone: license-labeled, binned, escaped GeoJSON + CSV, "
                "gated before install",
            ),
        ],
    )
