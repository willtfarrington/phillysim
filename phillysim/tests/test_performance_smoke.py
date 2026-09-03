"""EP-13: the CI performance smoke (roadmap/quality.md "Performance smoke").

``phillysim run --fixture`` runs as a child process under the same process-tree RSS
sampler the routing harness uses; the wall clock and the peak RSS are asserted against
generous bounds (60 s, 2 GiB) and written to the test log. The point is that the
measurement exists and the machinery runs on both CI platforms; CI never runs the JVM,
and the fixture's ``network`` / ``travel_times`` stages stay stubs (owner decision at
EP-11).
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import psutil

from phillysim.routing.sampler import Sampler

WALL_BOUND_SECONDS = 60.0
RSS_BOUND_BYTES = 2 * 1024**3


def test_fixture_pipeline_under_the_sampler(tmp_path: Path, record_property, capsys) -> None:
    root = tmp_path / "fixture-root"
    command = [sys.executable, "-m", "phillysim.cli", "run", "--fixture", "--data-root", str(root)]
    started = time.perf_counter()
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    sampler = Sampler.for_process(
        psutil.Process(process.pid), interval=0.1, startup_interval=0.1, startup_seconds=0.0
    )
    sampler.start()
    output, _ = process.communicate(timeout=WALL_BOUND_SECONDS * 3)
    wall = time.perf_counter() - started
    sampler.join(timeout=10)
    result = sampler.result
    assert process.returncode == 0, output
    assert "stage(s) ran" in output
    assert not result.killed and result.samples, result.to_dict()
    assert wall < WALL_BOUND_SECONDS, f"fixture run took {wall:.1f} s"
    assert result.peak_bytes < RSS_BOUND_BYTES, f"peak RSS {result.peak_bytes} bytes"
    numbers = {
        "wall_seconds": round(wall, 2),
        "peak_rss_bytes": result.peak_bytes,
        "peak_rss_mib": round(result.peak_bytes / 1024**2, 1),
        "samples": len(result.samples),
        "platform": sys.platform,
    }
    for key, value in numbers.items():
        record_property(f"performance_smoke_{key}", value)
    with capsys.disabled():
        print(f"\nperformance smoke: {json.dumps(numbers)}")
    assert (root / "pipeline_state.json").is_file()
