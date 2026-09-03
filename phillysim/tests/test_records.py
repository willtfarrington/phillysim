"""EP-13: run plans, run IDs, the scrub, and the two output digests."""

from __future__ import annotations

import json
import math
import re
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from phillysim.routing import records
from phillysim.routing.records import (
    OUTCOMES,
    Point,
    RunPlan,
    RunRecord,
    canonical_rows,
    canonical_value,
    canonical_value_digest,
    outputs_agree,
    read_output,
    run_id,
    scrub,
    scrub_value,
    write_output,
)


def plan(**overrides) -> RunPlan:
    base = dict(
        slug="smoke",
        modes=("walk", "walk_transit"),
        speed_walking_kmh=4.8,
        departure="2026-09-23T08:00",
        time_zone="America/New_York",
        window_minutes=60,
        percentiles=(50, 85),
        max_time_minutes=120,
        origins=(Point("42101000500", -75.156452, 39.95196),),
        destinations=(Point("snap_retailers:1298051", -75.15858, 39.95055),),
        inputs={
            "osm": "intermediate/network/clip.osm.pbf",
            "gtfs_bus": "intermediate/network/b.zip",
        },
        origins_description="one tract",
        destinations_description="one retailer",
    )
    base.update(overrides)
    return RunPlan(**base)


def test_plan_round_trips_and_counts() -> None:
    p = plan()
    data = p.to_dict()
    assert data["origins"]["count"] == 1 and data["destinations"]["count"] == 1
    assert data["origins"]["points"][0] == {"id": "42101000500", "lon": -75.156452, "lat": 39.95196}
    assert RunPlan.from_dict(json.loads(json.dumps(data))) == p


@pytest.mark.parametrize(
    "bad",
    [
        {"slug": "Smoke Run"},
        {"slug": ""},
        {"modes": ("drive",)},
        {"modes": ()},
        {"window_minutes": 0},
        {"speed_walking_kmh": 0},
        {"departure": "2026-09-23 08:00"},
        {"origins": ()},
        {"inputs": {"osm": "../outside.pbf"}},
        {"inputs": {"osm": "C:/abs/clip.pbf"}},
    ],
)
def test_plan_rules(bad: dict) -> None:
    with pytest.raises(ValueError):
        plan(**bad)


def test_run_id_is_utc_timestamp_and_slug() -> None:
    when = datetime(2026, 9, 3, 21, 5, 9, tzinfo=UTC)
    assert run_id("smoke", when) == "20260903T210509Z-smoke"
    assert re.fullmatch(r"\d{8}T\d{6}Z-smoke-single", run_id("smoke-single"))
    with pytest.raises(ValueError):
        run_id("bad slug")


def test_outcomes_are_the_four_and_the_record_refuses_others() -> None:
    assert OUTCOMES == ("completed", "killed-rss", "failed", "cancelled")
    with pytest.raises(ValueError):
        RunRecord("id", "smoke", "exploded", "now", None, None, None)
    record = RunRecord("id", "smoke", "completed", "now", "later", 1.5, 0)
    assert record.to_dict()["schema_version"] == 1 and record.to_dict()["outcome"] == "completed"


