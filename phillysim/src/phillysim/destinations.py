"""Destination layers on the tract spine: the SNAP retailer point layer (EP-6).

The first destination layer of the real pipeline: every SNAP-authorized
retailer in Philadelphia County as of the file's as-of date, classified by
the published store-format mapping (:mod:`phillysim.classify.store_format`),
assigned to the tract containing it, keyed by a stable source-scoped site ID
(``snap_retailers:<USDA record ID>``), geometry in the analysis CRS
(ADR-0007), the provider's coordinates kept as delivered in ``longitude`` /
``latitude``. One layer serves both destination sets methodology.md names:
the **supermarket-format** layer is the rows with ``supermarket_format``
true (AM-4), and the **all-SNAP-retailer** variant M5 compares with USDA's
SRAM is the whole table. Nothing is de-duplicated across sources here
(conflation is M4), and the file carries no hours (the SNAP file has none).

:func:`check_snap_layer` is the layer's invariant set, enforced by the stage
on its own output like the spine's: CRS as declared, unique site IDs, every
format class from the mapping and the supermarket flag consistent with it,
every point inside the county bounds, every assigned tract a spine tract.
A point the spine does not contain keeps a null ``geoid`` (the provider
attributes it to the county; the stage report counts them), so the
all-retailer count matches the source and nothing is silently dropped.
"""

from __future__ import annotations

import json
from typing import Any

import geopandas as gpd
import pandas as pd
from pyproj import CRS

from phillysim import adapters
from phillysim.adapters.base import TRACT_GEOID_PATTERN
from phillysim.classify import store_format
from phillysim.spine import ANALYSIS_CRS, SPINE, county_bounds
from phillysim.stages import StageContext, StageError

SNAP_RETAILERS = "curated/snap_retailers.parquet"
SNAP_REPORT = "intermediate/snap_retailers.json"
SNAP_LAYER_COLUMNS: tuple[str, ...] = (
    "site_id",
    "source",
    "source_record_id",
    "name",
    "store_type",
    "format_class",
    "supermarket_format",
    "geoid",
    "longitude",
    "latitude",
    "authorized_since",
    "geometry",
)


def site_ids(source: str, record_ids: pd.Series) -> pd.Series:
    """Source-scoped site IDs, ``<source>:<record id>`` (the data dictionary's key form)."""
    return source + ":" + record_ids.astype(str)


def assign_tracts(points: gpd.GeoSeries, spine: gpd.GeoDataFrame) -> pd.Series:
    """The spine GEOID containing each point (null where none does), index preserved.

    A point on a shared boundary that falls within two tracts gets the smaller GEOID,
    deterministically; the caller reports how many.
    """
    frame = gpd.GeoDataFrame(geometry=points.to_crs(spine.crs))
    joined = gpd.sjoin(frame, spine[["geoid", "geometry"]], how="left", predicate="within")
    joined = joined.sort_values("geoid", kind="stable")
    first = joined[~joined.index.duplicated(keep="first")]
    return first["geoid"].reindex(points.index).astype("string")


def build_snap_layer(
    retailers: gpd.GeoDataFrame, spine: gpd.GeoDataFrame, crs: str = ANALYSIS_CRS
) -> gpd.GeoDataFrame:
    """The classified SNAP retailer layer from the adapter's read and the curated spine."""
    classes = store_format.classify(retailers["Store Type"])
    record_ids = retailers["Record ID"].astype(str)
    authorized = pd.to_datetime(
        retailers["Authorization Date"], format=adapters.snap.DATE_FORMAT, errors="raise"
    )
    frame = gpd.GeoDataFrame(
        {
            "site_id": site_ids(adapters.snap.SOURCE, record_ids).to_numpy(),
            "source": adapters.snap.SOURCE,
            "source_record_id": record_ids.to_numpy(),
            "name": retailers["Store Name"].astype(str).to_numpy(),
            "store_type": retailers["Store Type"].astype(str).to_numpy(),
            "format_class": classes["format_class"].astype(str).to_numpy(),
            "supermarket_format": classes["supermarket_format"].to_numpy(),
            "geoid": assign_tracts(retailers.geometry, spine).to_numpy(),
            "longitude": retailers["Longitude"].astype("float64").to_numpy(),
            "latitude": retailers["Latitude"].astype("float64").to_numpy(),
            "authorized_since": authorized.to_numpy(),
        },
        geometry=retailers.geometry.to_crs(crs).to_numpy(),
        crs=crs,
    )
    frame["geoid"] = frame["geoid"].astype("string")
    return frame.sort_values("site_id", kind="stable").reset_index(drop=True)


