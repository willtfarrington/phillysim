"""The real pipeline: the stages that run on the real data root (EP-5a onward).

Same stage names, zones, and output paths as the fixture pipeline
(:mod:`phillysim.fixtures.pipeline`), so architecture.md's stage table
describes both; different stage bodies, a different pipeline name (``real``),
and a different data root (``<data root>/`` versus ``<data root>/fixture/``).
The two never meet: the runner's state file records its pipeline's name and
refuses the other one, and the CLI picks the pipeline and the root together
from ``--fixture``.

EP-5a registers ``acquire`` and ``validate`` for the three spine sources;
EP-5b adds ``spine`` and ``demographics`` (bodies in :mod:`phillysim.spine`,
which also holds the geospatial invariants and the analysis CRS); EP-6 adds
the ``snap_retailers`` source to ``acquire`` / ``validate`` and the
``snap_retailers`` stage (body in :mod:`phillysim.destinations`), the first
per-source destination layer, which the fixture pipeline has no counterpart
for (its ``destinations`` stage reads its fake sources directly); EP-7 adds
``metrics`` (body in :mod:`phillysim.metrics.slice`: the QA-only straight-line
slice metric, the analytic table's first real instance) and ``publish`` (the
public zone through :mod:`phillysim.publish`: license-labeled, binned, escaped
GeoJSON + CSV, gated before install); EP-8b adds the ``tiger_roads`` source
and the ``basemap`` stage (body in :mod:`phillysim.basemap`: the major roads
in the analysis CRS) and publishes the basemap file beside the rest (public
schema version 2); EP-12 adds the two routing sources (``osm_network``, the
first Bucket B source of the real pipeline, and ``gtfs``) and the ``network``
stage (body in :mod:`phillysim.network`: the clipped street network and the
unwrapped feeds, no JVM); EP-15 adds ``travel_times`` on the M3 go verdict (body in
:mod:`phillysim.routing.stage`: the spike's two core runs as a night under the harness,
concatenated in the dictionary's shape, Bucket B by derivation); M4 appends
``destinations`` .. ``hours`` between ``snap_retailers`` and ``network``.

Snapshot IDs are pinned **per source** in :data:`SNAPSHOT_IDS` (ADR-0006,
ADR-0008) rather than taken from the clock, because a stage's outputs are
static paths in the DAG; a source acquired later takes its own acquisition
date, and the sources already in the raw zone keep theirs. ``acquire``
downloads a pinned snapshot when it is absent and re-uses it, after
verifying it against its manifest, when it is already in the raw zone (so a
lost state file never re-downloads and never touches the immutable raw
zone). A controlled refresh (roadmap/sources.md) is a change to one source's
entry in :data:`SNAPSHOT_IDS` recorded in the changelog: the new date
acquires a fresh snapshot beside the old one, which is never overwritten.
"""

from __future__ import annotations

import json
import shutil
import time
from collections.abc import Callable, Mapping
from dataclasses import replace
from typing import Any

import geopandas as gpd
import pandas as pd

from phillysim.adapters import ADAPTERS, acs, cenpop, osm, septa_gtfs, snap, tiger, tiger_roads
from phillysim.adapters.base import COUNTY_BOUNDS, COUNTY_NAME, ROUTING_BUFFER_M
from phillysim.basemap import BASEMAP_REPORT, ROADS, basemap
from phillysim.classify.store_format import MAPPING_VERSION
from phillysim.contracts import check_frame
from phillysim.destinations import SNAP_REPORT, SNAP_RETAILERS, snap_retailers
from phillysim.download import Acquisition, Opener, acquire_snapshot, urllib_open
from phillysim.manifest import SCHEMA_VERSION, read_manifest, verify_snapshot
from phillysim.metrics import slice as qa_slice
from phillysim.network import NETWORK_DIR, NETWORK_REPORT, network
from phillysim.publish import bins, export
from phillysim.routing import stage as routing_stage
from phillysim.routing.records import RunRecord
from phillysim.routing.toolchain import Toolchain, ToolchainReport
from phillysim.spine import ACS_TRACTS, ANALYSIS_CRS, SPINE, TRACT_COUNT, demographics, spine
from phillysim.stages import Pipeline, Stage, StageContext, StageError

PIPELINE_NAME = "real"
#: The pinned snapshot ID (acquisition date) of every registered source (see the module
#: docstring): the five sources of EP-5a to EP-8b, acquired 2026-09-02, and the two
#: routing sources of EP-12, acquired 2026-09-03.
SNAPSHOT_IDS: dict[str, str] = {
    acs.SOURCE: "2026-09-02",
    cenpop.SOURCE: "2026-09-02",
    snap.SOURCE: "2026-09-02",
    tiger.SOURCE: "2026-09-02",
    tiger_roads.SOURCE: "2026-09-02",
    osm.SOURCE: "2026-09-03",
    septa_gtfs.SOURCE: "2026-09-03",
}