def test_scrub_replaces_every_form_of_every_root(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    repo = tmp_path
    text = (
        f"native {data_root}; posix {data_root.as_posix()}; "
        f"repr {str(data_root).replace(chr(92), chr(92) * 2)}; repo {repo}"
    )
    out = scrub(text, {"<data-root>": data_root, "<repo-root>": repo})
    assert out == "native <data-root>; posix <data-root>; repr <data-root>; repo <repo-root>"
    assert str(tmp_path) not in out
    nested = scrub_value(
        {"a": [str(data_root), 3], "b": {"c": repo.as_posix()}},
        {"<data-root>": data_root, "<repo-root>": repo},
    )
    assert nested == {"a": ["<data-root>", 3], "b": {"c": "<repo-root>"}}


def test_canonical_values() -> None:
    assert canonical_value(3.0) == 3 and isinstance(canonical_value(3.0), int)
    assert canonical_value(float("nan")) is None and canonical_value(None) is None
    assert canonical_value(np.float64(12.0)) == 12
    assert canonical_value(np.int64(7)) == 7
    assert canonical_value(2.123456789) == 2.123457
    assert canonical_value("x") == "x"
    assert math.isnan(float("nan"))  # sanity for the reader


def frame(rows):
    return pd.DataFrame(
        rows, columns=["mode", "from_id", "to_id", "travel_time_p50", "travel_time_p85"]
    )


def test_canonical_digest_ignores_row_and_column_order_and_float_formatting() -> None:
    a = frame(
        [
            ("walk", "o", "d1", 12.0, 14.0),
            ("walk", "o", "d2", float("nan"), float("nan")),
            ("walk_transit", "o", "d1", 9.0, 11.0),
        ]
    )
    b = a.iloc[::-1].reset_index(drop=True)[
        ["travel_time_p85", "to_id", "mode", "from_id", "travel_time_p50"]
    ]
    b["travel_time_p50"] = b["travel_time_p50"].astype("Int64").astype("float64")
    assert canonical_value_digest(a) == canonical_value_digest(b)
    c = a.copy()
    c.loc[0, "travel_time_p50"] = 13.0
    assert canonical_value_digest(a) != canonical_value_digest(c)
    rows = canonical_rows(a)
    assert rows[0] == {
        "from_id": "o",
        "mode": "walk",
        "to_id": "d1",
        "travel_time_p50": 12,
        "travel_time_p85": 14,
    }
    assert rows[1]["travel_time_p50"] is None
    with pytest.raises(ValueError, match="key column"):
        canonical_value_digest(a.drop(columns=["mode"]))


def test_write_output_is_byte_identical_for_value_identical_frames(tmp_path: Path) -> None:
    a = frame([("walk", "o", "d1", 12.0, 14.0), ("walk", "o", "d2", float("nan"), 30.0)])
    b = a.iloc[::-1].reset_index(drop=True)
    write_output(a, tmp_path / "a.csv")
    write_output(b, tmp_path / "b.csv")
    assert (tmp_path / "a.csv").read_bytes() == (tmp_path / "b.csv").read_bytes()
    text = (tmp_path / "a.csv").read_text("utf-8")
    assert text.splitlines()[0] == "mode,from_id,to_id,travel_time_p50,travel_time_p85"
    assert text.splitlines()[1] == "walk,o,d1,12,14"
    assert text.splitlines()[2] == "walk,o,d2,,30"
    back = read_output(tmp_path / "a.csv")
    assert canonical_value_digest(back) == canonical_value_digest(a)


def test_outputs_agree() -> None:
    same = [{"output": {"canonical_value_sha256": "a"}}] * 3
    assert outputs_agree(same) == (True, ["a", "a", "a"])
    assert (
        outputs_agree(
            [
                {"output": {"canonical_value_sha256": "a"}},
                {"output": {"canonical_value_sha256": "b"}},
            ]
        )[0]
        is False
    )
    assert outputs_agree([{"output": {"canonical_value_sha256": "a"}}, {"output": None}]) == (
        False,
        ["a", None],
    )
    assert outputs_agree([])[0] is False


def test_input_digests_and_list_runs(tmp_path: Path) -> None:
    (tmp_path / "intermediate").mkdir()
    (tmp_path / "intermediate" / "x.bin").write_bytes(b"abc")
    digests = records.input_digests(tmp_path, {"osm": "intermediate/x.bin"})
    assert digests["osm"]["bytes"] == 3 and digests["osm"]["path"] == "intermediate/x.bin"
    assert digests["osm"]["sha256"].startswith("ba7816bf")
    assert records.list_runs(tmp_path) == []
    records.run_dir(tmp_path, "20260903T000000Z-smoke").mkdir(parents=True)
    assert [p.name for p in records.list_runs(tmp_path)] == ["20260903T000000Z-smoke"]
