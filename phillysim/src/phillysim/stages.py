"""Stage registry: what a pipeline stage declares, and the pipeline that orders them.

architecture.md fixes the shape: eleven idempotent stages with fingerprint-DAG
semantics, each a plain function behind a Typer command, no orchestrator. A
:class:`Stage` declares its *inputs* and *outputs* as paths relative to the data
root (``raw/<source>``, ``curated/tracts_spine.parquet``, ...) plus a mapping of
JSON-serializable *parameters*; the runner (:mod:`phillysim.runner`) turns the
inputs' content and the parameters into a fingerprint, and skips a stage whose
fingerprint has not changed since its recorded run.

A stage never writes into a zone itself. It writes its outputs under the
:class:`StageContext`'s ``staging`` directory and the runner installs them with
an atomic rename once the stage has finished, so a crash or cancellation never
leaves a partially written file in a zone. Cancellation is cooperative: the
runner checks the :class:`CancelToken` between stages, and a stage calls
:meth:`StageContext.checkpoint` at its own safe points.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any

from phillysim.config import ZONES

STAGE_NAME_PATTERN = r"[a-z][a-z0-9_]{0,63}"
_STAGE_NAME_RE = re.compile(rf"^{STAGE_NAME_PATTERN}$")


class PipelineError(ValueError):
    """A stage declaration or the pipeline's wiring breaks the registry rules."""


class StageError(Exception):
    """A stage could not complete (bad input, contract violation, missing output, ...)."""


class CancelledError(Exception):
    """Raised at a checkpoint after :meth:`CancelToken.cancel` was called."""


class CancelToken:
    """A cooperative cancellation flag shared between a caller and the runner."""

    def __init__(self) -> None:
        self._cancelled = False

    @property
    def cancelled(self) -> bool:
        return self._cancelled

    def cancel(self) -> None:
        self._cancelled = True

    def check(self) -> None:
        """Raise :class:`CancelledError` if cancellation was requested."""
        if self._cancelled:
            raise CancelledError("cancellation requested")


def check_stage_name(name: str) -> str:
    if not isinstance(name, str) or not _STAGE_NAME_RE.match(name):
        raise PipelineError(
            f"invalid stage name {name!r}: expected lowercase slug /{STAGE_NAME_PATTERN}/"
        )
    return name


def check_relpath(rel: str) -> str:
    """A data-root-relative POSIX path inside a zone: no absolute paths, drives, or ``..``."""
    if not isinstance(rel, str) or not rel:
        raise PipelineError(f"invalid stage path {rel!r}")
    if "\\" in rel or ":" in rel or rel.startswith("/") or rel.endswith("/"):
        raise PipelineError(f"stage path {rel!r} must be a relative POSIX path")
    parts = PurePosixPath(rel).parts
    if any(part in {".", "..", ""} for part in parts):
        raise PipelineError(f"stage path {rel!r} must not contain '.' or '..' components")
    if parts[0] not in ZONES:
        raise PipelineError(f"stage path {rel!r} must start with a zone name {ZONES}")
    return rel


def zone_of(rel: str) -> str:
    return PurePosixPath(rel).parts[0]


