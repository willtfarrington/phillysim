"""The basemap's roads layer on the tract spine and its invariants (EP-8b).

ADR-0005's minimal public-domain basemap is the county boundary plus the
major roads, grayscale. The boundary needs no source of its own (the
``publish`` stage dissolves the spine's tract polygons); the roads do. This
module's ``basemap`` stage reads the admitted TIGER/Line county roads
snapshot through its adapter (primary and secondary roads only,
:mod:`phillysim.adapters.tiger_roads`), reprojects into the analysis CRS
(ADR-0007), keeps the provider's identifier, name, route type, and feature
class under project column names, and writes one GeoParquet layer that the
``publish`` stage turns into the public ``basemap.geojson`` beside the
boundary. Nothing is clipped or simplified: the provider's county file is
the county scope, and :func:`check_roads` verifies it against the spine
rather than cutting geometry (every road must touch the county's tracts;
the stage report records how much length, if any, lies outside them).

:func:`check_roads` is the layer's invariant set, enforced by the stage on
its own output like the spine's and the SNAP layer's: CRS as declared,
unique identifiers, feature classes within the major-road vocabulary, every
geometry a valid, non-empty line inside the county bounds, every road
touching the spine.
"""

from __future__ import annotations

import json
from typing import Any

import geopandas as gpd
from pyproj import CRS

from phillysim import adapters
from phillysim.adapters.tiger_roads import MAJOR_ROAD_CLASSES, ROUTE_TYPES
from phillysim.spine import ANALYSIS_CRS, SPINE, county_bounds
from phillysim.stages import StageContext, StageError

ROADS = "curated/basemap_roads.parquet"
BASEMAP_REPORT = "intermediate/basemap.json"
ROAD_COLUMNS: tuple[str, ...] = ("linearid", "name", "mtfcc", "route_type", "geometry")
LINE_TYPES: frozenset[str] = frozenset({"LineString", "MultiLineString"})


def build_roads(roads: gpd.GeoDataFrame, crs: str = ANALYSIS_CRS) -> gpd.GeoDataFrame:
    """The curated roads layer from the adapter's read: project column names, the analysis
    CRS, sorted by identifier. The geometry is the provider's, reprojected and nothing else."""
    frame = gpd.GeoDataFrame(
        {
            "linearid": roads["LINEARID"].astype("string").to_numpy(),
            "name": roads["FULLNAME"].astype("string").to_numpy(),
            "mtfcc": roads["MTFCC"].astype("string").to_numpy(),
            "route_type": roads["RTTYP"].astype("string").to_numpy(),
        },
        geometry=roads.geometry.to_numpy(),
        crs=roads.crs,
    ).to_crs(crs)
    frame = frame[list(ROAD_COLUMNS)]
    return frame.sort_values("linearid", kind="stable").reset_index(drop=True)


