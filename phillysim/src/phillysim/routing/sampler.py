"""The process-tree RSS sampler and the wall clock (EP-13; architecture.md "Resource budgets").

The routing budget is measured as the peak **sum of RSS across the process
tree** (the Python child, the JVM it hosts, and anything either spawns),
sampled at >= 1 Hz: budget 20 GB, kill 22 GB. A :class:`Sampler` thread in
the parent samples the child and all its descendants with psutil (1 Hz by
default, 4 Hz during start-up, when the JVM's heap grows fastest), records
the peak and the whole time series, notes the second the 20 GB budget line
was first crossed, and kills the whole tree (children first) the moment a
sample reaches the kill line. Wall time runs from the child's start to its
exit.

The clock, the sleep, the RSS probe, and the killer are injectable, so the
unit tests drive the loop with a scripted memory profile and a fake clock and
also run it against a real scripted child that allocates in steps.
"""

from __future__ import annotations

import csv
import threading
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import psutil

GB = 10**9
#: architecture.md: the budget line (recorded when crossed) and the kill line (enforced).
BUDGET_BYTES = 20 * GB
KILL_BYTES = 22 * GB
DEFAULT_INTERVAL = 1.0  # seconds; >= 1 Hz
STARTUP_INTERVAL = 0.25  # 4 Hz while the JVM starts
STARTUP_SECONDS = 60.0

RSS_CSV_COLUMNS: tuple[str, ...] = ("utc", "elapsed_s", "rss_bytes")


def tree_rss(process: psutil.Process) -> int | None:
    """Sum of RSS over ``process`` and every descendant, or ``None`` once it has exited.

    A descendant that disappears between listing and measuring is skipped.
    """
    try:
        if not process.is_running() or process.status() == psutil.STATUS_ZOMBIE:
            return None
        members = [process, *process.children(recursive=True)]
    except (psutil.NoSuchProcess, psutil.ZombieProcess):
        return None
    except psutil.AccessDenied:  # pragma: no cover - the parent owns its child
        members = [process]
    total = 0
    for member in members:
        try:
            total += member.memory_info().rss
        except (psutil.NoSuchProcess, psutil.ZombieProcess, psutil.AccessDenied):
            continue
    return total


def kill_tree(process: psutil.Process, timeout: float = 10.0) -> list[int]:
    """Kill every descendant (deepest first), then the process; wait for them. Returns the
    PIDs killed."""
    try:
        children = process.children(recursive=True)
    except psutil.NoSuchProcess:
        children = []
    killed: list[int] = []
    for member in [*reversed(children), process]:
        try:
            member.kill()
            killed.append(member.pid)
        except psutil.NoSuchProcess:
            continue
    psutil.wait_procs([*children, process], timeout=timeout)
    return killed


@dataclass(frozen=True)
class Sample:
    utc: str
    elapsed_s: float
    rss_bytes: int


@dataclass
class SamplerResult:
    """What the sampler saw: the series, the peak and when, the lines, and the kill."""

    samples: list[Sample] = field(default_factory=list)
    peak_bytes: int = 0
    peak_elapsed_s: float | None = None
    peak_utc: str | None = None
    budget_bytes: int = BUDGET_BYTES
    kill_bytes: int = KILL_BYTES
    budget_crossed_elapsed_s: float | None = None
    killed: bool = False
    killed_elapsed_s: float | None = None
    killed_bytes: int | None = None

    @property
    def budget_crossed(self) -> bool:
        return self.budget_crossed_elapsed_s is not None

    def peak_between(self, start_utc: str | None, end_utc: str | None) -> int | None:
        """The peak over the samples whose UTC stamp lies in ``[start_utc, end_utc]``
        (ISO 8601 strings compare lexically); ``None`` when no sample does."""
        if start_utc is None or end_utc is None:
            return None
        inside = [s.rss_bytes for s in self.samples if start_utc <= s.utc <= end_utc]
        return max(inside) if inside else None

    def to_dict(self) -> dict:
        return {
            "samples": len(self.samples),
            "peak_rss_bytes": self.peak_bytes,
            "peak_rss_elapsed_s": self.peak_elapsed_s,
            "peak_rss_utc": self.peak_utc,
            "budget_bytes": self.budget_bytes,
            "budget_crossed": self.budget_crossed,
            "budget_crossed_elapsed_s": self.budget_crossed_elapsed_s,
            "kill_bytes": self.kill_bytes,
            "killed": self.killed,
            "killed_elapsed_s": self.killed_elapsed_s,
            "killed_bytes": self.killed_bytes,
        }


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