SOURCES: tuple[str, ...] = tuple(sorted(ADAPTERS))
if set(SNAPSHOT_IDS) != set(SOURCES):
    raise RuntimeError(
        f"SNAPSHOT_IDS names {sorted(SNAPSHOT_IDS)} but the registry has {list(SOURCES)}"
    )
ACQUISITION = "intermediate/acquisition.json"
VALIDATION = "intermediate/validation.json"
#: The sources the public zone is derived from (its provenance and its license bucket): the
#: spine's geometry and centers, the SNAP layer, and the basemap's roads (EP-8b). ACS feeds
#: nothing published until M5.
PUBLISH_SOURCES: tuple[str, ...] = tuple(
    sorted((cenpop.SOURCE, snap.SOURCE, tiger.SOURCE, tiger_roads.SOURCE))
)


def _raw(source: str) -> str:
    return f"raw/{source}/{SNAPSHOT_IDS[source]}"


RAW_SNAPSHOTS: tuple[str, ...] = tuple(_raw(source) for source in SOURCES)

#: ``{source: {file name: "<algorithm>:<hex>"}}``: pinned digests that override the
#: adapters' own (the test suite pins the committed samples' digests this way).
Pins = Mapping[str, Mapping[str, str]]


def _pinned(spec, pins: Pins | None):
    if not pins or spec.source not in pins:
        return spec
    overrides = pins[spec.source]
    files = tuple(
        replace(fetch, digest=overrides[fetch.file_name]) if fetch.file_name in overrides else fetch
        for fetch in spec.files
    )
    return replace(spec, files=files)


# --- 1. acquire ------------------------------------------------------------------------------


def make_acquire(opener: Opener, pins: Pins | None = None):
    """The ``acquire`` stage body bound to a transport (the default is the real one) and,
    optionally, to pinned digests overriding the adapters' (see :data:`Pins`)."""

    def acquire(ctx: StageContext) -> None:
        """Acquire the pinned snapshot of every registered source through the guarded path,
        or re-use the verified snapshot already in the raw zone; write the acquisition
        report."""
        quarantine_zone = ctx.root / "quarantine"
        report: dict[str, Any] = {"snapshot_ids": dict(sorted(SNAPSHOT_IDS.items())), "sources": {}}
        for source in SOURCES:
            ctx.checkpoint()
            adapter = ADAPTERS[source]
            target = ctx.output(_raw(source))
            existing = ctx.root / _raw(source)
            started = time.perf_counter()
            if existing.is_dir():
                verdict = verify_snapshot(existing)
                if not verdict.ok:
                    problems = "; ".join(str(p) for p in verdict.problems)
                    raise StageError(
                        f"{source}/{SNAPSHOT_IDS[source]} is in the raw zone but fails "
                        f"verification ({problems}); the raw zone is immutable, so it will not "
                        "be replaced: move it aside and run again"
                    )
                shutil.copytree(existing, target)
                acquisition = Acquisition(
                    read_manifest(existing), (), time.perf_counter() - started, reused=True
                )
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                spec = replace(
                    _pinned(adapter.spec, pins),
                    timeout=float(ctx.params["timeout_s"]),
                    attempts=int(ctx.params["attempts"]),
                )
                acquisition = acquire_snapshot(
                    spec, target, quarantine_zone=quarantine_zone, opener=opener
                )
            entry = acquisition.to_dict()
            entry["filter"] = adapter.filter_note
            entry["limits"] = {
                "max_file_bytes": adapter.spec.limits.max_file_bytes,
                "max_extracted_bytes": adapter.spec.limits.max_extracted_bytes,
                "max_compression_ratio": adapter.spec.limits.max_compression_ratio,
                "max_members": adapter.spec.limits.max_members,
            }
            report["sources"][source] = entry
        ctx.output(ACQUISITION).write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", "utf-8"
        )

    return acquire


# --- 2. validate -------------------------------------------------------------------------------


