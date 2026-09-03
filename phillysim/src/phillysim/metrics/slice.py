"""The thin-slice QA metric (EP-7): straight-line distance from each tract's population-weighted
center to the nearest supermarket-format SNAP retailer.

**QA only, never an access measure.** methodology.md ("Travel model") is explicit:
straight-line distance is computed only as a QA column. This metric exists to
carry one number per tract from the curated zone through the publish gate into
the public zone and onto EP-8's page, so that the labeling, binning, escaping,
and gate machinery is proven end to end before the real metrics (network
travel time, M3 / M5) exist. Its ID starts with ``qa_``, which the public
manifest flags as QA-only and the gate enforces; its description says so; the
method card (docs/method-cards/qa-straight-line.md) says so again. When M5's
metrics land, this column is retained as a QA column, not promoted.

The computation is a plain nearest-neighbour query in the analysis CRS
(EPSG:26918, metres; ADR-0007): origins are the CenPop centers the spine
carries (:func:`phillysim.spine.centroids_in`), destinations are the layer's
rows with ``supermarket_format`` true (EP-6). Distances are Euclidean in the
projected plane, rounded to a tenth of a metre; a tract's distance is null only
if there is no destination at all.
"""

from __future__ import annotations

import json
from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
from pyproj import CRS

from phillysim.contracts import ANALYTIC_TABLE, check_frame
from phillysim.destinations import SNAP_RETAILERS
from phillysim.manifest import SCHEMA_VERSION
from phillysim.spine import SPINE, centroids_in
from phillysim.stages import StageContext, StageError

METRIC_ID = "qa_straight_line_m"
CATEGORY = "supermarket_format"
#: The methods-axis version of this stage's definition (ADR-0006); any change bumps it.
METHODS_VERSION = "slice-qa-1"
TRACT_METRICS = "curated/tract_metrics.parquet"
SLICE_REPORT = "intermediate/slice_metric.json"

DESCRIPTION = (
    "QA-only plumbing check, not an access measure: straight-line (Euclidean) distance in "
    "metres, in the analysis CRS, from the tract's 2020 population-weighted center to the "
    "nearest SNAP-authorized supermarket-format retailer. Access is measured as network "
    "travel time (roadmap/methodology.md); this column only proves the publication path."
)
DESCRIPTIONS: dict[str, str] = {METRIC_ID: DESCRIPTION}


def nearest_distance(origins: gpd.GeoSeries, destinations: gpd.GeoSeries) -> pd.Series:
    """Distance in metres from each origin to its nearest destination (float64, origins' index).

    Both series must carry the same *projected* CRS in metres; the query is planar. With no
    destination at all every distance is null. Ties resolve to the first destination in
    order, and only the distance is returned, so ties cannot change the result.
    """
    if origins.crs is None or destinations.crs is None:
        raise ValueError("origins and destinations must both carry a CRS")
    crs = CRS.from_user_input(origins.crs)
    if crs != CRS.from_user_input(destinations.crs):
        raise ValueError(
            f"CRS mismatch: origins {origins.crs!r}, destinations {destinations.crs!r}"
        )
    if not crs.is_projected or crs.axis_info[0].unit_name != "metre":
        raise ValueError(
            f"straight-line distance needs a projected CRS in metres, not {crs.name!r}"
        )
    out = pd.Series(np.nan, index=origins.index, dtype="float64")
    if len(destinations) == 0 or len(origins) == 0:
        return out
    tree = shapely.STRtree(destinations.geometry.to_numpy())
    positions, distances = tree.query_nearest(
        origins.geometry.to_numpy(), return_distance=True, all_matches=False
    )
    out.iloc[positions[0]] = np.round(distances, 1)
    return out


def slice_table(
    spine: gpd.GeoDataFrame,
    destinations: gpd.GeoSeries,
    *,
    crs: str,
    category: str = CATEGORY,
    methods_version: str = METHODS_VERSION,
    schema_version: int = SCHEMA_VERSION,
) -> pd.DataFrame:
    """The analytic table for the QA metric: one row per spine tract, in the locked shape
    (``estimate`` = metres; ``moe`` / ``cv_tier`` null, there is no sampling error;
    ``reliability_action`` ``none``), sorted by GEOID."""
    origins = centroids_in(spine, crs)
    distance = nearest_distance(origins, destinations.to_crs(crs))
    n = len(spine)
    frame = pd.DataFrame(
        {
            "geoid": spine["geoid"].astype(str).to_numpy(),
            "metric_id": METRIC_ID,
            "category": category,
            "mode": pd.Series([None] * n, dtype="object"),
            "estimate": distance.to_numpy(dtype="float64"),
            "moe": pd.Series([np.nan] * n, dtype="float64"),
            "cv_tier": pd.Series([pd.NA] * n, dtype="Int64"),
            "reliability_action": "none",
            "schema_version": pd.Series([int(schema_version)] * n, dtype="int64"),
            "methods_version": str(methods_version),
        }
    )
    frame = frame.sort_values("geoid").reset_index(drop=True)
    violations = check_frame(ANALYTIC_TABLE, frame)
    if violations:
        raise StageError(
            f"QA slice table breaks the analytic contract: {'; '.join(str(v) for v in violations)}"
        )
    return frame


def summarize(frame: pd.DataFrame, *, destinations: int) -> dict[str, Any]:
    """The stage report: counts and the distance distribution, for the handoff and the card."""
    values = frame["estimate"].dropna()
    return {
        "metric_id": METRIC_ID,
        "category": CATEGORY,
        "methods_version": str(frame["methods_version"].iloc[0]) if len(frame) else None,
        "qa_only": True,
        "tracts": int(len(frame)),
        "destinations": int(destinations),
        "null_estimates": int(frame["estimate"].isna().sum()),
        "distance_m": {
            "min": float(values.min()) if len(values) else None,
            "median": float(values.median()) if len(values) else None,
            "max": float(values.max()) if len(values) else None,
        },
    }


def metrics(ctx: StageContext) -> None:
    """The real pipeline's ``metrics`` stage (EP-7 body): the QA slice metric on the spine."""
    crs = str(ctx.params["crs"])
    if str(ctx.params["methods_version"]) != METHODS_VERSION:
        raise StageError(
            f"stage parameter methods_version {ctx.params['methods_version']!r} != this "
            f"metric's {METHODS_VERSION!r}"
        )
    spine = gpd.read_parquet(ctx.input(SPINE))
    layer = gpd.read_parquet(ctx.input(SNAP_RETAILERS))
    ctx.checkpoint()
    points = layer.loc[layer["supermarket_format"].astype(bool), layer.geometry.name]
    frame = slice_table(
        spine,
        points,
        crs=crs,
        category=str(ctx.params["category"]),
        schema_version=int(ctx.params["schema_version"]),
    )
    frame.to_parquet(ctx.output(TRACT_METRICS), index=False, engine="pyarrow")
    report = summarize(frame, destinations=len(points))
    ctx.output(SLICE_REPORT).write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", "utf-8"
    )
