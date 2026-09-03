"""EP-4b runner unit tests: registry rules, fingerprints, skip / resume / cancel, status, verify.

These use a tiny three-stage pipeline of pure Python stages so the runner's
semantics are tested without the fixture's geo stack; the fixture pipeline
itself is covered by ``tests/integration/test_fixture_pipeline.py``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from phillysim import runner
from phillysim.runner import (
    DONE,
    FAILED,
    FRESH,
    INCOMPLETE,
    MISSING,
    STALE,
    MissingInputError,
    State,
    StateError,
    digest_tree,
    fingerprint,
    load_state,
    save_state,
    status,
    verify_state,
)
from phillysim.stages import (
    CancelledError,
    CancelToken,
    Pipeline,
    PipelineError,
    Stage,
    StageContext,
    StageError,
    parse_params,
)

RAW = "raw/src/2026-01-01"
UPPER = "intermediate/upper.txt"
COUNT = "curated/count.json"
OUT = "public/out.txt"


def _upper(ctx: StageContext) -> None:
    text = (ctx.input(RAW) / "words.txt").read_text("utf-8")
    ctx.checkpoint()
    ctx.output(UPPER).write_text(text.upper(), "utf-8")


def _count(ctx: StageContext) -> None:
    words = ctx.input(UPPER).read_text("utf-8").split()
    payload = {"words": len(words), "suffix": ctx.params["suffix"]}
    ctx.output(COUNT).write_text(json.dumps(payload, sort_keys=True), "utf-8")


def _publish(ctx: StageContext) -> None:
    payload = json.loads(ctx.input(COUNT).read_text("utf-8"))
    ctx.output(OUT).write_text(f"{payload['words']}{payload['suffix']}\n", "utf-8")


def make_pipeline(count_fn=_count, upper_fn=_upper) -> Pipeline:
    return Pipeline(
        "toy",
        [
            Stage("upper", upper_fn, inputs=(RAW,), outputs=(UPPER,)),
            Stage("count", count_fn, inputs=(UPPER,), outputs=(COUNT,), params={"suffix": "!"}),
            Stage("publish", _publish, inputs=(COUNT,), outputs=(OUT,)),
        ],
    )


@pytest.fixture
def root(tmp_path: Path) -> Path:
    data_root = tmp_path / "data"
    snapshot = data_root / RAW
    snapshot.mkdir(parents=True)
    (snapshot / "words.txt").write_text("one two three\n", "utf-8")
    return data_root


# --- registry rules ---------------------------------------------------------------------


def test_pipeline_rejects_bad_wiring() -> None:
    def noop(ctx: StageContext) -> None:
        pass

    with pytest.raises(PipelineError, match="produced by no earlier stage"):
        Pipeline("p", [Stage("a", noop, inputs=("intermediate/x",), outputs=("curated/y",))])
    with pytest.raises(PipelineError, match="produced by both"):
        Pipeline(
            "p",
            [
                Stage("a", noop, outputs=("curated/y",)),
                Stage("b", noop, outputs=("curated/y",)),
            ],
        )
    with pytest.raises(PipelineError, match="duplicate stage name"):
        Pipeline(
            "p",
            [Stage("a", noop, outputs=("curated/y",)), Stage("a", noop, outputs=("curated/z",))],
        )
    with pytest.raises(PipelineError, match="zone name"):
        Stage("a", noop, outputs=("elsewhere/y",))
    with pytest.raises(PipelineError, match="relative POSIX"):
        Stage("a", noop, outputs=("/curated/y",))
    with pytest.raises(PipelineError, match=r"'\.' or '\.\.'"):
        Stage("a", noop, outputs=("curated/../y",))
    with pytest.raises(PipelineError, match="at least one output"):
        Stage("a", noop)
    with pytest.raises(PipelineError, match="JSON-serializable"):
        Stage("a", noop, outputs=("curated/y",), params={"p": object()})
    with pytest.raises(PipelineError, match="invalid stage name"):
        Stage("Bad-Name", noop, outputs=("curated/y",))


def test_param_overrides_and_parsing() -> None:
    pipeline = make_pipeline()
    assert parse_params(["count.suffix=?", "count.n=3", "count.flag=true", 'count.s="3"']) == {
        "count": {"suffix": "?", "n": 3, "flag": True, "s": "3"}
    }
    changed = pipeline.with_params({"count": {"suffix": "?"}})
    assert changed["count"].params == {"suffix": "?"}
    assert pipeline["count"].params == {"suffix": "!"}, "with_params must not mutate"
    with pytest.raises(PipelineError, match="no parameter"):
        pipeline.with_params({"count": {"unknown": 1}})
    with pytest.raises(PipelineError, match="no such stage"):
        pipeline.with_params({"nope": {"suffix": 1}})
    with pytest.raises(PipelineError, match="stage.key=value"):
        parse_params(["count=1"])
    assert pipeline.through("count") == pipeline.stages[:2]
    assert pipeline.producer(UPPER) == "upper" and pipeline.producer(RAW) is None


# --- fingerprints -------------------------------------------------------------------------


def test_fingerprint_is_content_hash_plus_params(root: Path) -> None:
    pipeline = make_pipeline()
    fp1, inputs = fingerprint(root, pipeline["upper"])
    assert inputs == {RAW: digest_tree(root / RAW)}
    (root / RAW / "words.txt").write_text("one two three\n", "utf-8")  # same content, new mtime
    assert fingerprint(root, pipeline["upper"])[0] == fp1
    (root / RAW / "words.txt").write_text("one two\n", "utf-8")
    assert fingerprint(root, pipeline["upper"])[0] != fp1
    changed = pipeline.with_params({"count": {"suffix": "?"}})
    (root / UPPER).parent.mkdir(parents=True)
    (root / UPPER).write_text("X", "utf-8")
    assert fingerprint(root, changed["count"])[0] != fingerprint(root, pipeline["count"])[0]
    with pytest.raises(MissingInputError, match="absent"):
        fingerprint(root, pipeline["publish"])


def test_digest_tree_is_platform_independent_and_ignores_layout_noise(tmp_path: Path) -> None:
    a, b = tmp_path / "a", tmp_path / "b"
    for base in (a, b):
        (base / "sub").mkdir(parents=True)
        (base / "sub" / "x.txt").write_bytes(b"x")
        (base / "y.txt").write_bytes(b"y")
    assert digest_tree(a) == digest_tree(b)
    (b / "sub" / "x.txt").write_bytes(b"z")
    assert digest_tree(a) != digest_tree(b)


# --- run / skip / resume ---------------------------------------------------------------


def test_first_run_runs_all_and_second_run_skips_all(root: Path) -> None:
    pipeline = make_pipeline()
    first = runner.run(root, pipeline)
    assert first.ran == ["upper", "count", "publish"] and first.skipped == []
    assert (root / OUT).read_text("utf-8") == "3!\n"
    assert not any((root / "cache" / "staging").iterdir()), "staging cleaned after each stage"
    second = runner.run(root, pipeline)
    assert second.ran == [] and second.skipped == ["upper", "count", "publish"]
    assert all(row.status == FRESH for row in status(root, pipeline))


def test_parameter_change_reruns_only_dependents(root: Path) -> None:
    pipeline = make_pipeline()
    runner.run(root, pipeline)
    changed = pipeline.with_params({"count": {"suffix": "?"}})
    rows = {row.name: row for row in status(root, changed)}
    assert rows["upper"].status == FRESH
    assert rows["count"].status == STALE and "parameters" in rows["count"].detail
    assert rows["publish"].status == FRESH, "publish's own inputs have not changed yet"
    report = runner.run(root, changed)
    assert report.skipped == ["upper"] and report.ran == ["count", "publish"]
    assert (root / OUT).read_text("utf-8") == "3?\n"


def test_newly_declared_output_makes_a_done_stage_stale(root: Path) -> None:
    """A stage that now declares an output it never produced (a source registered after
    the last run, EP-6) is stale even though its recorded outputs are intact."""
    runner.run(root, make_pipeline())
    extra = "intermediate/extra.txt"

    def count_with_extra(ctx: StageContext) -> None:
        _count(ctx)
        ctx.output(extra).write_text("extra\n", "utf-8")

    grown = Pipeline(
        "toy",
        [
            Stage("upper", _upper, inputs=(RAW,), outputs=(UPPER,)),
            Stage(
                "count",
                count_with_extra,
                inputs=(UPPER,),
                outputs=(COUNT, extra),
                params={"suffix": "!"},
            ),
            Stage("publish", _publish, inputs=(COUNT,), outputs=(OUT,)),
        ],
    )
    rows = {row.name: row for row in status(root, grown)}
    assert rows["count"].status == STALE and rows["count"].detail == "changed: declared outputs"
    report = runner.run(root, grown)
    assert report.ran == ["count"] and report.skipped == ["upper", "publish"]
    assert (root / extra).read_text("utf-8") == "extra\n"
    assert all(row.status == FRESH for row in status(root, grown))


def test_input_change_reruns_downstream_only_where_content_changed(root: Path) -> None:
    pipeline = make_pipeline()
    runner.run(root, pipeline)
    (root / RAW / "words.txt").write_text("ONE TWO THREE\n", "utf-8")  # upper() output unchanged
    report = runner.run(root, pipeline)
    assert report.ran == ["upper"] and report.skipped == ["count", "publish"]
    (root / RAW / "words.txt").write_text("one two\n", "utf-8")
    report = runner.run(root, pipeline)
    assert report.ran == ["upper", "count", "publish"]
    assert (root / OUT).read_text("utf-8") == "2!\n"


def test_through_runs_a_prefix_only(root: Path) -> None:
    pipeline = make_pipeline()
    report = runner.run(root, pipeline, through="count")
    assert report.ran == ["upper", "count"]
    assert not (root / OUT).exists()
    assert {r.name: r.status for r in status(root, pipeline)}["publish"] == MISSING


def test_injected_failure_leaves_a_coherent_state_and_next_run_resumes(root: Path) -> None:
    calls = {"count": 0}

    def failing_count(ctx: StageContext) -> None:
        calls["count"] += 1
        ctx.output(COUNT).write_text("partial", "utf-8")  # written to staging only
        if calls["count"] == 1:
            raise RuntimeError("injected mid-stage failure")
        _count(ctx)

    pipeline = make_pipeline(count_fn=failing_count)
    with pytest.raises(StageError, match="injected mid-stage failure"):
        runner.run(root, pipeline)
    assert (root / UPPER).exists()
    assert not (root / COUNT).exists(), "no partially written file in a zone"
    assert not (root / "cache" / "staging" / "count").exists(), "staging discarded"
    state = load_state(root)
    assert state is not None and state.stages["count"].status == FAILED
    assert "injected mid-stage failure" in (state.stages["count"].error or "")
    assert "publish" not in state.stages

    report = verify_state(root, pipeline)
    assert not report.ok and report.problems == ()
    assert report.incomplete == ("count",)
    assert [v.verdict for v in report.verdicts] == ["ok", "incomplete", "missing"]
    rows = {r.name: r.status for r in status(root, pipeline)}
    assert rows == {"upper": FRESH, "count": INCOMPLETE, "publish": MISSING}

    resumed = runner.run(root, pipeline)
    assert resumed.skipped == ["upper"] and resumed.ran == ["count", "publish"]
    assert verify_state(root, pipeline).ok
    assert (root / OUT).read_text("utf-8") == "3!\n"


def test_cancel_between_stages_and_at_a_checkpoint(root: Path) -> None:
    token = CancelToken()

    def cancelling_upper(ctx: StageContext) -> None:
        token.cancel()
        _upper(ctx)  # _upper calls ctx.checkpoint() before writing

    pipeline = make_pipeline(upper_fn=cancelling_upper)
    with pytest.raises(CancelledError):
        runner.run(root, pipeline, cancel=token)
    state = load_state(root)
    assert state is not None and state.stages["upper"].status == runner.CANCELLED
    assert not (root / UPPER).exists()
    assert verify_state(root, pipeline).incomplete == ("upper",)

    # Between stages: cancel after 'upper' completes, before 'count' starts.
    calls: list[str] = []
    token2 = CancelToken()

    def upper_then_cancel(ctx: StageContext) -> None:
        _upper(ctx)
        calls.append("upper")
        token2.cancel()

    pipeline2 = make_pipeline(upper_fn=upper_then_cancel)
    with pytest.raises(CancelledError):
        runner.run(root, pipeline2, cancel=token2)
    assert calls == ["upper"]
    state = load_state(root)
    assert state is not None and state.stages["upper"].status == DONE
    assert "count" not in state.stages, "cancellation between stages starts nothing"
    assert (root / UPPER).exists()
    assert runner.run(root, pipeline2).ran == ["count", "publish"]


def test_stage_that_forgets_an_output_fails(root: Path) -> None:
    def lazy(ctx: StageContext) -> None:
        pass

    pipeline = make_pipeline(upper_fn=lazy)
    with pytest.raises(StageError, match="without producing output"):
        runner.run(root, pipeline)
    assert load_state(root).stages["upper"].status == FAILED  # type: ignore[union-attr]


def test_raw_zone_is_immutable_for_stage_outputs(root: Path) -> None:
    target = "raw/other/2026-01-01"

    def acquire(ctx: StageContext) -> None:
        out = ctx.output(target)
        out.mkdir(parents=True)
        (out / "data.txt").write_text(ctx.params["text"], "utf-8")

    pipeline = Pipeline("acq", [Stage("acquire", acquire, outputs=(target,), params={"text": "a"})])
    runner.run(root, pipeline)
    assert runner.run(root, pipeline).skipped == ["acquire"]
    # Identical content re-produced: a no-op (rerun via a param that keeps the content).
    same = Pipeline("acq", [Stage("acquire", acquire, outputs=(target,), params={"text": "a"})])
    assert runner.run(root, same).skipped == ["acquire"]
    changed = pipeline.with_params({"acquire": {"text": "b"}})
    with pytest.raises(StageError, match="immutable raw zone"):
        runner.run(root, changed)
    assert (root / target / "data.txt").read_text("utf-8") == "a"


def test_state_file_holds_no_absolute_paths(root: Path) -> None:
    def failing(ctx: StageContext) -> None:
        # A Windows OSError quotes its paths in repr form (doubled backslashes); the
        # first real acquisition (EP-5a) leaked the data root that way.
        raise PermissionError(f"[WinError 5] Access is denied: {str(ctx.root / 'raw')!r}")

    pipeline = make_pipeline(upper_fn=failing)
    with pytest.raises(StageError):
        runner.run(root, pipeline)
    text = (root / runner.STATE_FILE).read_text("utf-8")
    assert str(root) not in text and root.as_posix() not in text
    assert str(root).replace("\\", "\\\\") not in text
    assert "<data-root>" in text
    payload = json.loads(text)
    assert payload["schema_version"] == 1 and payload["pipeline"] == "toy"
    assert "Access is denied: '<data-root>" in payload["stages"]["upper"]["error"]


def test_install_retries_a_transient_permission_error(root: Path, monkeypatch) -> None:
    """A virus scanner holding a just-written file made the first real install fail (EP-5a);
    the rename is retried a bounded number of times before the stage is failed."""
    real_replace = runner.os.replace
    failures = {"left": 2}
    sleeps: list[float] = []

    def flaky_replace(src, dst):
        if str(dst).endswith("upper.txt") and failures["left"]:
            failures["left"] -= 1
            raise PermissionError("[WinError 5] Access is denied")
        return real_replace(src, dst)

    monkeypatch.setattr(runner.os, "replace", flaky_replace)
    monkeypatch.setattr(runner.time, "sleep", sleeps.append)
    report = runner.run(root, make_pipeline())
    assert report.ran == ["upper", "count", "publish"]
    assert sleeps == [0.25, 0.5] and (root / UPPER).read_text("utf-8") == "ONE TWO THREE\n"

    failures["left"] = 99  # never succeeds: the stage fails after the bounded retries
    (root / RAW / "words.txt").write_text("four five\n", "utf-8")
    with pytest.raises(StageError, match="Access is denied"):
        runner.run(root, make_pipeline())
    assert len(sleeps) == 2 + 9


# --- status and verify edge cases ----------------------------------------------------------


def test_status_detects_missing_and_altered_outputs(root: Path) -> None:
    pipeline = make_pipeline()
    runner.run(root, pipeline)
    (root / COUNT).write_text("tampered", "utf-8")
    rows = {r.name: r for r in status(root, pipeline)}
    assert rows["count"].status == STALE and "altered" in rows["count"].detail
    assert rows["publish"].status == STALE and COUNT in rows["publish"].detail
    report = verify_state(root, pipeline)
    assert [v.verdict for v in report.verdicts] == ["ok", "broken", "ok"]
    assert not report.ok and report.broken == ("count",)
    (root / COUNT).unlink()
    rows = {r.name: r for r in status(root, pipeline)}
    assert rows["count"].status == MISSING and "absent" in rows["count"].detail
    assert rows["publish"].status == STALE
    assert runner.run(root, pipeline).ran == ["count"], "count re-made; publish input unchanged"


def test_verify_flags_leftover_staging_and_unknown_records(root: Path) -> None:
    pipeline = make_pipeline()
    runner.run(root, pipeline)
    (root / "cache" / "staging" / "count").mkdir(parents=True)
    state = load_state(root)
    assert state is not None
    state.stages["ghost"] = state.stages["count"]
    save_state(root, state)
    report = verify_state(root, pipeline)
    assert not report.ok
    assert any("leftover staging" in p and "count" in p for p in report.problems)
    assert any("unknown stage 'ghost'" in p for p in report.problems)


def test_verify_without_state_reports_every_stage_missing(root: Path) -> None:
    report = verify_state(root, make_pipeline())
    assert report.problems == () and report.incomplete == ()
    assert all(v.verdict == "missing" for v in report.verdicts)
    assert report.ok, "nothing has run: coherent, just empty"


def test_malformed_or_foreign_state_is_refused(root: Path) -> None:
    pipeline = make_pipeline()
    (root / runner.STATE_FILE).write_text("{not json", "utf-8")
    with pytest.raises(StateError, match="not valid JSON"):
        status(root, pipeline)
    assert verify_state(root, pipeline).problems[0].startswith("state file is not valid JSON")
    save_state(root, State(pipeline="other"))
    with pytest.raises(StateError, match="belongs to pipeline 'other'"):
        runner.run(root, pipeline)
    with pytest.raises(StateError):
        status(root, pipeline)
    assert "belongs to pipeline 'other'" in verify_state(root, pipeline).problems[0]
    (root / runner.STATE_FILE).write_text(json.dumps({"schema_version": 99, "pipeline": "toy"}))
    with pytest.raises(StateError, match="schema_version"):
        load_state(root)
