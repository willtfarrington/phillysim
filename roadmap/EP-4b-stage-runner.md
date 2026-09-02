# EP-4b — Stage runner: fingerprints, resume/cancel, preflight, `phillysim run/status/verify`

**Status:** [x] 9a0a3dc · **Milestone:** M1 · **Effort:** S (1 session, medium confidence) · **Parallel with:** — · **Split from:** EP-4 (2026-09-02; EP-4a is the other half)

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

## Handoff payload (filled 2026-09-02)
- **Packet:** EP-4b — done at commit `9a0a3dc` (+ this status commit).
  Planning Baseline v1.0. CI run
  [33669100510](https://github.com/willtfarrington/phillysim/actions/runs/33669100510)
  on `9a0a3dc` green on `windows-latest` and `ubuntu-latest`, including the
  new `phillysim run --fixture`, `status --fixture`, and `verify --fixture`
  steps. **M1 go/no-go criterion met** (`phillysim run --fixture` green in
  offline CI); M1 recorded done in `roadmap/README.md`.
- **Files changed:** new `phillysim/src/phillysim/{stages,runner,preflight}.py`
  and `phillysim/src/phillysim/fixtures/pipeline.py`;
  `phillysim/src/phillysim/cli.py` (`run`, `status`; `verify` extended and
  retargeted; module docstring); `phillysim/src/phillysim/fixtures/tinycity.py`
  (polygon corners rounded); regenerated
  `phillysim/tests/fixtures/tinycity/{CHECKSUMS.txt,expected/tracts_spine.parquet}`;
  new `phillysim/tests/{test_runner,test_preflight}.py` and
  `phillysim/tests/integration/test_fixture_pipeline.py`;
  `phillysim/tests/test_manifest.py` (the fresh-generation `verify --fixture`
  test retired in favour of the integration suite); `.github/workflows/ci.yml`
  (three fixture-pipeline steps); `.gitignore` (`data/pipeline_state.json`,
  `data/fixture/`); `phillysim/README.md` (layout; "Pipeline: stages,
  fingerprints, state, resume" section); `docs/data-dictionary.md` (stage
  state file section); `CHANGELOG.md`; `roadmap/README.md` (packet row, M1
  heading and phase row, checkpoint note); this file.
- **Commands/tests run + results:** `uv run pytest` → 240 passed (207 before
  the packet; whole suite about seven seconds); `uv run ruff check .` and
  `ruff format --check .` clean; `pre-commit run --all-files` with the new
  files staged → all hooks passed; both fixture variants regenerated with
  `phillysim gen-tinycity` (34 / 30 files; only the spine golden and its
  checksum line changed); manual `phillysim run --fixture` in a scratch root:
  11 ran (about 0.5 s total), second run 0 ran / 11 skipped, `status` 11
  fresh, `verify` 8 of 8 snapshots + 11 of 11 stages, curated outputs equal
  the golden tables by content, `--param travel_times.censor_min=30` re-ran
  travel_times + metrics only; scan of the new files and the state file for
  usernames / absolute paths → none (the runner replaces the data root with
  `<data-root>` in recorded error text and a test pins it).
- **Resource observations:** trivial, as budgeted; single session. The
  fixture root is under 1 MB; preflight on this machine reported the real
  thresholds would also pass, but only the fixture-scale set is applied by
  `--fixture` and the report says so.
- **Decisions made (revisable, below ADR level):**
  - Fingerprint = SHA-256 of canonical JSON `{inputs: {path: digest}, params}`;
    a directory input's digest is the SHA-256 of its sorted `path␀digest`
    listing (platform-independent). No code hashing, no timestamps.
  - Skip rule = recorded fingerprint equals the current one *and* every
    recorded output is on disk with its recorded digest. Consequence:
    downstream stages re-run only when their inputs change *in content*, so
    a parameter change that leaves a stage's output identical stops the
    re-run cascade there (documented; the integration suite shows both the
    cascade and the stop).
  - Outputs are written to `cache/staging/<stage>/` and installed by
    `os.replace` per output after the stage function returns; the state
    file is rewritten atomically at every transition. A stage that returns
    normally is installed even if cancellation was requested meanwhile
    (cancellation is honoured between stages and at in-stage checkpoints,
    never by discarding finished work).
  - The raw zone is immutable under the runner: an output under `raw/` that
    already exists must be content-identical or the stage fails. The fixture
    `acquire` stage goes through `quarantine.admit` with allowlist
    `example.invalid` and fixture-scale `Limits`, so the invalid variant is
    quarantined at admission and `acquire` is recorded as failed
    (`test_invalid_variant_is_quarantined_at_acquire`).
  - `status` has four states: fresh / stale / missing (never run, or an
    output gone) / **incomplete** (failed or cancelled). `verify` exits 1
    for an incomplete or broken stage as well as for raw-zone problems; a
    partially run pipeline is reported as coherent-but-incomplete, naming
    the stage.
  - `--fixture` targets `<data root>/fixture/` (gitignored), the "fixture
    data root" EP-4a's handoff anticipated; `--data-root DIR` is accepted by
    all three verbs; `--stage NAME` runs a prefix (EP-5's
    `phillysim run --stage spine` shape); `--param stage.key=value` overrides
    declared parameters only. `run` and `status` without `--fixture` say no
    real pipeline is registered yet and exit 1.
  - Preflight measures physical RAM without a new dependency (Win32
    `GlobalMemoryStatusEx`, `/proc/meminfo`, `sysconf`); an unmeasurable
    value fails rather than passes. Probes are injectable for the negative
    tests.
  - Eleven fixture stages named after architecture.md's data flow; stubs:
    `hours` (oracle answers; M4), `travel_times` (oracle matrix, censored by
    parameter; M3), and `publish` (plain CSV, no license labels or CSV
    escaping; EP-7). `conflate` is the identity on the fixture (each site
    appears once) but enforces the unique-key contract.
  - tinycity polygon corners rounded to six decimals (generator change;
    golden spine regenerated by content).
- **Owner decisions taken interactively (2026-09-02):** commit and push
  both commits (yes); accept the fixture rounding change (yes); accept the
  three stubs as recorded, keeping eleven stages and the placeholder public
  CSV in the gitignored fixture root (yes); next packet is the first
  checkpoint packet, EP-9, then EP-5 (yes).
- **Unresolved risks/questions:** the publish stage's placeholder must not
  be mistaken for the publish gate; EP-7 replaces its body and adds bucket
  labels and escaping. Cancellation is cooperative only: a hard kill
  between the state write and the output rename can leave a `running`
  record, which `verify` reports and the next `run` clears (by design; no
  signal handling was added). Preflight's real-run RAM threshold uses the
  24 GB routine peak, not the 20/22 GB process-tree routing budget, which
  belongs to the M3 spike harness.
- **No-go areas touched:** none — no network calls, no real data,
  `source material/` untouched, no machine identifiers or absolute paths in
  tracked files or in the state file, `data/` (including the fixture root
  and state file) gitignored.
- **`roadmap/README.md` packet row:** updated to `[x] 9a0a3dc`; M1 heading
  set to `[x] 9a0a3dc` (go/no-go met); phase overview row updated.
- **Exact next packet:** EP-9, the first checkpoint packet (to be authored
  from `_TEMPLATE.md` per milestones.md "Spikes & gates"), then EP-5.
