"""The curated tract spine and the geospatial invariants every later packet inherits (EP-5b).

The spine is one GeoParquet table keyed by 2020 GEOID for Philadelphia
County's tracts: TIGER/Line geometry reprojected into the pinned analysis
CRS (:data:`ANALYSIS_CRS`, ADR-0007), the 2020 Census population and the
population-weighted center from CenPop2020 (never recomputed from geometry),
and the display name. ``demographics`` joins the pinned ACS estimates and
their margins of error to the spine one-to-one, leaving suppressed cells
null (ADR-0004). Both stage bodies live here and are registered by
:mod:`phillysim.pipeline`; the shape is the data dictionary's
``tracts_spine.parquet`` / ``acs_tracts.parquet``.

:func:`check_spine` is the invariant module the brief asks for: CRS as
declared, every geometry valid and inside the county bounds, GEOID pattern,
uniqueness, and count, exactly one CenPop center and one ACS row per tract.
The ``spine`` and ``demographics`` stages run it on their own output and fail
on any violation, so a real run enforces the invariants; the test suite runs
the same function on the committed samples and on the real spine when a data
root is given (``pytest --real-data-root``).
"""

from __future__ import annotations

import re
from collections.abc import Sequence

import geopandas as gpd
import pandas as pd
from pyproj import CRS, Transformer

from phillysim import adapters
from phillysim.adapters.acs import column_names as acs_column_names
from phillysim.adapters.base import ANALYSIS_CRS, COUNTY_BOUNDS, NAD83, TRACT_GEOID_PATTERN
from phillysim.stages import StageContext, StageError

#: Philadelphia County's 2020 census tracts (Census Bureau count; the stop condition).
TRACT_COUNT = 408

SPINE = "curated/tracts_spine.parquet"
ACS_TRACTS = "intermediate/acs_tracts.parquet"
SPINE_COLUMNS: tuple[str, ...] = (
    "geoid",
    "name",
    "population",
    "centroid_lon",
    "centroid_lat",
    "geometry",
)


def county_bounds(crs: str) -> tuple[float, float, float, float]:
    """The county bounds (:data:`~phillysim.adapters.base.COUNTY_BOUNDS`, NAD 83 degrees)
    expressed in ``crs`` as (minx, miny, maxx, maxy)."""
    transformer = Transformer.from_crs(NAD83, crs, always_xy=True)
    return tuple(transformer.transform_bounds(*COUNTY_BOUNDS))  # type: ignore[return-value]


# --- building ---------------------------------------------------------------------------------


def build_spine(
    tracts: gpd.GeoDataFrame, centers: gpd.GeoDataFrame, crs: str = ANALYSIS_CRS
) -> gpd.GeoDataFrame:
    """The curated spine from the TIGER read and the CenPop read (both county-filtered).

    One row per TIGER tract, sorted by GEOID; population and the population-weighted
    center come from CenPop, joined one-to-one on GEOID (a tract without a center, or a
    center without a tract, is an error: the two vintages must agree); geometry is
    reprojected into ``crs``.
    """
    tract_ids = tracts["GEOID"].astype(str)
    center_ids = centers["geoid"].astype(str)
    if tract_ids.duplicated().any() or center_ids.duplicated().any():
        raise StageError("duplicate GEOIDs in the tract or center table")
    missing = sorted(set(tract_ids) - set(center_ids))
    extra = sorted(set(center_ids) - set(tract_ids))
    if missing or extra:
        raise StageError(
            f"TIGER and CenPop disagree on the tract set: {len(missing)} tract(s) without a "
            f"center {missing[:5]}, {len(extra)} center(s) without a tract {extra[:5]}"
        )
    by_geoid = centers.set_index(center_ids)
    projected = tracts.geometry.to_crs(crs)
    frame = gpd.GeoDataFrame(
        {
            "geoid": tract_ids.to_numpy(),
            "name": tracts["NAMELSAD"].astype(str).to_numpy(),
            "population": tract_ids.map(by_geoid["POPULATION"]).astype("int64").to_numpy(),
            "centroid_lon": tract_ids.map(by_geoid["LONGITUDE"]).astype("float64").to_numpy(),
            "centroid_lat": tract_ids.map(by_geoid["LATITUDE"]).astype("float64").to_numpy(),
        },
        geometry=projected.to_numpy(),
        crs=crs,
    )
    return frame.sort_values("geoid").reset_index(drop=True)


