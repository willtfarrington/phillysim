"""The stage runner: fingerprints, the state file, skip / resume / cancel, status, verify.

Fingerprint-DAG semantics (architecture.md): a stage's fingerprint is the SHA-256
of a canonical JSON document holding the content digest of every declared input
(a file's SHA-256, or for a directory the SHA-256 of its sorted ``path\\0digest``
listing) and the stage's parameters. Nothing fancier: no code hashing, no
timestamps. The runner records each stage's fingerprint and output digests in
``<data root>/pipeline_state.json`` and skips a stage whose recorded fingerprint
equals the current one *and* whose outputs are still on disk unaltered.

Resume and cancel: a stage is marked ``running`` before it starts and ``done``
only after every declared output has been installed into its zone by an atomic
rename from the staging directory (``cache/staging/<stage>/``). A failure or a
cooperative cancellation marks the stage ``failed`` / ``cancelled`` and discards
the staging directory, so the zones only ever hold complete outputs; the next
run re-executes that stage and everything downstream whose inputs changed.
``status`` reports every stage as fresh / stale / missing / incomplete;
``verify`` checks that the state file and the zones agree and names any
incomplete stage.

The state file holds relative paths, digests, parameters, and UTC timestamps
only: no machine identifiers and no absolute paths.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from phillysim.manifest import canonical_bytes, sha256_file
from phillysim.stages import CancelledError, CancelToken, Pipeline, Stage, StageContext, StageError
from phillysim.zones import ensure_layout

STATE_FILE = "pipeline_state.json"
STATE_SCHEMA_VERSION = 1
STAGING_DIR = "cache/staging"

DONE, RUNNING, FAILED, CANCELLED = "done", "running", "failed", "cancelled"
RECORD_STATUSES = frozenset({DONE, RUNNING, FAILED, CANCELLED})

FRESH, STALE, MISSING, INCOMPLETE = "fresh", "stale", "missing", "incomplete"


class StateError(ValueError):
    """The state file is missing, malformed, or describes a different pipeline."""


class MissingInputError(StageError):
    """A declared input is absent, so the stage's fingerprint cannot be computed."""

    def __init__(self, stage: str, rel: str) -> None:
        self.stage, self.rel = stage, rel
        super().__init__(f"stage {stage!r}: input {rel!r} is absent")


# --- digests and fingerprints --------------------------------------------------------


def digest_tree(path: Path) -> str:
    """SHA-256 of a file's bytes, or of a directory's sorted ``relpath\\0digest`` listing."""
    if path.is_file():
        return sha256_file(path)
    if not path.is_dir():
        raise FileNotFoundError(str(path))
    digest = hashlib.sha256()
    entries = sorted(
        (entry.relative_to(path).as_posix(), entry) for entry in path.rglob("*") if entry.is_file()
    )
    for rel, entry in entries:
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update(sha256_file(entry).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def input_digests(root: Path, stage: Stage) -> dict[str, str]:
    out: dict[str, str] = {}
    for rel in stage.inputs:
        path = root / rel
        if not path.exists():
            raise MissingInputError(stage.name, rel)
        out[rel] = digest_tree(path)
    return out


def fingerprint_of(inputs: dict[str, str], params: dict[str, Any]) -> str:
    payload = {"inputs": dict(sorted(inputs.items())), "params": params}
    return hashlib.sha256(canonical_bytes(payload)).hexdigest()


def fingerprint(root: Path, stage: Stage) -> tuple[str, dict[str, str]]:
    """The stage's current fingerprint and the input digests it was built from."""
    inputs = input_digests(root, stage)
    return fingerprint_of(inputs, dict(stage.params)), inputs


# --- the state file -------------------------------------------------------------------


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass
class StageRecord:
    """What the state file remembers about one stage's most recent run."""

    name: str
    status: str
    fingerprint: str
    inputs: dict[str, str]
    params: dict[str, Any]
    outputs: dict[str, str] = field(default_factory=dict)
    started_at: str = ""
    finished_at: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "fingerprint": self.fingerprint,
            "inputs": dict(sorted(self.inputs.items())),
            "params": self.params,
            "outputs": dict(sorted(self.outputs.items())),
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, name: str, payload: Any) -> StageRecord:
        if not isinstance(payload, dict):
            raise StateError(f"stage record {name!r} must be an object")
        try:
            record = cls(
                name=name,
                status=payload["status"],
                fingerprint=payload["fingerprint"],
                inputs=dict(payload["inputs"]),
                params=dict(payload["params"]),
                outputs=dict(payload.get("outputs", {})),
                started_at=payload.get("started_at", ""),
                finished_at=payload.get("finished_at"),
                error=payload.get("error"),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise StateError(f"stage record {name!r} is malformed: {exc}") from exc
        if record.status not in RECORD_STATUSES:
            raise StateError(f"stage record {name!r} has unknown status {record.status!r}")
        return record


@dataclass
class State:
    """The whole state file: which pipeline, and one record per stage that has ever started."""

    pipeline: str
    stages: dict[str, StageRecord] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": STATE_SCHEMA_VERSION,
            "pipeline": self.pipeline,
            "stages": {name: record.to_dict() for name, record in sorted(self.stages.items())},
        }

    @classmethod
    def from_dict(cls, payload: Any) -> State:
        if not isinstance(payload, dict):
            raise StateError("state file must be a JSON object")
        if payload.get("schema_version") != STATE_SCHEMA_VERSION:
            raise StateError(
                f"state file schema_version {payload.get('schema_version')!r} "
                f"is not {STATE_SCHEMA_VERSION}"
            )
        pipeline = payload.get("pipeline")
        if not isinstance(pipeline, str) or not pipeline:
            raise StateError("state file has no pipeline name")
        stages_payload = payload.get("stages", {})
        if not isinstance(stages_payload, dict):
            raise StateError("state file 'stages' must be an object")
        stages = {
            name: StageRecord.from_dict(name, record) for name, record in stages_payload.items()
        }
        return cls(pipeline=pipeline, stages=stages)


