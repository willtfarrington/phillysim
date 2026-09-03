"""Source-contract harness: schema, license, and geometry expectations per source.

roadmap/quality.md lists "source contracts" as the first row of the test matrix:
schema / license / geometry expectations per adapter, checked on offline fixtures
in CI. This module is the adapter-agnostic half of that: a contract is a frozen
description of what a loaded table must look like, and :func:`check_frame` turns
a table (plus its snapshot manifest) into a list of :class:`Violation` records.
Adapters (EP-5 onward) declare a :class:`SourceContract` each; the tinycity
fixture (EP-3) proves the pattern against fake sources.

Design limits, on purpose: the harness inspects pandas / GeoPandas frames only,
so it never touches the network or a file format; it reports every violation it
finds rather than stopping at the first; and it knows nothing about how a table
was acquired — that is the manifest engine's job (EP-4).
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import geopandas as gpd
import pandas as pd
from pandas.api import types as ptypes
from pyproj import CRS

KINDS: tuple[str, ...] = ("int", "float", "str", "bool")

#: License buckets a published output may carry (ADR-0003). A raw-source
#: manifest records the bucket its derived outputs will fall into.
LICENSE_BUCKETS: frozenset[str] = frozenset({"A", "B"})


@dataclass(frozen=True)
class ColumnSpec:
    """One required column.

    ``kind`` is a coarse type family, not a dtype: ``int`` accepts any integer
    dtype (nullable ``Int64`` included), ``float`` accepts float *or* integer,
    ``str`` accepts string / object dtypes (and an all-null column, which pandas
    cannot type), ``bool`` accepts boolean dtypes. ``minimum``, ``maximum``,
    ``allowed``, and ``pattern`` (a regex the whole string value must match) are
    value constraints checked on non-null cells.
    """

    name: str
    kind: str
    nullable: bool = True
    minimum: float | None = None
    maximum: float | None = None
    allowed: frozenset[str] | None = None
    pattern: str | None = None

    def __post_init__(self) -> None:
        if self.kind not in KINDS:
            raise ValueError(f"unknown column kind {self.kind!r}; expected one of {KINDS}")
        if self.pattern is not None:
            re.compile(self.pattern)


@dataclass(frozen=True)
class GeometrySpec:
    """Geometry expectations for a spatial table."""

    types: frozenset[str]
    crs: str = "EPSG:4326"
    bounds: tuple[float, float, float, float] | None = None  # minx, miny, maxx, maxy
    require_valid: bool = True


@dataclass(frozen=True)
class SourceContract:
    """What one source table must satisfy after loading."""

    name: str
    columns: tuple[ColumnSpec, ...]
    key: str | None = None
    geometry: GeometrySpec | None = None
    license_buckets: frozenset[str] = LICENSE_BUCKETS
    schema_version: int = 1
    min_rows: int = 1
    max_rows: int | None = None

    def column_names(self) -> tuple[str, ...]:
        return tuple(column.name for column in self.columns)


@dataclass(frozen=True)
class Violation:
    """One failed expectation. ``check`` is one of schema / license / geometry / key / rows."""

    contract: str
    check: str
    detail: str

    def __str__(self) -> str:
        return f"[{self.contract}] {self.check}: {self.detail}"


class ContractViolationError(Exception):
    """Raised by :func:`enforce` when a table breaks its contract."""

    def __init__(self, violations: list[Violation]) -> None:
        self.violations = violations
        lines = "\n".join(f"  - {violation}" for violation in violations)
        super().__init__(f"{len(violations)} contract violation(s):\n{lines}")


# --- checks ---------------------------------------------------------------------


def _kind_matches(series: pd.Series, kind: str) -> bool:
    dtype = series.dtype
    if kind == "int":
        return bool(ptypes.is_integer_dtype(dtype))
    if kind == "float":
        return bool(ptypes.is_float_dtype(dtype) or ptypes.is_integer_dtype(dtype))
    if kind == "bool":
        return bool(ptypes.is_bool_dtype(dtype))
    # str: string or object dtype; an all-null column has no inferable type.
    return bool(
        ptypes.is_string_dtype(dtype) or ptypes.is_object_dtype(dtype) or series.isna().all()
    )


def _check_schema(contract: SourceContract, frame: pd.DataFrame) -> list[Violation]:
    out: list[Violation] = []
    for spec in contract.columns:
        if spec.name not in frame.columns:
            out.append(Violation(contract.name, "schema", f"missing column {spec.name!r}"))
            continue
        series = frame[spec.name]
        if not _kind_matches(series, spec.kind):
            out.append(
                Violation(
                    contract.name,
                    "schema",
                    f"column {spec.name!r} has dtype {series.dtype}, expected kind {spec.kind!r}",
                )
            )
            continue
        nulls = int(series.isna().sum())
        if nulls and not spec.nullable:
            out.append(
                Violation(contract.name, "schema", f"column {spec.name!r} has {nulls} null(s)")
            )
        present = series.dropna()
        if spec.minimum is not None and spec.kind in ("int", "float"):
            below = int((present < spec.minimum).sum())
            if below:
                out.append(
                    Violation(
                        contract.name,
                        "schema",
                        f"column {spec.name!r} has {below} value(s) below {spec.minimum}",
                    )
                )
        if spec.maximum is not None and spec.kind in ("int", "float"):
            above = int((present > spec.maximum).sum())
            if above:
                out.append(
                    Violation(
                        contract.name,
                        "schema",
                        f"column {spec.name!r} has {above} value(s) above {spec.maximum}",
                    )
                )
        if spec.allowed is not None:
            bad = sorted({str(value) for value in present if str(value) not in spec.allowed})
            if bad:
                out.append(
                    Violation(
                        contract.name,
                        "schema",
                        f"column {spec.name!r} has value(s) outside the allowed set: {bad}",
                    )
                )
        if spec.pattern is not None:
            regex = re.compile(spec.pattern)
            bad = sorted({str(value) for value in present if not regex.fullmatch(str(value))})
            if bad:
                out.append(
                    Violation(
                        contract.name,
                        "schema",
                        f"column {spec.name!r} has value(s) not matching {spec.pattern!r}: "
                        f"{bad[:5]}",
                    )
                )
    return out


def _check_license(contract: SourceContract, manifest: Mapping[str, Any]) -> list[Violation]:
    out: list[Violation] = []
    bucket = manifest.get("license_bucket")
    if bucket not in contract.license_buckets:
        out.append(
            Violation(
                contract.name,
                "license",
                f"manifest license_bucket {bucket!r} not in {sorted(contract.license_buckets)}",
            )
        )
    version = manifest.get("schema_version")
    if version != contract.schema_version:
        out.append(
            Violation(
                contract.name,
                "license",
                f"manifest schema_version {version!r} != contract {contract.schema_version}",
            )
        )
    return out


def _check_geometry(
    contract: SourceContract, spec: GeometrySpec, frame: pd.DataFrame
) -> list[Violation]:
    if not isinstance(frame, gpd.GeoDataFrame) or frame.geometry is None:
        return [Violation(contract.name, "geometry", "table has no geometry column")]
    out: list[Violation] = []
    geometry = frame.geometry
    expected_crs = CRS.from_user_input(spec.crs)
    if frame.crs is None or frame.crs != expected_crs:
        out.append(
            Violation(contract.name, "geometry", f"CRS is {frame.crs!r}, expected {spec.crs}")
        )
    missing = int((geometry.isna() | geometry.is_empty).sum())
    if missing:
        out.append(Violation(contract.name, "geometry", f"{missing} null/empty geometr(ies)"))
    present = geometry[~(geometry.isna() | geometry.is_empty)]
    if len(present) == 0:
        return out
    stray = sorted(set(present.geom_type) - set(spec.types))
    if stray:
        out.append(
            Violation(
                contract.name,
                "geometry",
                f"geometry type(s) {stray} outside the allowed {sorted(spec.types)}",
            )
        )
    if spec.require_valid:
        invalid = present[~present.is_valid]
        if len(invalid):
            reasons = sorted(set(invalid.is_valid_reason()))
            out.append(
                Violation(
                    contract.name, "geometry", f"{len(invalid)} invalid geometr(ies): {reasons}"
                )
            )
    if spec.bounds is not None:
        minx, miny, maxx, maxy = present.total_bounds
        bminx, bminy, bmaxx, bmaxy = spec.bounds
        if minx < bminx or miny < bminy or maxx > bmaxx or maxy > bmaxy:
            out.append(
                Violation(
                    contract.name,
                    "geometry",
                    f"extent ({minx:.6f}, {miny:.6f}, {maxx:.6f}, {maxy:.6f}) "
                    f"exceeds bounds {spec.bounds}",
                )
            )
    return out


def _check_key(contract: SourceContract, key: str, frame: pd.DataFrame) -> list[Violation]:
    if key not in frame.columns:
        return [Violation(contract.name, "key", f"key column {key!r} missing")]
    out: list[Violation] = []
    series = frame[key]
    nulls = int(series.isna().sum())
    if nulls:
        out.append(Violation(contract.name, "key", f"{nulls} null key(s) in {key!r}"))
    duplicates = series.dropna()[series.dropna().duplicated()]
    if len(duplicates):
        sample = sorted({str(value) for value in duplicates})[:5]
        out.append(Violation(contract.name, "key", f"duplicate key(s) in {key!r}: {sample}"))
    return out


def _check_rows(contract: SourceContract, frame: pd.DataFrame) -> list[Violation]:
    n = len(frame)
    if n < contract.min_rows:
        return [Violation(contract.name, "rows", f"{n} row(s) < minimum {contract.min_rows}")]
    if contract.max_rows is not None and n > contract.max_rows:
        return [Violation(contract.name, "rows", f"{n} row(s) > maximum {contract.max_rows}")]
    return []


def check_frame(
    contract: SourceContract,
    frame: pd.DataFrame,
    manifest: Mapping[str, Any] | None = None,
) -> list[Violation]:
    """Return every violation of ``contract`` in ``frame`` (empty list = conforming).

    License and schema-version checks run only when a ``manifest`` is supplied;
    the manifest is the snapshot's checksummed record (architecture.md, "Zones &
    identifiers"), and the fixture writes a proposed shape for it.
    """
    violations = _check_rows(contract, frame)
    violations += _check_schema(contract, frame)
    if contract.key is not None:
        violations += _check_key(contract, contract.key, frame)
    if contract.geometry is not None:
        violations += _check_geometry(contract, contract.geometry, frame)
    if manifest is not None:
        violations += _check_license(contract, manifest)
    return violations


def enforce(
    contract: SourceContract,
    frame: pd.DataFrame,
    manifest: Mapping[str, Any] | None = None,
) -> None:
    """Raise :class:`ContractViolationError` if ``frame`` breaks ``contract``."""
    violations = check_frame(contract, frame, manifest)
    if violations:
        raise ContractViolationError(violations)


# --- the analytic-table contract (locked schema; methodology.md "Uncertainty") ----

RELIABILITY_ACTIONS: frozenset[str] = frozenset({"none", "interval-only"})

#: Per tract-metric row: {estimate, MOE, CV tier, reliability_action}. ``estimate``
#: and ``moe`` are nullable because provider-suppressed upstream values stay
#: missing (ADR-0004) and quantities without sampling error carry no MOE;
#: ``reliability_action`` is never null.
ANALYTIC_TABLE = SourceContract(
    name="analytic_table",
    columns=(
        ColumnSpec("geoid", "str", nullable=False),
        ColumnSpec("metric_id", "str", nullable=False),
        ColumnSpec("category", "str"),
        ColumnSpec("mode", "str"),
        ColumnSpec("estimate", "float"),
        ColumnSpec("moe", "float", minimum=0.0),
        ColumnSpec("cv_tier", "int", minimum=1),
        ColumnSpec("reliability_action", "str", nullable=False, allowed=RELIABILITY_ACTIONS),
        ColumnSpec("schema_version", "int", nullable=False, minimum=1),
        ColumnSpec("methods_version", "str", nullable=False),
    ),
)
