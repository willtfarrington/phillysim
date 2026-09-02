"""The real pipeline: the stages that run on the real data root (EP-5a onward).

Same stage names, zones, and output paths as the fixture pipeline
(:mod:`phillysim.fixtures.pipeline`), so architecture.md's stage table
describes both; different stage bodies, a different pipeline name (``real``),
and a different data root (``<data root>/`` versus ``<data root>/fixture/``).
The two never meet: the runner's state file records its pipeline's name and
refuses the other one, and the CLI picks the pipeline and the root together
from ``--fixture``.

EP-5a registers ``acquire`` and ``validate`` for the three spine sources;
EP-5b adds ``spine`` and ``demographics``; later packets append the rest.

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

from phillysim.adapters import ADAPTERS
from phillysim.contracts import check_frame
from phillysim.download import Acquisition, Opener, acquire_snapshot, urllib_open
from phillysim.manifest import SCHEMA_VERSION, read_manifest, verify_snapshot
from phillysim.stages import Pipeline, Stage, StageContext, StageError

PIPELINE_NAME = "real"
#: The pinned acquisition date of the current spine snapshots (see the module docstring).
SNAPSHOT_ID = "2026-09-02"

SOURCES: tuple[str, ...] = tuple(sorted(ADAPTERS))
RAW_SNAPSHOTS: tuple[str, ...] = tuple(f"raw/{source}/{SNAPSHOT_ID}" for source in SOURCES)
ACQUISITION = "intermediate/acquisition.json"
VALIDATION = "intermediate/validation.json"


def _raw(source: str) -> str:
    return f"raw/{source}/{SNAPSHOT_ID}"


# --- 1. acquire ------------------------------------------------------------------------------


def make_acquire(opener: Opener):
    """The ``acquire`` stage body bound to a transport (the default is the real one)."""

    def acquire(ctx: StageContext) -> None:
        """Acquire the pinned snapshot of every spine source through the guarded path, or
        re-use the verified snapshot already in the raw zone; write the acquisition report."""
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
    """Read every admitted spine snapshot through its adapter (county filter applied) and
    check it against its contract; any violation fails the stage."""
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
                params={"timeout_s": 60, "attempts": 3},
                description="acquire the pinned spine snapshots through the guarded path",
            ),
            Stage(
                "validate",
                validate,
                inputs=RAW_SNAPSHOTS,
                outputs=(VALIDATION,),
                params={"schema_version": SCHEMA_VERSION},
                description="check every spine source against its contract",
            ),
        ],
    )
