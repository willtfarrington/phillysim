# EP-4b — Stage runner: fingerprints, resume/cancel, preflight, `phillysim run/status/verify`

**Status:** [ ] planned · **Milestone:** M1 · **Effort:** S (1 session, medium confidence) · **Parallel with:** — · **Split from:** EP-4 (2026-09-02; EP-4a is the other half)

## Outcome & value
The execution half of the pipeline backbone: an idempotent stage runner over
EP-4a's zones and manifests, with input fingerprints (unchanged inputs →
skipped stage), resume/cancel semantics that always leave a state `verify`
can report as coherent, preflight checks (disk/RAM/dependency versions)
before a run, and the CLI verbs `phillysim run/status/verify --fixture` —
proven end-to-end on tinycity so that M1's go/no-go criterion
(`phillysim run --fixture` green in offline CI) is met.

## Scope
- in: stage registry + runner, fingerprints, skip/resume/cancel, preflight,
  `run`/`status`/`verify` verbs, fixture stage implementations that carry
  tinycity's raw snapshots through every zone to the expected tables,
  integration suite in CI.
- out (explicit non-scope): real adapters and real stage logic (EP-5+);
  parallel stage execution; anything beyond content-hash fingerprints.

## Prerequisites & locked decisions
- prerequisites: EP-4a.
- locked decisions honored: architecture.md eleven-stage fingerprint-DAG
  semantics; B3-07 CLI shape (plain Typer-style stages, no orchestrator);
  preflight thresholds from architecture.md resource budgets (the ≥150 GB
  free-disk rule applies to real runs; the fixture path uses a
  fixture-scale threshold and says so).
- dependencies: none external.

## Safety preconditions
Standing policy (see EP-1). Packet-specific: a cancelled or crashed stage
never leaves a partially written file in a zone (write to a temp path, then
atomic rename); stage-state files contain no machine identifiers or absolute
paths; `data/` gitignored.

## Likely components & contracts (proposed)
`src/phillysim/{stages,runner,preflight}.py`; fixture stages under
`src/phillysim/fixtures/` that reuse EP-3's expected tables as oracles; CLI
verbs `run`, `status`, `verify` with `--fixture`; `tests/test_runner.py`,
`tests/test_preflight.py`, `tests/integration/test_fixture_pipeline.py`.
Contract: a stage declares inputs, outputs, and parameters; fingerprint =
content hash of inputs + parameters; the runner records fingerprints per
stage in a state file under the data root.

## Implementation notes
Anything fancier than content-hash + params is out of scope. Cancellation is
a cooperative flag checked between stages and at safe points inside a stage;
the kill test uses an injected failure (raise inside a stage) rather than
process signals so it is deterministic on Windows and Linux. `status` prints
per-stage fresh/stale/missing; `verify` combines EP-4a's snapshot checks
with stage-state coherence. The fixture pipeline's outputs must equal EP-3's
`expected/` tables by content.

## Acceptance criteria & evidence
- [x] `phillysim run --fixture` completes end-to-end; a second run skips
      every stage; changing one parameter re-runs only the dependent stages.
      — `test_run_fixture_end_to_end_matches_golden_tables` (11 ran, then
      "0 stage(s) ran, 11 skipped"; the four curated outputs equal
      `expected/*.parquet` by content; `status` 11 fresh; `verify` 8 of 8
      snapshots + 11 of 11 stages) and
      `test_parameter_change_reruns_only_dependent_stages`
      (`--param metrics.methods_version=…` → metrics + publish only;
      `--param travel_times.censor_min=30` → travel_times + metrics, publish
      skipped because the metrics content did not change). Runner-level:
      `test_parameter_change_reruns_only_dependents`,
      `test_input_change_reruns_downstream_only_where_content_changed`.
- [x] Injected mid-stage failure → `phillysim verify --fixture` reports a
      coherent state naming the incomplete stage; the next `run` resumes
      from it. —
      `test_injected_failure_then_verify_names_the_stage_and_run_resumes`:
      a raise inside `hours` after writing to staging leaves no file in
      `curated/`; `verify --fixture` prints `stage hours: incomplete (failed:
      RuntimeError: injected mid-stage failure)` and `6 of 11 stage(s) done
      and intact; incomplete: hours` with no coherence problem; the next
      `run` skips 6 and runs 5, then `verify` is green. Runner-level:
      `test_injected_failure_leaves_a_coherent_state_and_next_run_resumes`,
      `test_cancel_between_stages_and_at_a_checkpoint`.
- [x] Preflight refuses to run when a simulated check fails (negative test)
      and reports all checks in one pass. —
      `test_simulated_failures_are_all_reported_in_one_pass` (all five checks
      fail together and are all listed), `test_one_failing_check_is_enough_to_refuse`,
      `test_cli_run_refuses_when_preflight_fails` (exit 1, every check
      printed, "fixture scale" named, data root not created).
- Evidence: `uv run pytest` → 240 passed locally (207 before the packet);
  CI runs `phillysim run/status/verify --fixture` on Windows + Linux
  (run ID in the handoff); M1 go/no-go criterion recorded as met in the
  handoff.

## Tests / validation
Integration suite on tinycity; runner unit tests; preflight negative tests;
`uv run pytest` green in CI.

## Resource budget
Trivial at fixture scale.

## Risks, rollback, stop condition
Fingerprint design churn → hold to content-hash + params. Stop if
end-to-end on the fixture needs stage logic that belongs to a real adapter
(EP-5+) — stub it with the expected table and record the stub in the
handoff.

## Documentation / ADR updates
Pipeline section in `phillysim/README.md` (verbs, zones, state file, how to
resume); `docs/data-dictionary.md` stage-state file shape; CHANGELOG; packet
row in `roadmap/README.md`, and the M1 heading there if the go/no-go
criterion is met.

## Handoff payload (fill at session end)
- packet ID + status; baseline/roadmap version
- files changed; commands/tests run + results
- resource observations
- decisions/ADRs made; unresolved risks/questions
- no-go areas touched? (must be none)
- `roadmap/README.md` packet row (and M1 status) updated
- exact next packet: EP-5 — after the first checkpoint packet if the owner
  authors one (milestones.md "Spikes & gates": every ~5 packets)