def join_demographics(spine_geoids: pd.Series, acs: pd.DataFrame) -> pd.DataFrame:
    """The ACS table restricted to the spine's tracts, one row per tract, sorted by GEOID.

    Every spine tract must have exactly one ACS row (the two vintages must agree); ACS
    rows for tracts outside the spine are dropped. Value columns are float64 with nulls
    where the provider suppressed or annotated the cell (ADR-0004).
    """
    wanted = set(spine_geoids.astype(str))
    ids = acs["geoid"].astype(str)
    if ids.duplicated().any():
        raise StageError("duplicate GEOIDs in the ACS table")
    missing = sorted(wanted - set(ids))
    if missing:
        raise StageError(f"ACS has no row for {len(missing)} spine tract(s): {missing[:5]}")
    frame = acs[ids.isin(wanted)].sort_values("geoid").reset_index(drop=True)
    frame = frame[["geoid", *acs_column_names()]].copy()
    frame["geoid"] = frame["geoid"].astype(str)
    for column in acs_column_names():
        frame[column] = frame[column].astype("float64")
    return frame


def centroids_in(frame: gpd.GeoDataFrame, crs: str | None = None) -> gpd.GeoSeries:
    """The population-weighted centers as points in ``crs`` (default: the frame's own CRS).

    The spine stores them as the degrees CenPop publishes (``centroid_lon`` /
    ``centroid_lat``, NAD 83); this is the one place that turns them into geometry.
    """
    points = gpd.GeoSeries(
        gpd.points_from_xy(frame["centroid_lon"], frame["centroid_lat"]),
        index=frame.index,
        crs=NAD83,
    )
    return points.to_crs(crs or frame.crs)


# --- invariants ---------------------------------------------------------------------------


def check_spine(
    spine: gpd.GeoDataFrame,
    *,
    crs: str = ANALYSIS_CRS,
    expected_tracts: int | None = TRACT_COUNT,
    centers: pd.DataFrame | None = None,
    acs: pd.DataFrame | None = None,
) -> list[str]:
    """The geospatial invariants, as a list of violations (empty when the spine is sound).

    ``crs``: the declared analysis CRS the geometry must carry. ``expected_tracts``: the
    exact row count (``None`` skips the count; the samples have six). ``centers`` /
    ``acs``: when given, every tract must have exactly one row in each (join cardinality),
    and every row must belong to a tract.
    """
    problems: list[str] = []
    missing_columns = [column for column in SPINE_COLUMNS if column not in spine.columns]
    if missing_columns:
        return [f"missing column(s) {missing_columns}"]

    # GEOID integrity: 2020-vintage Philadelphia County tracts, unique, the expected count.
    geoids = spine["geoid"].astype(str)
    pattern = re.compile(rf"^{TRACT_GEOID_PATTERN}$")
    bad = sorted(g for g in geoids if not pattern.match(g))
    if bad:
        problems.append(f"{len(bad)} GEOID(s) are not Philadelphia County 2020 tracts: {bad[:5]}")
    duplicates = sorted(geoids[geoids.duplicated()].unique())
    if duplicates:
        problems.append(f"{len(duplicates)} duplicate GEOID(s): {duplicates[:5]}")
    if expected_tracts is not None and len(spine) != expected_tracts:
        problems.append(f"{len(spine)} tract(s), expected {expected_tracts}")

    # CRS as declared.
    declared = CRS.from_user_input(crs)
    if spine.crs is None or CRS.from_user_input(spine.crs) != declared:
        problems.append(f"CRS is {spine.crs!r}, expected {crs}")
        return problems  # the bounds below are meaningless in another CRS
    geometry = spine.geometry

    # Geometry validity: present, polygonal, valid.
    empty = int((geometry.isna() | geometry.is_empty).sum())
    if empty:
        problems.append(f"{empty} null/empty geometr(ies)")
    present = geometry[~(geometry.isna() | geometry.is_empty)]
    stray = sorted(set(present.geom_type) - {"Polygon", "MultiPolygon"})
    if stray:
        problems.append(f"geometry type(s) {stray} outside Polygon / MultiPolygon")
    invalid = present[~present.is_valid]
    if len(invalid):
        reasons = sorted(set(invalid.is_valid_reason()))[:3]
        problems.append(f"{len(invalid)} invalid geometr(ies): {reasons}")

    # County bounds, in the analysis CRS: every geometry and every center inside.
    minx, miny, maxx, maxy = county_bounds(crs)
    bounds = present.bounds
    outside = bounds[
        (bounds["minx"] < minx)
        | (bounds["miny"] < miny)
        | (bounds["maxx"] > maxx)
        | (bounds["maxy"] > maxy)
    ]
    if len(outside):
        problems.append(
            f"{len(outside)} geometr(ies) outside the county bounds: "
            f"{sorted(geoids[outside.index])[:5]}"
        )
    centers_here = centroids_in(spine, crs)
    cx, cy = centers_here.x, centers_here.y
    center_outside = spine[(cx < minx) | (cx > maxx) | (cy < miny) | (cy > maxy)]
    if len(center_outside):
        problems.append(
            f"{len(center_outside)} population-weighted center(s) outside the county bounds: "
            f"{sorted(center_outside['geoid'].astype(str))[:5]}"
        )

    # Join cardinality: exactly one center and one ACS row per tract, nothing unmatched.
    if centers is not None:
        problems += _cardinality("CenPop center", geoids, centers["geoid"].astype(str))
    if acs is not None:
        problems += _cardinality("ACS row", geoids, acs["geoid"].astype(str))
        absent = [c for c in acs_column_names() if c not in acs.columns]
        if absent:
            problems.append(f"ACS table lacks estimate / MOE column(s) {absent}")
    return problems