def check_roads(
    layer: gpd.GeoDataFrame,
    *,
    crs: str = ANALYSIS_CRS,
    spine: gpd.GeoDataFrame | None = None,
) -> list[str]:
    """The layer's invariants, as a list of violations (empty when the layer is sound).

    ``spine``: when given, every road must intersect the union of its tract polygons (the
    county scope the provider's file promises), compared in the layer's own CRS.
    """
    problems: list[str] = []
    missing = [column for column in ROAD_COLUMNS if column not in layer.columns]
    if missing:
        return [f"missing column(s) {missing}"]
    if len(layer) == 0:
        problems.append("empty layer")

    ids = layer["linearid"].astype(str)
    if layer["linearid"].isna().any() or (ids == "").any():
        problems.append("null or empty linearid")
    duplicates = sorted(ids[ids.duplicated()].unique())
    if duplicates:
        problems.append(f"{len(duplicates)} duplicate linearid(s): {duplicates[:5]}")
    stray_classes = sorted(set(layer["mtfcc"].astype(str)) - set(MAJOR_ROAD_CLASSES))
    if stray_classes:
        problems.append(f"feature class(es) outside the major-road vocabulary: {stray_classes[:5]}")
    stray_types = sorted(set(layer["route_type"].astype(str)) - set(ROUTE_TYPES))
    if stray_types:
        problems.append(f"route type(s) outside the TIGER vocabulary: {stray_types[:5]}")

    declared = CRS.from_user_input(crs)
    if layer.crs is None or CRS.from_user_input(layer.crs) != declared:
        problems.append(f"CRS is {layer.crs!r}, expected {crs}")
        return problems
    geometry = layer.geometry
    empty = int((geometry.isna() | geometry.is_empty).sum())
    if empty:
        problems.append(f"{empty} null/empty geometr(ies)")
    present = geometry[~(geometry.isna() | geometry.is_empty)]
    stray = sorted(set(present.geom_type) - LINE_TYPES)
    if stray:
        problems.append(f"geometry type(s) {stray} outside {sorted(LINE_TYPES)}")
    invalid = int((~present.is_valid).sum())
    if invalid:
        problems.append(f"{invalid} invalid geometr(ies)")
    minx, miny, maxx, maxy = county_bounds(crs)
    bounds = present.bounds
    outside_bounds = present[
        (bounds["minx"] < minx)
        | (bounds["maxx"] > maxx)
        | (bounds["miny"] < miny)
        | (bounds["maxy"] > maxy)
    ]
    if len(outside_bounds):
        problems.append(
            f"{len(outside_bounds)} road(s) outside the county bounds: "
            f"{sorted(ids[outside_bounds.index])[:5]}"
        )
    if spine is not None and len(present):
        tracts = spine.geometry if spine.crs == layer.crs else spine.geometry.to_crs(layer.crs)
        union = tracts.union_all()
        apart = present[~present.intersects(union)]
        if len(apart):
            problems.append(
                f"{len(apart)} road(s) touching no tract of the spine: "
                f"{sorted(ids[apart.index])[:5]}"
            )
    return problems


def summarize(layer: gpd.GeoDataFrame, spine: gpd.GeoDataFrame, *, crs: str) -> dict[str, Any]:
    """The stage report: counts and lengths the handoff and the data card cite."""
    tracts = spine.geometry if spine.crs == layer.crs else spine.geometry.to_crs(layer.crs)
    union = tracts.union_all()
    by_class = layer["mtfcc"].astype(str).value_counts().sort_index()
    by_type = layer["route_type"].astype(str).value_counts().sort_index()
    return {
        "crs": crs,
        "rows": int(len(layer)),
        "by_mtfcc": {str(k): int(v) for k, v in by_class.items()},
        "by_route_type": {str(k): int(v) for k, v in by_type.items()},
        "unnamed": int(layer["name"].isna().sum()),
        "length_km": round(float(layer.length.sum()) / 1000.0, 3),
        "length_outside_tracts_m": round(float(layer.difference(union).length.sum()), 3),
    }


def _raw(ctx: StageContext, source: str) -> str:
    prefix = f"raw/{source}/"
    matches = [rel for rel in ctx.stage.inputs if rel.startswith(prefix)]
    if len(matches) != 1:
        raise StageError(f"stage {ctx.stage.name!r} declares {len(matches)} {source} snapshot(s)")
    return matches[0]


def basemap(ctx: StageContext) -> None:
    """The curated roads layer in the analysis CRS, invariants enforced against the spine."""
    crs = str(ctx.params["crs"])
    spine = gpd.read_parquet(ctx.input(SPINE))
    roads = adapters.tiger_roads.read(ctx.input(_raw(ctx, adapters.tiger_roads.SOURCE)))
    ctx.checkpoint()
    layer = build_roads(roads, crs)
    problems = check_roads(layer, crs=crs, spine=spine)
    if problems:
        raise StageError(
            f"basemap roads layer: {len(problems)} invariant violation(s): " + "; ".join(problems)
        )
    layer.to_parquet(ctx.output(ROADS), index=False)
    report = summarize(layer, spine, crs=crs)
    ctx.output(BASEMAP_REPORT).write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", "utf-8"
    )