def state_path(root: Path) -> Path:
    return root / STATE_FILE


def load_state(root: Path) -> State | None:
    """The state file, or ``None`` if none exists. Malformed files raise :class:`StateError`."""
    path = state_path(root)
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StateError(f"state file is not valid JSON: {exc}") from exc
    return State.from_dict(payload)


def save_state(root: Path, state: State) -> Path:
    """Write the state file atomically (temp file in the same directory, then rename)."""
    path = state_path(root)
    temp = path.with_name(path.name + ".partial")
    temp.write_bytes(canonical_bytes(state.to_dict()))
    os.replace(temp, path)
    return path


# --- status -----------------------------------------------------------------------------


@dataclass(frozen=True)
class StageStatus:
    """One row of ``phillysim status``: fresh / stale / missing / incomplete plus why."""

    name: str
    status: str
    detail: str


def _outputs_intact(root: Path, record: StageRecord) -> str | None:
    """``None`` if every recorded output is on disk with its recorded digest, else why not."""
    for rel, digest in sorted(record.outputs.items()):
        path = root / rel
        if not path.exists():
            return f"output {rel} is absent"
        if digest_tree(path) != digest:
            return f"output {rel} was altered after the stage ran"
    return None


def stage_status(root: Path, state: State | None, stage: Stage) -> StageStatus:
    record = state.stages.get(stage.name) if state is not None else None
    if record is None:
        return StageStatus(stage.name, MISSING, "never run")
    if record.status != DONE:
        why = f"{record.status}" + (f": {record.error}" if record.error else "")
        return StageStatus(stage.name, INCOMPLETE, why)
    problem = _outputs_intact(root, record)
    if problem is not None:
        kind = MISSING if problem.endswith("is absent") else STALE
        return StageStatus(stage.name, kind, problem)
    if set(record.outputs) != set(stage.outputs):
        # The stage now declares different outputs than it produced (a source was
        # registered, say): the recorded ones may be intact, but the run is not complete.
        return StageStatus(stage.name, STALE, "changed: declared outputs")
    try:
        current, _ = fingerprint(root, stage)
    except MissingInputError as exc:
        return StageStatus(stage.name, STALE, f"input {exc.rel} is absent")
    if current != record.fingerprint:
        changed = [
            rel for rel, digest in record.inputs.items() if digest != _digest_or_none(root, rel)
        ]
        if dict(stage.params) != record.params:
            changed.append("parameters")
        return StageStatus(stage.name, STALE, "changed: " + ", ".join(changed or ["inputs"]))
    return StageStatus(stage.name, FRESH, "fingerprint unchanged")


def _digest_or_none(root: Path, rel: str) -> str | None:
    path = root / rel
    return digest_tree(path) if path.exists() else None


def status(root: Path, pipeline: Pipeline) -> list[StageStatus]:
    """Per-stage status for ``pipeline`` at ``root``. Creates nothing."""
    state = load_state(root)
    if state is not None and state.pipeline != pipeline.name:
        raise StateError(
            f"state file belongs to pipeline {state.pipeline!r}, not {pipeline.name!r}"
        )
    return [stage_status(root, state, stage) for stage in pipeline]


