"""EP-5a integration: the real pipeline's ``acquire`` and ``validate`` stages, offline.

A fake transport serves the committed spine samples under the adapters' real
URLs, so the stages run exactly as they do against the Census hosts (allowlist,
caps, archive guards, terms check, manifest, admission) without a network. The
suite-wide socket guard in ``conftest.py`` would fail any test that tried.
"""

from __future__ import annotations

import io
import json
from collections import Counter
from pathlib import Path

import pytest
from typer.testing import CliRunner

from phillysim import pipeline, runner
from phillysim.adapters import ADAPTERS
from phillysim.cli import app
from phillysim.fixtures.pipeline import fixture_pipeline
from phillysim.pipeline import ACQUISITION, RAW_SNAPSHOTS, SNAPSHOT_ID, VALIDATION, real_pipeline
from phillysim.quarantine import list_quarantined
from phillysim.runner import StateError
from phillysim.stages import StageError


class SampleTransport:
    """Serves each adapter's URLs from the committed samples; counts every call."""

    def __init__(self, samples: Path, *, terms: bytes | None = None) -> None:
        self.routes: dict[str, bytes] = {}
        self.calls: list[str] = []
        for source, adapter in ADAPTERS.items():
            sample = samples / "raw" / source / SNAPSHOT_ID
            for fetch in adapter.spec.files:
                self.routes[fetch.url] = (sample / fetch.file_name).read_bytes()
            page = (sample / adapter.spec.terms.file_name).read_bytes()
            self.routes[adapter.spec.terms.url] = page if terms is None else terms

    def __call__(self, url: str, allowlist, timeout: float):
        self.calls.append(url)
        data = self.routes[url]
        return _Response(data)


class _Response:
    def __init__(self, data: bytes) -> None:
        self._buffer = io.BytesIO(data)
        self.status = 200
        self.headers = {"Content-Length": str(len(data))}

    def read(self, size: int = -1) -> bytes:
        return self._buffer.read(size)

    def close(self) -> None:
        pass


@pytest.fixture
def root(tmp_path: Path) -> Path:
    return tmp_path / "data"


def test_acquire_and_validate_end_to_end(root: Path, spine_samples_dir: Path) -> None:
    transport = SampleTransport(spine_samples_dir)
    lines: list[str] = []
    report = runner.run(root, real_pipeline(opener=transport), echo=lines.append)
    assert report.ran == ["acquire", "validate"] and report.skipped == []
    expected_calls = Counter(
        fetch.url for adapter in ADAPTERS.values() for fetch in adapter.spec.files
    )
    expected_calls.update(adapter.spec.terms.url for adapter in ADAPTERS.values())
    assert Counter(transport.calls) == expected_calls, "each file once, the terms page per source"

    for rel in RAW_SNAPSHOTS:
        snapshot = root / rel
        manifest = json.loads((snapshot / "manifest.json").read_text("utf-8"))
        assert manifest["terms_archive"] == "terms.html" and (snapshot / "terms.html").is_file()
        assert manifest["license_bucket"] == "A" and manifest["license_note"]
        assert manifest["synthetic"] is False
        assert manifest["terms_archive"] in manifest["files"]
    acquisition = json.loads((root / ACQUISITION).read_text("utf-8"))
    assert acquisition["snapshot_id"] == SNAPSHOT_ID
    for source, entry in acquisition["sources"].items():
        assert entry["reused"] is False and entry["bytes"] > 0 and entry["fetches"]
        assert entry["filter"] == ADAPTERS[source].filter_note
        assert entry["limits"]["max_file_bytes"] == ADAPTERS[source].spec.limits.max_file_bytes
    validation = json.loads((root / VALIDATION).read_text("utf-8"))
    assert set(validation) == set(pipeline.SOURCES)
    assert all(v["rows"] == 6 and v["violations"] == [] for v in validation.values())
    assert not any((root / "quarantine").iterdir())

    verify = CliRunner().invoke(app, ["verify", "--data-root", str(root)])
    assert verify.exit_code == 0, verify.output
    assert "3 of 3 snapshot(s) verified" in verify.output
    assert "pipeline 'real'" in verify.output and "2 of 2 stage(s) done and intact" in verify.output
    status = CliRunner().invoke(app, ["status", "--data-root", str(root)])
    assert status.exit_code == 0 and "2 fresh, 0 stale, 0 missing, 0 incomplete" in status.output

    calls_before = len(transport.calls)
    second = runner.run(root, real_pipeline(opener=transport))
    assert second.ran == [] and second.skipped == ["acquire", "validate"]
    assert len(transport.calls) == calls_before, "a fresh run opens no connection"


def test_existing_snapshots_are_reused_never_refetched(root: Path, spine_samples_dir: Path):
    transport = SampleTransport(spine_samples_dir)
    runner.run(root, real_pipeline(opener=transport))
    calls = len(transport.calls)
    (root / runner.STATE_FILE).unlink()  # the state file is lost; the raw zone is not
    report = runner.run(root, real_pipeline(opener=transport))
    assert report.ran == ["acquire", "validate"]
    assert len(transport.calls) == calls, "verified snapshots in the raw zone are re-used"
    acquisition = json.loads((root / ACQUISITION).read_text("utf-8"))
    assert all(entry["reused"] is True for entry in acquisition["sources"].values())
    assert CliRunner().invoke(app, ["verify", "--data-root", str(root)]).exit_code == 0


def test_tampered_existing_snapshot_is_refused_not_replaced(root: Path, spine_samples_dir: Path):
    transport = SampleTransport(spine_samples_dir)
    runner.run(root, real_pipeline(opener=transport))
    target = root / "raw" / "cenpop" / SNAPSHOT_ID / "CenPop2020_Mean_TR42.txt"
    target.write_bytes(target.read_bytes() + b"tampered\n")
    (root / runner.STATE_FILE).unlink()
    with pytest.raises(StageError, match="fails verification"):
        runner.run(root, real_pipeline(opener=transport))
    assert target.read_bytes().endswith(b"tampered\n"), "the raw zone is never rewritten"
    verify = CliRunner().invoke(app, ["verify", "--data-root", str(root)])
    assert verify.exit_code == 1 and "FAIL cenpop/2026-09-02" in verify.output


def test_terms_drift_stops_acquisition_and_quarantines(root: Path, spine_samples_dir: Path):
    transport = SampleTransport(spine_samples_dir, terms=b"<html>The terms have changed.</html>")
    with pytest.raises(StageError, match="quarantined \\(terms\\)"):
        runner.run(root, real_pipeline(opener=transport))
    records = list_quarantined(root / "quarantine")
    assert len(records) == 1 and records[0].kind == "terms" and records[0].source == "acs"
    assert "freely available" in records[0].reason
    assert not (root / "raw").exists() or not any((root / "raw").iterdir())
    verify = CliRunner().invoke(app, ["verify", "--data-root", str(root)])
    assert verify.exit_code == 1, verify.output
    assert "0 of 0 snapshot(s) verified" in verify.output
    assert "0 of 2 stage(s) done and intact; incomplete: acquire" in verify.output
    assert "quarantined (terms)" in verify.output
    status = CliRunner().invoke(app, ["status", "--data-root", str(root)])
    assert "incomplete acquire" in status.output


def test_real_and_fixture_state_files_never_mix(root: Path, spine_samples_dir: Path) -> None:
    runner.run(root, real_pipeline(opener=SampleTransport(spine_samples_dir)))
    with pytest.raises(StateError, match="belongs to pipeline 'real'"):
        runner.run(root, fixture_pipeline())
    assert real_pipeline().names == fixture_pipeline().names[:2]
