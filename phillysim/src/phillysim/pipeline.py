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
GeoJSON + CSV, gated before install); later packets append the rest
(``destinations`` .. ``travel_times`` between ``snap_retailers`` and
``metrics`` at M3 / M4).

Snapshot IDs are pinned in :data:`SNAPSHOT_ID` rather than taken from the
clock, because a stage's outputs are static paths in the DAG. ``acquire``
downloads the pinned snapshot when it is absent and re-uses it, after
verifying it against its manifest, when it is already in the raw zone (so a
lost state file never re-downloads and never touches the immutable raw
zone). A controlled refresh (roadmap/sources.md) is a change to
:data:`SNAPSHOT_ID` recorded in the changelog: the new date acquires fresh
snapshots beside the old ones, which are never overwritten.
"""

from __future__ import annotations

import json
import shutil
import time
from dataclasses import replace
from typing import Any

import geopandas as gpd
import pandas as pd

from phillysim.adapters import ADAPTERS, cenpop, snap, tiger
from phillysim.adapters.base import COUNTY_BOUNDS
from phillysim.classify.store_format import MAPPING_VERSION
from phillysim.contracts import check_frame
from phillysim.destinations import SNAP_REPORT, SNAP_RETAILERS, snap_retailers
from phillysim.download import Acquisition, Opener, acquire_snapshot, urllib_open
from phillysim.manifest import SCHEMA_VERSION, read_manifest, verify_snapshot
from phillysim.metrics import slice as qa_slice
from phillysim.publish import bins, export
from phillysim.spine import ACS_TRACTS, ANALYSIS_CRS, SPINE, TRACT_COUNT, demographics, spine
from phillysim.stages import Pipeline, Stage, StageContext, StageError

PIPELINE_NAME = "real"
#: The pinned acquisition date of the current spine snapshots (see the module docstring).
SNAPSHOT_ID = "2026-09-02"

SOURCES: tuple[str, ...] = tuple(sorted(ADAPTERS))
RAW_SNAPSHOTS: tuple[str, ...] = tuple(f"raw/{source}/{SNAPSHOT_ID}" for source in SOURCES)
ACQUISITION = "intermediate/acquisition.json"
VALIDATION = "intermediate/validation.json"
#: The sources the public zone is derived from (its provenance and its license bucket): the
#: spine's geometry and centers, and the SNAP layer. ACS feeds nothing published until M5.
PUBLISH_SOURCES: tuple[str, ...] = tuple(sorted((cenpop.SOURCE, snap.SOURCE, tiger.SOURCE)))


def _raw(source: str) -> str:
    return f"raw/{source}/{SNAPSHOT_ID}"


# --- 1. acquire ------------------------------------------------------------------------------


def make_acquire(opener: Opener):
    """The ``acquire`` stage body bound to a transport (the default is the real one)."""

    def acquire(ctx: StageContext) -> None:
        """Acquire the pinned snapshot of every registered source through the guarded path,
        or re-use the verified snapshot already in the raw zone; write the acquisition
        report."""
        quarantine_zone = ctx.root / "quarantine"
        report: dict[str, Any] = {"snapshot_id": SNAPSHOT_ID, "sources": {}}
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
                        f"{source}/{SNAPSHOT_ID} is in the raw zone but fails verification "
                        f"({problems}); the raw zone is immutable, so it will not be replaced: "
                        "move it aside and run again"
                    )
                shutil.copytree(existing, target)
                acquisition = Acquisition(
                    read_manifest(existing), (), time.perf_counter() - started, reused=True
                )
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                spec = replace(
                    adapter.spec,
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
    supermarket-format points the metric was computed against, per-file license labels
    derived from the three sources' manifests, gated before the runner installs it."""
    metrics = pd.read_parquet(ctx.input(qa_slice.TRACT_METRICS))
    spine_frame = gpd.read_parquet(ctx.input(SPINE))
    layer = gpd.read_parquet(ctx.input(SNAP_RETAILERS))
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
    )


# --- the pipeline -------------------------------------------------------------------------------


def real_pipeline(opener: Opener = urllib_open) -> Pipeline:
    """The real stages registered so far, wired over the pinned snapshot paths.

    ``opener`` is the transport ``acquire`` uses; the CLI passes nothing (the real
    https path), the test suite passes a fake that serves the committed samples.
    """
    return Pipeline(
        PIPELINE_NAME,
        [
            Stage(
                "acquire",
                make_acquire(opener),
                outputs=(*RAW_SNAPSHOTS, ACQUISITION),
                # The source set and snapshot ID are parameters so that registering a new
                # source (EP-6 added snap_retailers) or a controlled refresh changes the
                # fingerprint and re-runs the stage, which re-uses every existing snapshot.
                params={
                    "timeout_s": 60,
                    "attempts": 3,
                    "snapshot_id": SNAPSHOT_ID,
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
                description="public zone: license-labeled, binned, escaped GeoJSON + CSV, "
                "gated before install",
            ),
        ],
    )