# --- running -----------------------------------------------------------------------------


@dataclass(frozen=True)
class StageOutcome:
    name: str
    action: str  # "ran" or "skipped"
    seconds: float
    detail: str = ""


@dataclass
class RunReport:
    outcomes: list[StageOutcome] = field(default_factory=list)

    @property
    def ran(self) -> list[str]:
        return [o.name for o in self.outcomes if o.action == "ran"]

    @property
    def skipped(self) -> list[str]:
        return [o.name for o in self.outcomes if o.action == "skipped"]


def _scrub(text: str, root: Path) -> str:
    """Keep absolute paths out of the state file: replace the data root with a placeholder.

    Native, POSIX, and repr-escaped (doubled backslash) forms are all replaced; a
    Windows ``OSError`` message quotes paths in the last form (found at EP-5a).
    """
    native = str(root)
    for form in dict.fromkeys((native.replace("\\", "\\\\"), native, root.as_posix())):
        text = text.replace(form, "<data-root>")
    return text


def _replace_with_retry(source: Path, target: Path, attempts: int = 10) -> None:
    """``os.replace`` with a short, bounded retry on ``PermissionError``.

    On Windows a virus scanner or indexer can hold a freshly written file for a
    moment; the first real acquisition (a 13 MB zip, EP-5a) failed its install
    on exactly that, and a 24 MB zip (EP-6) outlasted six attempts. The retry
    waits 0.25 s, 0.5 s, ... (about 14 s in all) and then gives up.
    """
    for attempt in range(1, attempts + 1):
        try:
            os.replace(source, target)
            return
        except PermissionError:
            if attempt == attempts:
                raise
            time.sleep(0.25 * attempt)


def _staging_dir(root: Path, stage_name: str) -> Path:
    return root / STAGING_DIR / stage_name


def _install_outputs(root: Path, stage: Stage, staging: Path) -> dict[str, str]:
    """Move each declared output from staging into its zone atomically; return their digests."""
    for rel in stage.outputs:
        if not (staging / rel).exists():
            raise StageError(f"stage {stage.name!r} finished without producing output {rel!r}")
    digests: dict[str, str] = {}
    for rel in stage.outputs:
        source, target = staging / rel, root / rel
        if rel.startswith("raw/") and target.exists():
            # The raw zone is immutable: an identical snapshot is a no-op, a different one an error.
            if digest_tree(source) != digest_tree(target):
                raise StageError(
                    f"stage {stage.name!r}: {rel!r} already exists in the immutable raw zone "
                    "with different content; it will not be overwritten"
                )
            digests[rel] = digest_tree(target)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.is_dir():
            shutil.rmtree(target)
        _replace_with_retry(source, target)
        digests[rel] = digest_tree(target)
    return digests


def run(
    root: Path,
    pipeline: Pipeline,
    *,
    through: str | None = None,
    cancel: CancelToken | None = None,
    echo: Callable[[str], None] | None = None,
) -> RunReport:
    """Bring ``pipeline`` up to date at ``root``, running only stages that are not fresh.

    Creates the zone layout (the one directory-creating call). Raises
    :class:`StageError` if a stage fails and :class:`CancelledError` if the token was
    triggered; in both cases the state file already records the stage as
    incomplete and the staging directory has been discarded.
    """
    cancel = cancel or CancelToken()
    say = echo or (lambda _line: None)
    ensure_layout(root)
    state = load_state(root)
    if state is None:
        state = State(pipeline=pipeline.name)
    elif state.pipeline != pipeline.name:
        raise StateError(
            f"state file belongs to pipeline {state.pipeline!r}, not {pipeline.name!r}"
        )
    report = RunReport()
    for stage in pipeline.through(through):
        cancel.check()
        started = time.perf_counter()
        current = stage_status(root, state, stage)
        if current.status == FRESH:
            report.outcomes.append(StageOutcome(stage.name, "skipped", 0.0, current.detail))
            say(f"skip {stage.name:<14} fresh")
            continue
        fp, inputs = fingerprint(root, stage)  # MissingInputError if an input is absent
        record = StageRecord(
            name=stage.name,
            status=RUNNING,
            fingerprint=fp,
            inputs=inputs,
            params=dict(stage.params),
            started_at=_utc_now(),
        )
        state.stages[stage.name] = record
        save_state(root, state)
        staging = _staging_dir(root, stage.name)
        if staging.exists():
            shutil.rmtree(staging)
        staging.mkdir(parents=True)
        say(f"run  {stage.name:<14} {current.status}: {current.detail}")
        try:
            stage.run(StageContext(stage, root, staging, stage.params, cancel))
            record.outputs = _install_outputs(root, stage, staging)
        except CancelledError:
            record.status, record.finished_at = CANCELLED, _utc_now()
            record.error = "cancelled at a checkpoint"
            save_state(root, state)
            shutil.rmtree(staging, ignore_errors=True)
            raise
        except Exception as exc:
            record.status, record.finished_at = FAILED, _utc_now()
            record.error = _scrub(f"{type(exc).__name__}: {exc}", root)
            save_state(root, state)
            shutil.rmtree(staging, ignore_errors=True)
            if isinstance(exc, StageError):
                raise
            raise StageError(f"stage {stage.name!r} failed: {record.error}") from exc
        shutil.rmtree(staging, ignore_errors=True)
        record.status, record.finished_at = DONE, _utc_now()
        save_state(root, state)
        seconds = time.perf_counter() - started
        report.outcomes.append(StageOutcome(stage.name, "ran", seconds))
        say(f"done {stage.name:<14} {seconds:.1f}s")
    return report


