"""Contract harness proven on the tinycity fake sources (EP-3).

Positive: every raw source in the golden fixture satisfies its contract when
loaded the way an adapter would load it. Negative: every fault injected into the
committed invalid variant is caught, by the check kind the fault targets.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from phillysim.contracts import ANALYTIC_TABLE, check_frame, enforce
from phillysim.fixtures.tinycity import RAW_SOURCES, load_raw
from phillysim.fixtures.tinycity_contracts import CONTRACTS

SOURCES = sorted(RAW_SOURCES)


def test_every_raw_source_has_a_contract() -> None:
    assert set(CONTRACTS) == set(RAW_SOURCES)


@pytest.mark.parametrize("source", SOURCES)
def test_valid_source_conforms(tinycity_dir: Path, source: str) -> None:
    frame, manifest = load_raw(tinycity_dir, source)
    enforce(CONTRACTS[source], frame, manifest)


def test_manifests_record_file_digests(tinycity_dir: Path) -> None:
    import hashlib

    for source in SOURCES:
        base = tinycity_dir / "raw" / source / "2026-01-01"
        manifest = json.loads((base / "manifest.json").read_text("utf-8"))
        assert manifest["synthetic"] is True
        assert manifest["license_bucket"] in {"A", "B"}
        assert (base / manifest["terms_archive"]).is_file()
        for name, digest in manifest["files"].items():
            assert hashlib.sha256((base / name).read_bytes()).hexdigest() == digest, name


def test_golden_analytic_table_meets_the_locked_schema(tinycity_dir: Path) -> None:
    frame = pd.read_parquet(tinycity_dir / "expected" / "tract_metrics.parquet")
    enforce(ANALYTIC_TABLE, frame)


# --- negative: the committed invalid variant ------------------------------------------


def _injected(tinycity_invalid_dir: Path) -> list[dict[str, str]]:
    return json.loads((tinycity_invalid_dir / "fixture.json").read_text("utf-8"))["injected_faults"]


def test_invalid_variant_declares_faults(tinycity_invalid_dir: Path) -> None:
    faults = _injected(tinycity_invalid_dir)
    assert len(faults) >= 5
    assert {fault["check"] for fault in faults} == {"schema", "geometry", "license", "key", "rows"}


def test_every_injected_fault_is_caught(tinycity_invalid_dir: Path) -> None:
    faults = _injected(tinycity_invalid_dir)
    found: dict[str, set[str]] = {}
    for source in sorted({fault["source"] for fault in faults}):
        frame, manifest = load_raw(tinycity_invalid_dir, source)
        found[source] = {v.check for v in check_frame(CONTRACTS[source], frame, manifest)}
    for fault in faults:
        assert fault["check"] in found[fault["source"]], f"{fault['id']} not caught: {found}"


def test_untouched_sources_in_invalid_variant_still_conform(tinycity_invalid_dir: Path) -> None:
    broken = {fault["source"] for fault in _injected(tinycity_invalid_dir)}
    for source in SOURCES:
        if source not in broken:
            frame, manifest = load_raw(tinycity_invalid_dir, source)
            assert check_frame(CONTRACTS[source], frame, manifest) == [], source


def test_injected_schema_violation_on_the_fly(tinycity_dir: Path) -> None:
    """The brief's acceptance criterion, stated directly: drop a column, the harness fires."""
    frame, manifest = load_raw(tinycity_dir, "snap_retailers")
    violations = check_frame(
        CONTRACTS["snap_retailers"], frame.drop(columns=["store_type"]), manifest
    )
    assert [v.check for v in violations] == ["schema"]
    assert "store_type" in violations[0].detail