def _check_params(params: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(params, Mapping):
        raise PipelineError("stage params must be a mapping")
    try:
        json.dumps(params, sort_keys=True)
    except (TypeError, ValueError) as exc:
        raise PipelineError(f"stage params must be JSON-serializable: {exc}") from exc
    return dict(params)


@dataclass(frozen=True)
class StageContext:
    """What a stage function receives.

    ``root`` is the data root (read declared inputs from ``root / rel``);
    ``staging`` is the scratch directory the stage writes its outputs into
    (``staging / rel``); ``params`` are the stage's parameters after any
    command-line overrides; ``cancel`` is the cooperative cancellation token.
    """

    stage: Stage
    root: Path
    staging: Path
    params: Mapping[str, Any]
    cancel: CancelToken

    def input(self, rel: str) -> Path:
        """Path of a declared input under the data root."""
        if rel not in self.stage.inputs:
            raise StageError(f"stage {self.stage.name!r} did not declare input {rel!r}")
        return self.root / rel

    def output(self, rel: str) -> Path:
        """Path to write a declared output to (under staging; parent created)."""
        if rel not in self.stage.outputs:
            raise StageError(f"stage {self.stage.name!r} did not declare output {rel!r}")
        path = self.staging / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def checkpoint(self) -> None:
        """A safe point: raise :class:`CancelledError` if cancellation was requested."""
        self.cancel.check()


@dataclass(frozen=True)
class Stage:
    """One pipeline stage: a name, its inputs, its outputs, its parameters, and its function."""

    name: str
    run: Callable[[StageContext], None]
    inputs: tuple[str, ...] = ()
    outputs: tuple[str, ...] = ()
    params: Mapping[str, Any] = field(default_factory=dict)
    description: str = ""

    def __post_init__(self) -> None:
        check_stage_name(self.name)
        if not callable(self.run):
            raise PipelineError(f"stage {self.name!r}: run must be callable")
        for rel in (*self.inputs, *self.outputs):
            check_relpath(rel)
        if len(set(self.inputs)) != len(self.inputs):
            raise PipelineError(f"stage {self.name!r} lists an input twice")
        if len(set(self.outputs)) != len(self.outputs):
            raise PipelineError(f"stage {self.name!r} lists an output twice")
        if not self.outputs:
            raise PipelineError(f"stage {self.name!r} must declare at least one output")
        if set(self.inputs) & set(self.outputs):
            raise PipelineError(f"stage {self.name!r} lists a path as both input and output")
        object.__setattr__(self, "params", _check_params(self.params))

    def with_params(self, overrides: Mapping[str, Any]) -> Stage:
        """A copy with ``overrides`` merged over the declared parameters (unknown keys refused)."""
        unknown = sorted(set(overrides) - set(self.params))
        if unknown:
            raise PipelineError(f"stage {self.name!r} has no parameter(s) {unknown}")
        return Stage(
            name=self.name,
            run=self.run,
            inputs=self.inputs,
            outputs=self.outputs,
            params={**self.params, **overrides},
            description=self.description,
        )


class Pipeline:
    """An ordered, validated sequence of stages forming a DAG over data-root paths.

    Every input is either external (under ``raw/``, produced by acquisition) or the
    output of an *earlier* stage; every output is produced by exactly one stage.
    """

    def __init__(self, name: str, stages: tuple[Stage, ...] | list[Stage]) -> None:
        self.name = check_stage_name(name)
        self.stages: tuple[Stage, ...] = tuple(stages)
        if not self.stages:
            raise PipelineError("a pipeline needs at least one stage")
        producers: dict[str, str] = {}
        names: set[str] = set()
        for stage in self.stages:
            if stage.name in names:
                raise PipelineError(f"duplicate stage name {stage.name!r}")
            names.add(stage.name)
            for rel in stage.inputs:
                if rel not in producers and zone_of(rel) != "raw":
                    raise PipelineError(
                        f"stage {stage.name!r} input {rel!r} is produced by no earlier stage"
                    )
            for rel in stage.outputs:
                if rel in producers:
                    raise PipelineError(
                        f"output {rel!r} is produced by both {producers[rel]!r} and {stage.name!r}"
                    )
                producers[rel] = stage.name
        self._producers = producers

    def __iter__(self) -> Iterator[Stage]:
        return iter(self.stages)

    def __len__(self) -> int:
        return len(self.stages)

    def __getitem__(self, name: str) -> Stage:
        for stage in self.stages:
            if stage.name == name:
                return stage
        raise KeyError(name)

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(stage.name for stage in self.stages)

    def producer(self, rel: str) -> str | None:
        """Name of the stage that produces ``rel``, or ``None`` for external (raw) inputs."""
        return self._producers.get(rel)

    def through(self, name: str | None = None) -> tuple[Stage, ...]:
        """The stages to run, in order, to bring ``name`` (default: the last stage) up to date."""
        if name is None:
            return self.stages
        if name not in self.names:
            raise PipelineError(f"unknown stage {name!r}; expected one of {list(self.names)}")
        return self.stages[: self.names.index(name) + 1]

    def with_params(self, overrides: Mapping[str, Mapping[str, Any]]) -> Pipeline:
        """A copy with per-stage parameter overrides ``{stage: {key: value}}`` applied."""
        unknown = sorted(set(overrides) - set(self.names))
        if unknown:
            raise PipelineError(f"no such stage(s) {unknown}; expected one of {list(self.names)}")
        stages = [
            stage.with_params(overrides[stage.name]) if stage.name in overrides else stage
            for stage in self.stages
        ]
        return Pipeline(self.name, stages)


def parse_param(text: str) -> tuple[str, str, Any]:
    """Parse a ``stage.key=value`` override; the value is JSON if it parses, else a string."""
    if "=" not in text:
        raise PipelineError(f"parameter override {text!r} must look like stage.key=value")
    target, raw_value = text.split("=", 1)
    if "." not in target:
        raise PipelineError(f"parameter override {text!r} must look like stage.key=value")
    stage, key = target.split(".", 1)
    check_stage_name(stage)
    if not key:
        raise PipelineError(f"parameter override {text!r} has an empty key")
    try:
        value: Any = json.loads(raw_value)
    except json.JSONDecodeError:
        value = raw_value
    return stage, key, value


def parse_params(texts: list[str]) -> dict[str, dict[str, Any]]:
    """Group ``stage.key=value`` overrides by stage."""
    out: dict[str, dict[str, Any]] = {}
    for text in texts:
        stage, key, value = parse_param(text)
        out.setdefault(stage, {})[key] = value
    return out