class Sampler(threading.Thread):
    """Sample ``rss_of()`` until it returns ``None`` (the tree is gone) or :meth:`stop`.

    ``rss_of`` returns the tree's RSS sum or ``None``; ``kill`` is called once when a
    sample reaches ``kill_bytes``. ``clock`` measures elapsed seconds, ``now`` stamps
    samples, ``sleep`` waits between them.
    """

    def __init__(
        self,
        rss_of: Callable[[], int | None],
        *,
        kill: Callable[[], None],
        kill_bytes: int = KILL_BYTES,
        budget_bytes: int = BUDGET_BYTES,
        interval: float = DEFAULT_INTERVAL,
        startup_interval: float = STARTUP_INTERVAL,
        startup_seconds: float = STARTUP_SECONDS,
        clock: Callable[[], float] = time.monotonic,
        now: Callable[[], str] = _utc_now,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        super().__init__(name="phillysim-rss-sampler", daemon=True)
        if interval <= 0 or interval > 1.0:
            raise ValueError("the sampling interval must be positive and at most 1 s (>= 1 Hz)")
        if kill_bytes <= budget_bytes:
            raise ValueError("the kill line must lie above the budget line")
        self._rss_of = rss_of
        self._kill = kill
        self._interval = interval
        self._startup_interval = min(startup_interval, interval)
        self._startup_seconds = startup_seconds
        self._clock = clock
        self._now = now
        self._sleep = sleep
        self._stop = threading.Event()
        self._started_at: float | None = None
        self.result = SamplerResult(budget_bytes=budget_bytes, kill_bytes=kill_bytes)

    @classmethod
    def for_process(cls, process: psutil.Process, **kwargs) -> Sampler:
        """A sampler over a live process tree."""
        return cls(lambda: tree_rss(process), kill=lambda: kill_tree(process), **kwargs)

    def stop(self) -> None:
        self._stop.set()

    def elapsed(self) -> float:
        if self._started_at is None:
            return 0.0
        return self._clock() - self._started_at

    def step(self) -> bool:
        """Take one sample; return ``False`` when sampling should end."""
        rss = self._rss_of()
        if rss is None:
            return False
        elapsed = round(self.elapsed(), 3)
        result = self.result
        result.samples.append(Sample(self._now(), elapsed, rss))
        if rss > result.peak_bytes or result.peak_elapsed_s is None:
            result.peak_bytes = rss
            result.peak_elapsed_s = elapsed
            result.peak_utc = result.samples[-1].utc
        if rss >= result.budget_bytes and result.budget_crossed_elapsed_s is None:
            result.budget_crossed_elapsed_s = elapsed
        if rss >= result.kill_bytes and not result.killed:
            result.killed = True
            result.killed_elapsed_s = elapsed
            result.killed_bytes = rss
            self._kill()
            return False
        return True

    def run(self) -> None:
        self._started_at = self._clock()
        while not self._stop.is_set():
            if not self.step():
                return
            fast = self.elapsed() < self._startup_seconds
            self._sleep(self._startup_interval if fast else self._interval)

    def run_to_end(self) -> SamplerResult:
        """Run the loop synchronously (tests)."""
        self.run()
        return self.result


def write_rss_csv(path: Path, samples: Iterable[Sample]) -> None:
    """``rss.csv``: one row per sample (UTC second, elapsed seconds, bytes)."""
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(RSS_CSV_COLUMNS)
        for sample in samples:
            writer.writerow([sample.utc, f"{sample.elapsed_s:.3f}", sample.rss_bytes])


def read_rss_csv(path: Path) -> list[Sample]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [Sample(r["utc"], float(r["elapsed_s"]), int(r["rss_bytes"])) for r in reader]