def check_snap_layer(
    layer: gpd.GeoDataFrame,
    *,
    crs: str = ANALYSIS_CRS,
    spine_geoids: pd.Series | None = None,
) -> list[str]:
    """The layer's invariants, as a list of violations (empty when the layer is sound)."""
    problems: list[str] = []
    missing = [column for column in SNAP_LAYER_COLUMNS if column not in layer.columns]
    if missing:
        return [f"missing column(s) {missing}"]
    if len(layer) == 0:
        problems.append("empty layer")

    ids = layer["site_id"].astype(str)
    prefix = adapters.snap.SOURCE + ":"
    bad_ids = sorted(i for i in ids if not i.startswith(prefix) or i == prefix)
    if bad_ids:
        problems.append(f"{len(bad_ids)} site ID(s) not of the form {prefix}<record id>")
    duplicates = sorted(ids[ids.duplicated()].unique())
    if duplicates:
        problems.append(f"{len(duplicates)} duplicate site ID(s): {duplicates[:5]}")
    if (layer["source"].astype(str) != adapters.snap.SOURCE).any():
        problems.append(f"source column is not {adapters.snap.SOURCE!r} throughout")

    known = store_format.load_table().set_index("store_type")
    unknown_types = sorted(set(layer["store_type"].astype(str)) - set(known.index))
    if unknown_types:
        problems.append(f"store type(s) outside the mapping: {unknown_types[:5]}")
    else:
        expected_class = layer["store_type"].astype(str).map(known["format_class"]).astype(str)
        mismatched = int((expected_class != layer["format_class"].astype(str)).sum())
        if mismatched:
            problems.append(f"{mismatched} row(s) whose format_class disagrees with the mapping")
    stray_classes = sorted(
        set(layer["format_class"].astype(str)) - set(store_format.FORMAT_CLASSES)
    )
    if stray_classes:
        problems.append(f"format class(es) outside the vocabulary: {stray_classes[:5]}")
    flag = layer["supermarket_format"]
    if flag.dtype != bool or flag.isna().any():
        problems.append("supermarket_format is not a non-null boolean column")
    elif (flag != (layer["format_class"].astype(str) == store_format.SUPERMARKET_FORMAT)).any():
        problems.append("supermarket_format disagrees with format_class")

    geoids = layer["geoid"]
    assigned = geoids.dropna().astype(str)
    bad_geoids = sorted(
        g for g in assigned if not pd.Series([g]).str.fullmatch(TRACT_GEOID_PATTERN)[0]
    )
    if bad_geoids:
        problems.append(
            f"{len(bad_geoids)} tract ID(s) not Philadelphia County tracts: {bad_geoids[:5]}"
        )
    if spine_geoids is not None:
        outside = sorted(set(assigned) - set(spine_geoids.astype(str)))
        if outside:
            problems.append(f"{len(outside)} tract ID(s) not in the spine: {outside[:5]}")

    declared = CRS.from_user_input(crs)
    if layer.crs is None or CRS.from_user_input(layer.crs) != declared:
        problems.append(f"CRS is {layer.crs!r}, expected {crs}")
        return problems
    geometry = layer.geometry
    empty = int((geometry.isna() | geometry.is_empty).sum())
    if empty:
        problems.append(f"{empty} null/empty geometr(ies)")
    present = geometry[~(geometry.isna() | geometry.is_empty)]
    stray = sorted(set(present.geom_type) - {"Point"})
    if stray:
        problems.append(f"geometry type(s) {stray} outside Point")
    minx, miny, maxx, maxy = county_bounds(crs)
    x, y = present.x, present.y
    outside_bounds = present[(x < minx) | (x > maxx) | (y < miny) | (y > maxy)]
    if len(outside_bounds):
        problems.append(
            f"{len(outside_bounds)} point(s) outside the county bounds: "
            f"{sorted(ids[outside_bounds.index])[:5]}"
        )
    return problems


def summarize(layer: gpd.GeoDataFrame, *, crs: str, as_of: str) -> dict[str, Any]:
    """The stage report: counts the handoff and the data card cite."""
    by_type = layer["store_type"].astype(str).value_counts().sort_index()
    by_class = layer["format_class"].astype(str).value_counts().sort_index()
    return {
        "as_of": as_of,
        "crs": crs,
        "mapping_version": store_format.MAPPING_VERSION,
        "rows": int(len(layer)),
        "supermarket_format": int(layer["supermarket_format"].sum()),
        "unassigned_to_tract": int(layer["geoid"].isna().sum()),
        "tracts_with_any_retailer": int(layer["geoid"].dropna().nunique()),
        "tracts_with_supermarket_format": int(
            layer.loc[layer["supermarket_format"], "geoid"].dropna().nunique()
        ),
        "by_store_type": {str(k): int(v) for k, v in by_type.items()},
        "by_format_class": {str(k): int(v) for k, v in by_class.items()},
    }


def _raw(ctx: StageContext, source: str) -> str:
    prefix = f"raw/{source}/"
    matches = [rel for rel in ctx.stage.inputs if rel.startswith(prefix)]
    if len(matches) != 1:
        raise StageError(f"stage {ctx.stage.name!r} declares {len(matches)} {source} snapshot(s)")
    return matches[0]


def snap_retailers(ctx: StageContext) -> None:
    """The classified SNAP retailer point layer on the spine, invariants enforced."""
    crs = str(ctx.params["crs"])
    if str(ctx.params["mapping_version"]) != store_format.MAPPING_VERSION:
        raise StageError(
            f"stage parameter mapping_version {ctx.params['mapping_version']!r} != packaged "
            f"mapping {store_format.MAPPING_VERSION!r}"
        )
    as_of = str(ctx.params["as_of"])
    spine = gpd.read_parquet(ctx.input(SPINE))
    retailers = adapters.snap.read(ctx.input(_raw(ctx, adapters.snap.SOURCE)))
    ctx.checkpoint()
    layer = build_snap_layer(retailers, spine, crs)
    problems = check_snap_layer(layer, crs=crs, spine_geoids=spine["geoid"])
    if problems:
        raise StageError(
            f"SNAP retailer layer: {len(problems)} invariant violation(s): " + "; ".join(problems)
        )
    layer.to_parquet(ctx.output(SNAP_RETAILERS), index=False)
    report = summarize(layer, crs=crs, as_of=as_of)
    ctx.output(SNAP_REPORT).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", "utf-8")
