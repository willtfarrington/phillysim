"""The contract harness itself: every check kind fires on an injected violation and stays quiet
on a conforming table. These are the harness's own negative tests, independent of any fixture."""

from __future__ import annotations

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Point, Polygon

from phillysim.contracts import (
    ANALYTIC_TABLE,
    ColumnSpec,
    ContractViolationError,
    GeometrySpec,
    SourceContract,
    check_frame,
    enforce,
)

CONTRACT = SourceContract(
    name="demo",
    columns=(
        ColumnSpec("id", "str", nullable=False, pattern=r"[A-Z]\d"),
        ColumnSpec("count", "int", nullable=False, minimum=0),
        ColumnSpec("note", "str"),
        ColumnSpec("kind", "str", allowed=frozenset({"a", "b"})),
    ),
    key="id",
    geometry=GeometrySpec(types=frozenset({"Point"}), bounds=(0.0, 0.0, 10.0, 10.0)),
    license_buckets=frozenset({"A"}),
    min_rows=2,
    max_rows=5,
)
MANIFEST = {"license_bucket": "A", "schema_version": 1}


def conforming() -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(
        {
            "id": ["A1", "B2", "C3"],
            "count": [1, 2, 3],
            "note": ["x", None, "z"],
            "kind": ["a", "b", None],
        },
        geometry=[Point(1, 1), Point(2, 2), Point(3, 3)],
        crs="EPSG:4326",
    )


def checks(frame: pd.DataFrame, manifest=MANIFEST) -> set[str]:
    return {violation.check for violation in check_frame(CONTRACT, frame, manifest)}


def test_conforming_table_has_no_violations() -> None:
    assert check_frame(CONTRACT, conforming(), MANIFEST) == []
    enforce(CONTRACT, conforming(), MANIFEST)  # must not raise


def test_enforce_raises_with_every_violation_listed() -> None:
    frame = conforming().drop(columns=["count"])
    frame.loc[0, "id"] = None
    with pytest.raises(ContractViolationError) as excinfo:
        enforce(CONTRACT, frame, {"license_bucket": "B", "schema_version": 2})
    kinds = {violation.check for violation in excinfo.value.violations}
    assert kinds == {"schema", "key", "license"}
    assert "missing column 'count'" in str(excinfo.value)


# --- schema ---------------------------------------------------------------------


def test_missing_column() -> None:
    assert "schema" in checks(conforming().drop(columns=["note"]))


def test_wrong_kind() -> None:
    frame = conforming()
    frame["count"] = frame["count"].astype(str)
    assert "schema" in checks(frame)


def test_null_in_non_nullable_column() -> None:
    frame = conforming()
    frame["count"] = pd.array([1, None, 3], dtype="Int64")
    assert "schema" in checks(frame)


def test_nullable_int_dtype_is_accepted() -> None:
    frame = conforming()
    frame["count"] = pd.array([1, 2, 3], dtype="Int64")
    assert checks(frame) == set()


def test_all_null_string_column_is_accepted() -> None:
    frame = conforming()
    frame["note"] = None
    assert checks(frame) == set()


def test_minimum_violation() -> None:
    frame = conforming()
    frame.loc[1, "count"] = -1
    assert "schema" in checks(frame)


def test_allowed_set_violation() -> None:
    frame = conforming()
    frame.loc[0, "kind"] = "zzz"
    assert "schema" in checks(frame)


def test_pattern_violation() -> None:
    frame = conforming()
    frame.loc[0, "id"] = "A10"
    assert "schema" in checks(frame)


def test_bad_kind_name_is_rejected_at_definition() -> None:
    with pytest.raises(ValueError):
        ColumnSpec("x", "decimal")


# --- key / rows -----------------------------------------------------------------


def test_duplicate_key() -> None:
    frame = pd.concat([conforming(), conforming().iloc[[0]]], ignore_index=True)
    assert "key" in checks(frame)


def test_null_key() -> None:
    frame = conforming()
    frame.loc[0, "id"] = None
    assert "key" in checks(frame)


def test_too_few_rows() -> None:
    assert "rows" in checks(conforming().iloc[[0]])


def test_too_many_rows() -> None:
    frame = pd.concat([conforming(), conforming()], ignore_index=True)
    frame["id"] = [f"{letter}{i}" for i, letter in enumerate("ABCDEF")]
    assert "rows" in checks(frame)


# --- license ----------------------------------------------------------------------


def test_license_bucket_violation() -> None:
    assert "license" in checks(conforming(), {"license_bucket": "Z", "schema_version": 1})


def test_schema_version_violation() -> None:
    assert "license" in checks(conforming(), {"license_bucket": "A", "schema_version": 2})


def test_no_manifest_skips_license_checks() -> None:
    assert check_frame(CONTRACT, conforming(), None) == []


# --- geometry -------------------------------------------------------------------


def test_plain_dataframe_fails_geometry_contract() -> None:
    assert "geometry" in checks(pd.DataFrame(conforming().drop(columns="geometry")))


def test_wrong_crs() -> None:
    assert "geometry" in checks(conforming().set_crs("EPSG:3857", allow_override=True))


def test_missing_crs() -> None:
    assert "geometry" in checks(conforming().set_crs(None, allow_override=True))


def test_wrong_geometry_type() -> None:
    frame = conforming()
    frame.loc[0, "geometry"] = Polygon([(1, 1), (2, 1), (2, 2), (1, 1)])
    assert "geometry" in checks(frame)


def test_invalid_geometry() -> None:
    polygon_contract = SourceContract(
        name="poly",
        columns=(),
        geometry=GeometrySpec(types=frozenset({"Polygon"})),
    )
    bowtie = Polygon([(0, 0), (1, 1), (1, 0), (0, 1)])
    frame = gpd.GeoDataFrame(geometry=[bowtie], crs="EPSG:4326")
    violations = check_frame(polygon_contract, frame)
    assert [v.check for v in violations] == ["geometry"]
    assert "Self-intersection" in violations[0].detail


def test_out_of_bounds() -> None:
    frame = conforming()
    frame.loc[0, "geometry"] = Point(50, 50)
    assert "geometry" in checks(frame)


def test_empty_geometry() -> None:
    frame = conforming()
    frame.loc[0, "geometry"] = None
    assert "geometry" in checks(frame)


# --- the locked analytic-table contract --------------------------------------------


def test_analytic_contract_accepts_minimal_conforming_row() -> None:
    frame = pd.DataFrame(
        {
            "geoid": ["99999000100"],
            "metric_id": ["population_total"],
            "category": [None],
            "mode": [None],
            "estimate": [3200.0],
            "moe": [210.0],
            "cv_tier": pd.array([1], dtype="Int64"),
            "reliability_action": ["none"],
            "schema_version": [1],
            "methods_version": ["x"],
        }
    )
    assert check_frame(ANALYTIC_TABLE, frame) == []
    frame.loc[0, "reliability_action"] = "suppress"
    assert {v.check for v in check_frame(ANALYTIC_TABLE, frame)} == {"schema"}