# --- verify: state / zone coherence --------------------------------------------------


@dataclass(frozen=True)
class StageVerdict:
    """``verify``'s view of one stage: ok / incomplete / missing / broken, plus detail."""

    name: str
    verdict: str
    detail: str


@dataclass(frozen=True)
class StateReport:
    """State-file coherence: every ``done`` stage's outputs on disk and unaltered, no stage left
    running / failed / cancelled, no leftover staging, no unknown records."""

    verdicts: tuple[StageVerdict, ...]
    problems: tuple[str, ...]  # incoherence between the state file and the zones

    @property
    def incomplete(self) -> tuple[str, ...]:
        return tuple(v.name for v in self.verdicts if v.verdict == "incomplete")

    @property
    def broken(self) -> tuple[str, ...]:
        return tuple(v.name for v in self.verdicts if v.verdict == "broken")

    @property
    def ok(self) -> bool:
        return not self.problems and not self.incomplete and not self.broken

    def lines(self) -> list[str]:
        out = []
        for verdict in self.verdicts:
            mark = (
                "ok  "
                if verdict.verdict == "ok"
                else "FAIL"
                if verdict.verdict == "broken"
                else "--  "
            )
            out.append(f"{mark} stage {verdict.name}: {verdict.verdict} ({verdict.detail})")
        out.extend(f"FAIL {problem}" for problem in self.problems)
        done = sum(1 for v in self.verdicts if v.verdict == "ok")
        summary = f"{done} of {len(self.verdicts)} stage(s) done and intact"
        if self.incomplete:
            summary += f"; incomplete: {', '.join(self.incomplete)}"
        if self.broken:
            summary += f"; broken: {', '.join(self.broken)}"
        if self.problems:
            summary += f"; {len(self.problems)} coherence problem(s)"
        out.append(summary)
        return out


def verify_state(root: Path, pipeline: Pipeline) -> StateReport:
    """Check the state file against the zones. Creates nothing."""
    problems: list[str] = []
    verdicts: list[StageVerdict] = []
    try:
        state = load_state(root)
    except StateError as exc:
        return StateReport((), (str(exc),))
    if state is not None and state.pipeline != pipeline.name:
        problems.append(f"state file belongs to pipeline {state.pipeline!r}, not {pipeline.name!r}")
        state = None
    for stage in pipeline:
        record = state.stages.get(stage.name) if state is not None else None
        if record is None:
            verdicts.append(StageVerdict(stage.name, "missing", "never run"))
            continue
        if record.status != DONE:
            detail = record.status + (f": {record.error}" if record.error else "")
            verdicts.append(StageVerdict(stage.name, "incomplete", detail))
            continue
        if set(record.outputs) != set(stage.outputs):
            verdicts.append(
                StageVerdict(stage.name, "broken", "recorded outputs differ from the declared ones")
            )
            continue
        problem = _outputs_intact(root, record)
        if problem is not None:
            verdicts.append(StageVerdict(stage.name, "broken", problem))
            continue
        verdicts.append(StageVerdict(stage.name, "ok", "outputs present and unaltered"))
    if state is not None:
        for name in sorted(set(state.stages) - set(pipeline.names)):
            problems.append(f"state file records unknown stage {name!r}")
    staging_root = root / STAGING_DIR
    if staging_root.is_dir():
        for entry in sorted(staging_root.iterdir(), key=lambda p: p.name):
            problems.append(f"leftover staging directory for stage {entry.name!r}")
    return StateReport(tuple(verdicts), tuple(problems))
