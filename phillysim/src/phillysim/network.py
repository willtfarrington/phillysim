"""The routing inputs: the clipped street network and the unwrapped transit feeds (EP-12).

The real pipeline's ``network`` stage (architecture.md stage 8) reads the two
routing snapshots through their adapters and writes ``intermediate/network/``:
the OpenStreetMap extract clipped to the routing box (the county bounds
buffered by ``buffer_m`` in the analysis CRS, expressed in WGS 84; ADR-0007,
ADR-0008) by :func:`phillysim.adapters.osm.clip`, way-complete, checked by
:func:`phillysim.adapters.osm.check_clip` on its own output like every layer
stage checks its invariants; and SEPTA's two feed zips copied out of the
release asset as files by :func:`phillysim.adapters.septa_gtfs.unwrap`,
never expanded. ``intermediate/network.json`` records the counts: nodes,
ways, highway ways, relations, and bytes of the clip; stops per feed, how
many lie outside the routing box and how many inside the county's tracts;
the license bucket the directory carries by derivation (Bucket B: the clip
is OSM-derived, ADR-0003). No routing runs here; the JVM, the toolchain, and
the smoke route on this output are EP-13's.

The raw zone is never written beside: the clip and the feed zips land in the
intermediate zone, and the stage's provenance is the two snapshots it names
as inputs.
"""

from __future__ import annotations

import json
from typing import Any

import geopandas as gpd

from phillysim.adapters import osm, septa_gtfs
from phillysim.adapters.base import COUNTY_BOUNDS, WGS84, buffered_bounds
from phillysim.manifest import read_manifest
from phillysim.publish.bucket import derive_bucket
from phillysim.spine import ANALYSIS_CRS, SPINE
from phillysim.stages import StageContext, StageError

NETWORK_DIR = "intermediate/network"
NETWORK_REPORT = "intermediate/network.json"

Box = tuple[float, float, float, float]


def routing_box(buffer_m: float, crs: str = ANALYSIS_CRS) -> Box:
    """The routing extent in WGS 84 (minlon, minlat, maxlon, maxlat): the county bounds
    buffered by ``buffer_m`` metres in the metric ``crs``."""
    return buffered_bounds(COUNTY_BOUNDS, buffer_m, crs)


def _raw(ctx: StageContext, source: str) -> str:
    prefix = f"raw/{source}/"
    matches = [rel for rel in ctx.stage.inputs if rel.startswith(prefix)]
    if len(matches) != 1:
        raise StageError(f"stage {ctx.stage.name!r} declares {len(matches)} {source} snapshot(s)")
    return matches[0]


def stops_summary(stops, box: Box, spine: gpd.GeoDataFrame) -> dict[str, int]:
    """Stop counts for one feed: all, outside the routing box, inside the spine's tracts."""
    points = gpd.GeoDataFrame(
        geometry=gpd.points_from_xy(stops["stop_lon"], stops["stop_lat"]), crs=WGS84
    ).to_crs(spine.crs)
    union = spine.geometry.union_all()
    return {
        "stops": int(len(stops)),
        "stops_outside_box": septa_gtfs.outside_box(stops, box),
        "stops_in_county_tracts": int(points.within(union).sum()),
    }


def network(ctx: StageContext) -> None:
    """Clip the street network to the routing box and unwrap the transit feeds; record
    the counts. Fails on any clip-contract violation."""
    buffer_m = float(ctx.params["buffer_m"])
    crs = str(ctx.params["crs"])
    node_band = osm.band(ctx.params["node_band"])
    way_band = osm.band(ctx.params["way_band"])
    box = routing_box(buffer_m, crs)
    spine = gpd.read_parquet(ctx.input(SPINE))
    osm_rel, gtfs_rel = _raw(ctx, osm.SOURCE), _raw(ctx, septa_gtfs.SOURCE)
    osm_snapshot, gtfs_snapshot = ctx.input(osm_rel), ctx.input(gtfs_rel)
    out_dir = ctx.output(NETWORK_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)

    clip_report = osm.clip(
        osm_snapshot / osm.FILE_NAME, out_dir / osm.clip_file_name(buffer_m), box
    )
    ctx.checkpoint()
    problems = osm.check_clip(
        out_dir / clip_report.file_name, box, node_band=node_band, way_band=way_band
    )
    if problems:
        raise StageError(
            f"clipped network: {len(problems)} contract violation(s): " + "; ".join(problems)
        )
    feeds = septa_gtfs.unwrap(gtfs_snapshot, out_dir)
    ctx.checkpoint()
    gtfs_report: dict[str, Any] = {}
    for feed in septa_gtfs.FEEDS:
        stops = septa_gtfs.read_stops(gtfs_snapshot, feed)
        gtfs_report[feed] = {
            "label": septa_gtfs.FEED_LABELS[feed],
            "bytes": feeds[feed],
            **stops_summary(stops, box, spine),
        }
    buckets = [
        read_manifest(osm_snapshot).license_bucket,
        read_manifest(gtfs_snapshot).license_bucket,
    ]
    report = {
        "crs": crs,
        "buffer_m": buffer_m,
        "box": list(box),
        "license_bucket": derive_bucket(buckets),
        "sources": {osm.SOURCE: osm_rel, septa_gtfs.SOURCE: gtfs_rel},
        "osm": clip_report.to_dict(),
        "gtfs": gtfs_report,
        "files": sorted(p.name for p in out_dir.iterdir()),
    }
    ctx.output(NETWORK_REPORT).write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", "utf-8"
    )
