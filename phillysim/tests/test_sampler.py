"""EP-13: the process-tree RSS sampler on a scripted profile and on a real scripted child.

The scripted tests drive :class:`Sampler` with a fake clock and a fake RSS probe, so
the peak, the budget crossing, and the kill are checked sample by sample; the child
tests spawn a Python process that allocates memory in steps (and one that spawns a
grandchild) and require the sampler to kill the whole tree at the threshold and to
record a peak within one allocation step of the true peak.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap
import time
from pathlib import Path

import psutil
import pytest

from phillysim.routing import sampler as sm
from phillysim.routing.sampler import (
    BUDGET_BYTES,
    KILL_BYTES,
    Sample,
    Sampler,
    kill_tree,
    read_rss_csv,
    tree_rss,
    write_rss_csv,
)

GB = 10**9
MIB = 1024**2


class FakeClock:
    def __init__(self, step: float = 1.0) -> None:
        self.now = 0.0
        self.step = step
        self.slept: list[float] = []

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds


def scripted(values: list[int | None], **kwargs) -> tuple[Sampler, FakeClock, list[int]]:
    clock = FakeClock()
    series = iter(values)
    kills: list[int] = []
    sampler = Sampler(
        lambda: next(series, None),
        kill=lambda: kills.append(1),
        clock=clock,
        now=lambda: f"2026-09-03T00:00:{int(clock.now):02d}Z",
        sleep=clock.sleep,
        startup_seconds=0.0,
        **kwargs,
    )
    return sampler, clock, kills


def test_lines_follow_architecture_budgets() -> None:
    assert BUDGET_BYTES == 20 * GB and KILL_BYTES == 22 * GB
    assert sm.DEFAULT_INTERVAL <= 1.0 and sm.STARTUP_INTERVAL <= 0.25


def test_kill_at_threshold_records_the_peak_and_the_budget_crossing() -> None:
    sampler, clock, kills = scripted([1 * GB, 5 * GB, 21 * GB, 23 * GB, 25 * GB])
    result = sampler.run_to_end()
    assert kills == [1]
    assert result.killed and result.killed_bytes == 23 * GB and result.killed_elapsed_s == 3.0
    assert result.peak_bytes == 23 * GB and result.peak_elapsed_s == 3.0
    assert result.budget_crossed and result.budget_crossed_elapsed_s == 2.0
    assert [s.rss_bytes for s in result.samples] == [1 * GB, 5 * GB, 21 * GB, 23 * GB]
    assert clock.slept == [1.0, 1.0, 1.0]  # one interval between samples, none after the kill
    assert result.to_dict()["samples"] == 4 and result.to_dict()["killed"] is True


def test_a_tree_that_exits_under_the_lines_is_not_killed() -> None:
    sampler, _clock, kills = scripted([3 * GB, 8 * GB, 6 * GB, None])
    result = sampler.run_to_end()
    assert kills == [] and not result.killed and not result.budget_crossed
    assert result.peak_bytes == 8 * GB and result.peak_elapsed_s == 1.0
    assert result.peak_utc == "2026-09-03T00:00:01Z"
    assert len(result.samples) == 3


def test_startup_sampling_is_faster_then_settles() -> None:
    clock = FakeClock()
    series = iter([1, 2, 3, 4, 5, 6, None])
    sampler = Sampler(
        lambda: next(series, None),
        kill=lambda: None,
        clock=clock,
        sleep=clock.sleep,
        startup_seconds=1.0,
        startup_interval=0.25,
        interval=1.0,
    )
    sampler.run_to_end()
    assert clock.slept == [0.25, 0.25, 0.25, 0.25, 1.0, 1.0]


def test_interval_and_lines_are_validated() -> None:
    with pytest.raises(ValueError, match=">= 1 Hz"):
        Sampler(lambda: None, kill=lambda: None, interval=2.0)
    with pytest.raises(ValueError, match="kill line"):
        Sampler(lambda: None, kill=lambda: None, kill_bytes=10, budget_bytes=20)


def test_peak_between_phases() -> None:
    sampler, _clock, _kills = scripted([1, 9, 4, 7, None])
    result = sampler.run_to_end()
    assert result.peak_between("2026-09-03T00:00:00Z", "2026-09-03T00:00:01Z") == 9
    assert result.peak_between("2026-09-03T00:00:02Z", "2026-09-03T00:00:03Z") == 7
    assert result.peak_between(None, "2026-09-03T00:00:03Z") is None
    assert result.peak_between("2026-09-03T00:01:00Z", "2026-09-03T00:02:00Z") is None


def test_rss_csv_round_trip(tmp_path: Path) -> None:
    samples = [Sample("2026-09-03T00:00:00Z", 0.0, 10), Sample("2026-09-03T00:00:01Z", 1.0, 20)]
    write_rss_csv(tmp_path / "rss.csv", samples)
    text = (tmp_path / "rss.csv").read_text("utf-8")
    assert text.splitlines()[0] == "utc,elapsed_s,rss_bytes"
    assert read_rss_csv(tmp_path / "rss.csv") == samples


# --- a real scripted child ------------------------------------------------------------------

ALLOCATOR = textwrap.dedent(
    """
    import sys, time
    step, steps, hold = int(sys.argv[1]), int(sys.argv[2]), float(sys.argv[3])
    blocks = []
    for _ in range(steps):
        blocks.append(bytearray(step))
        for i in range(0, step, 4096):
            blocks[-1][i] = 1  # touch every page so RSS grows with the allocation
        time.sleep(0.05)
    print("done", flush=True)
    time.sleep(hold)
    """
)

SPAWNER = textwrap.dedent(
    """
    import subprocess, sys, time
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    print(child.pid, flush=True)
    time.sleep(60)
    """
)


def test_sampler_kills_a_scripted_child_at_the_threshold() -> None:
    step = 32 * MIB
    process = subprocess.Popen(
        [sys.executable, "-c", ALLOCATOR, str(step), "20", "30"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        kill_at = 256 * MIB
        sampler = Sampler.for_process(
            psutil.Process(process.pid),
            kill_bytes=kill_at,
            budget_bytes=192 * MIB,
            interval=0.02,
            startup_interval=0.02,
        )
        sampler.start()
        exit_code = process.wait(timeout=60)
        sampler.join(timeout=10)
    finally:
        if process.poll() is None:
            process.kill()
    result = sampler.result
    assert result.killed, result.to_dict()
    assert exit_code != 0  # killed, never printed "done" and exited normally
    assert result.peak_bytes >= kill_at
    # Within one allocation step (plus the interpreter's own growth) of the true peak.
    assert result.peak_bytes <= kill_at + 3 * step, result.to_dict()
    assert result.budget_crossed and result.budget_crossed_elapsed_s <= result.killed_elapsed_s
    assert len(result.samples) >= 3
    assert not psutil.pid_exists(process.pid)


def test_sampler_lets_a_small_child_finish() -> None:
    process = subprocess.Popen(
        [sys.executable, "-c", ALLOCATOR, str(4 * MIB), "3", "0"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    sampler = Sampler.for_process(psutil.Process(process.pid), interval=0.02, startup_interval=0.02)
    sampler.start()
    out, _err = process.communicate(timeout=60)
    sampler.join(timeout=10)
    assert process.returncode == 0 and b"done" in out
    assert not sampler.result.killed and sampler.result.peak_bytes > 0


def test_kill_tree_takes_the_grandchild_too() -> None:
    process = subprocess.Popen([sys.executable, "-c", SPAWNER], stdout=subprocess.PIPE, text=True)
    grandchild_pid = int(process.stdout.readline().strip())
    parent = psutil.Process(process.pid)
    assert psutil.pid_exists(grandchild_pid)
    total = tree_rss(parent)
    assert total is not None and total > psutil.Process(process.pid).memory_info().rss
    killed = kill_tree(parent)
    # uv's venv `python.exe` on Windows is a trampoline that runs the real interpreter as
    # its own child, so the tree can hold more than the two PIDs the script knows about.
    assert {process.pid, grandchild_pid} <= set(killed)
    process.wait(timeout=10)
    deadline = time.monotonic() + 10
    while psutil.pid_exists(grandchild_pid) and time.monotonic() < deadline:
        time.sleep(0.05)
    assert not psutil.pid_exists(grandchild_pid)
    assert tree_rss(parent) is None