def validate(ctx: StageContext) -> None:
    """Read every admitted snapshot through its adapter (county filter applied) and check
    it against its contract; any violation fails the stage."""
    report: dict[str, Any] = {}
    failures: list[str] = []
    for source in SOURCES:
        ctx.checkpoint()
        adapter = ADAPTERS[source]
        snapshot = ctx.input(_raw(source))
        manifest = read_manifest(snapshot).to_dict()
        frame = adapter.read(snapshot)
        violations = check_frame(adapter.contract, frame, manifest)
        nulls = {
            column: int(frame[column].isna().sum())
            for column in adapter.contract.column_names()
            if column in frame.columns and int(frame[column].isna().sum())
        }
        report[source] = {
            "snapshot_id": manifest["snapshot_id"],
            "license_bucket": manifest["license_bucket"],
            "schema_version": manifest["schema_version"],
            "rows": int(len(frame)),
            "nulls": nulls,
            "violations": [str(v) for v in violations],
        }
        failures.extend(str(v) for v in violations)
    ctx.output(VALIDATION).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", "utf-8")
    if failures:
        raise StageError(f"{len(failures)} contract violation(s): " + "; ".join(failures))


# --- 11. publish ------------------------------------------------------------------------------


def publish(ctx: StageContext) -> None:
    """The public zone (EP-7): the tracts with the QA slice metric and its bins, the
    supermarket-format points the metric was computed against, the basemap (EP-8b: the
    county boundary dissolved from the spine and the curated major roads), per-file
    license labels derived from the sources' manifests, gated before the runner installs
    it."""
    metrics = pd.read_parquet(ctx.input(qa_slice.TRACT_METRICS))
    spine_frame = gpd.read_parquet(ctx.input(SPINE))
    layer = gpd.read_parquet(ctx.input(SNAP_RETAILERS))
    roads = gpd.read_parquet(ctx.input(ROADS))
    ctx.checkpoint()
    chosen = layer[layer["supermarket_format"].astype(bool)]
    sites = gpd.GeoDataFrame(
        {
            "site_id": chosen["site_id"].astype(str).to_numpy(),
            "source": chosen["source"].astype(str).to_numpy(),
            "category": qa_slice.CATEGORY,
            "name": chosen["name"].astype(str).to_numpy(),
            "geoid": chosen["geoid"].astype("string").to_numpy(),
        },
        geometry=chosen.geometry.to_numpy(),
        crs=layer.crs,
    )
    export.publish_zone(
        ctx,
        pipeline=PIPELINE_NAME,
        metrics=metrics,
        spine=spine_frame,
        sites=sites,
        raw_snapshots={source: _raw(source) for source in PUBLISH_SOURCES},
        citations={source: ADAPTERS[source].citation for source in PUBLISH_SOURCES},
        descriptions=qa_slice.DESCRIPTIONS,
        boundary_name=COUNTY_NAME,
        roads=roads,
    )


# --- the pipeline -------------------------------------------------------------------------------