def _cardinality(what: str, geoids: pd.Series, other: pd.Series) -> list[str]:
    problems: list[str] = []
    counts = other.value_counts()
    missing = sorted(set(geoids) - set(counts.index))
    if missing:
        problems.append(f"{len(missing)} tract(s) without a {what}: {missing[:5]}")
    multiple = sorted(counts[counts > 1].index)
    if multiple:
        problems.append(f"{len(multiple)} tract(s) with more than one {what}: {multiple[:5]}")
    unmatched = sorted(set(counts.index) - set(geoids))
    if unmatched:
        problems.append(f"{len(unmatched)} {what}(s) for no spine tract: {unmatched[:5]}")
    return problems


def enforce(problems: Sequence[str], what: str) -> None:
    """Raise :class:`~phillysim.stages.StageError` naming every violation, if any."""
    if problems:
        raise StageError(f"{what}: {len(problems)} invariant violation(s): " + "; ".join(problems))


# --- the stage bodies ---------------------------------------------------------------------


def _raw(ctx: StageContext, source: str) -> str:
    """The declared raw-snapshot input of ``source`` (the stage declares exactly one)."""
    prefix = f"raw/{source}/"
    matches = [rel for rel in ctx.stage.inputs if rel.startswith(prefix)]
    if len(matches) != 1:
        raise StageError(f"stage {ctx.stage.name!r} declares {len(matches)} {source} snapshot(s)")
    return matches[0]


def spine(ctx: StageContext) -> None:
    """Tract polygons in the analysis CRS plus CenPop population and centers, keyed by GEOID."""
    crs = str(ctx.params["crs"])
    expected = ctx.params["expected_tracts"]
    tracts = adapters.tiger.read(ctx.input(_raw(ctx, adapters.tiger.SOURCE)))
    centers = adapters.cenpop.read(ctx.input(_raw(ctx, adapters.cenpop.SOURCE)))
    ctx.checkpoint()
    frame = build_spine(tracts, centers, crs)
    enforce(
        check_spine(
            frame,
            crs=crs,
            expected_tracts=None if expected is None else int(expected),
            centers=centers,
        ),
        "curated spine",
    )
    frame.to_parquet(ctx.output(SPINE), index=False)


def demographics(ctx: StageContext) -> None:
    """ACS estimates and margins of error, one row per spine tract (suppressed cells stay null)."""
    spine_frame = gpd.read_parquet(ctx.input(SPINE))
    table = adapters.acs.read(ctx.input(_raw(ctx, adapters.acs.SOURCE)))
    ctx.checkpoint()
    frame = join_demographics(spine_frame["geoid"], table)
    enforce(
        check_spine(spine_frame, crs=str(spine_frame.crs), expected_tracts=None, acs=frame),
        "demographics",
    )
    frame.to_parquet(ctx.output(ACS_TRACTS), index=False, engine="pyarrow")