def real_pipeline(
    opener: Opener = urllib_open,
    pins: Pins | None = None,
    *,
    routing_runner: Callable[..., RunRecord] | None = None,
    toolchain: Toolchain | None = None,
    routing_check: Callable[[Toolchain], ToolchainReport] | None = None,
) -> Pipeline:
    """The real stages registered so far, wired over the pinned snapshot paths.

    ``opener`` is the transport ``acquire`` uses; the CLI passes nothing (the real
    https path), the test suite passes a fake that serves the committed samples and
    ``pins`` the samples' digests over the adapters' pinned ones. ``routing_runner`` and
    ``toolchain`` bind the ``travel_times`` stage (EP-15): the CLI passes nothing (the
    harness child on the project-local toolchain), the suite a scripted child, a crafted
    toolchain record, and ``routing_check`` accepting it, so no JVM runs in the suite.
    """
    routing_plan = routing_stage.stage_plan()
    return Pipeline(
        PIPELINE_NAME,
        [
            Stage(
                "acquire",
                make_acquire(opener, pins),
                outputs=(*RAW_SNAPSHOTS, ACQUISITION),
                # The source set and the per-source snapshot IDs are parameters so that
                # registering a new source (EP-6 added snap_retailers; EP-12 the routing
                # sources) or a controlled refresh changes the fingerprint and re-runs the
                # stage, which re-uses every existing snapshot and fetches only the new ones.
                params={
                    "timeout_s": 60,
                    "attempts": 3,
                    "snapshot_ids": dict(sorted(SNAPSHOT_IDS.items())),
                    "sources": list(SOURCES),
                },
                description="acquire the pinned snapshots through the guarded path",
            ),
            Stage(
                "validate",
                validate,
                inputs=RAW_SNAPSHOTS,
                outputs=(VALIDATION,),
                params={"schema_version": SCHEMA_VERSION},
                description="check every source against its contract",
            ),
            Stage(
                "spine",
                spine,
                inputs=(_raw("tiger_tracts"), _raw("cenpop"), VALIDATION),
                outputs=(SPINE,),
                params={"crs": ANALYSIS_CRS, "expected_tracts": TRACT_COUNT},
                description="curated tract spine: geometry in the analysis CRS, "
                "CenPop population and centers, invariants enforced",
            ),
            Stage(
                "demographics",
                demographics,
                inputs=(SPINE, _raw("acs")),
                outputs=(ACS_TRACTS,),
                params={"schema_version": SCHEMA_VERSION},
                description="ACS estimates and margins of error joined one-to-one to the spine",
            ),
            Stage(
                "snap_retailers",
                snap_retailers,
                inputs=(SPINE, _raw(snap.SOURCE), VALIDATION),
                outputs=(SNAP_RETAILERS, SNAP_REPORT),
                params={
                    "crs": ANALYSIS_CRS,
                    "mapping_version": MAPPING_VERSION,
                    "as_of": snap.AS_OF,
                },
                description="SNAP retailer point layer: store-format classification, tract "
                "assignment, stable site IDs, invariants enforced",
            ),
            Stage(
                "basemap",
                basemap,
                inputs=(SPINE, _raw(tiger_roads.SOURCE), VALIDATION),
                outputs=(ROADS, BASEMAP_REPORT),
                params={
                    "crs": ANALYSIS_CRS,
                    "road_classes": sorted(tiger_roads.MAJOR_ROAD_CLASSES),
                },
                description="basemap roads layer: TIGER primary and secondary roads in the "
                "analysis CRS, invariants enforced against the spine",
            ),
            Stage(
                "network",
                network,
                inputs=(SPINE, _raw(osm.SOURCE), _raw(septa_gtfs.SOURCE), VALIDATION),
                outputs=(NETWORK_DIR, NETWORK_REPORT),
                # The extent is a parameter so a change of buffer or CRS re-runs the clip;
                # the bands are the clip's contract (the CI sample overrides them).
                params={
                    "buffer_m": ROUTING_BUFFER_M,
                    "crs": ANALYSIS_CRS,
                    "node_band": list(osm.CLIP_NODE_BAND),
                    "way_band": list(osm.CLIP_WAY_BAND),
                },
                description="routing inputs: the OSM extract clipped to the county bounds "
                "+ 5 km (way-complete, Bucket B by derivation) and SEPTA's two GTFS zips "
                "unwrapped as files; no JVM",
            ),
            Stage(
                "travel_times",
                routing_stage.make_travel_times(
                    toolchain=toolchain,
                    **({"runner": routing_runner} if routing_runner is not None else {}),
                    **({"check": routing_check} if routing_check is not None else {}),
                ),
                inputs=(SPINE, SNAP_RETAILERS, NETWORK_DIR, NETWORK_REPORT),
                outputs=(routing_stage.TRAVEL_TIMES, routing_stage.TRAVEL_TIMES_REPORT),
                # The plan's digest and every run's parameters are the methods axis
                # (ADR-0006): a parameter change, like a refreshed input, re-runs routing
                # (an unattended night). The table sizes are overridable for the samples.
                params=routing_stage.stage_params(routing_plan),
                description="travel-time matrices (EP-15): the M3 spike's two core runs "
                "(walk 4.8 km/h; walk+transit 4.8 km/h over the pinned Wednesday's "
                "08:00-20:00 window) routed by R5 in a sampled child per run as a night "
                "under runs/routing/, concatenated in the dictionary's shape, censored at "
                "120 min; Bucket B by derivation; never published before M5",
            ),
            Stage(
                "metrics",
                qa_slice.metrics,
                inputs=(SPINE, SNAP_RETAILERS),
                outputs=(qa_slice.TRACT_METRICS, qa_slice.SLICE_REPORT),
                params={
                    "crs": ANALYSIS_CRS,
                    "category": qa_slice.CATEGORY,
                    "methods_version": qa_slice.METHODS_VERSION,
                    "schema_version": SCHEMA_VERSION,
                },
                description="analytic table (EP-7 body: the QA-only straight-line slice "
                "metric to the nearest supermarket-format retailer; real metrics at M5)",
            ),
            Stage(
                "publish",
                publish,
                inputs=(
                    qa_slice.TRACT_METRICS,
                    SPINE,
                    SNAP_RETAILERS,
                    ROADS,
                    *(_raw(source) for source in PUBLISH_SOURCES),
                ),
                outputs=(export.PUBLIC_ZONE,),
                params={
                    "public_schema_version": export.PUBLIC_SCHEMA_VERSION,
                    "bounds": list(COUNTY_BOUNDS),
                    "coordinate_decimals": export.COORDINATE_DECIMALS,
                    "bin_classes": bins.BIN_CLASSES,
                    "bin_method": bins.BIN_METHOD,
                },
                description="public zone: license-labeled, binned, escaped GeoJSON + CSV "
                "with the basemap, gated before install",
            ),
        ],
    )
