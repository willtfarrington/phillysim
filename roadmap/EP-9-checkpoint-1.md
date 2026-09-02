# EP-9 — Checkpoint 1: fixture re-run, docs sync, license sweep, budgets, estimate accuracy

**Status:** [x] 84c9ec1 · **Milestone:** — (checkpoint after M1, before M2) · **Effort:** S (1 session, high confidence) · **Parallel with:** —

## Outcome & value
The first recurring checkpoint packet ([milestones.md](milestones.md)
"Spikes & gates": every ~5 packets, S-sized). Five packets in (EP-1, EP-2,
EP-3, EP-4a, EP-4b) and before the first real data arrives with EP-5, this
packet confirms the foundation is what the documents say it is: the fixture
pipeline reproduces from a fresh clone, the data dictionary and READMEs match
the code, every license label in the repository is accounted for, resource
use is recorded against the budgets, and the effort estimates are checked
against actuals. It ends by reading EP-5 and deciding whether it fits one
session, so EP-5 starts split-or-not with no pickup work of its own. If any
re-plan trigger fires, the packet stops and surfaces it to the owner instead
of proceeding.

## Scope
- in:
  1. **Integration re-run from a fresh clone.** Clone the pushed `main` into
     a scratch directory (not the working clone); `uv sync --locked`;
     `uv run pytest`; `uv run phillysim run --fixture` twice (the second run
     must skip all eleven stages); `status --fixture`; `verify --fixture`.
     Record counts and timings.
  2. **Docs / data-dictionary sync.** Every file the fixture pipeline writes
     (`intermediate/validation.json`, `acs_tracts.parquet`,
     `destinations.parquet`, `sites_conflated.parquet`, `network.json`,
     the four curated tables, `public/tract_metrics.csv`, the state file)
     is either documented in `docs/data-dictionary.md` or listed there as
     intermediate-and-undocumented by policy. Statements about the pipeline
     in `phillysim/README.md`, the fixture README, `CHANGELOG.md`,
     `roadmap/architecture.md` (the eleven stages now have names: record
     them under "Data flow"), and `roadmap/quality.md` (test matrix rows)
     are checked against the code and tests; drift is fixed here if it is a
     documentation error, or recorded as a finding for the owning packet if
     it is a code gap.
  3. **License-label sweep.** No published output exists yet, so the sweep
     is: every fixture manifest's `license_bucket` agrees with its contract
     (already tested; confirm); `docs/DATA-LICENSES.md` "Source terms
     summary" and "What ships with each snapshot" describe the manifest
     fields the engine owns since EP-4a (`terms_archive`, `license_bucket`,
     `license_note`); the placeholder `publish` stage's output is explicitly
     flagged as unlabeled until EP-7; `git ls-files` shows nothing under any
     `public/` zone; `.gitignore` covers the state file and the fixture
     root. Findings recorded as a checklist in the handoff.
  4. **Performance vs budgets.** Record baselines: per-stage wall time from
     `run --fixture`, full-suite time, fixture data-root size, and the
     preflight report on the development machine; compare to
     architecture.md's budgets (trivially within at fixture scale) and note
     that peak-RSS measurement starts with the M3 spike harness. Baselines
     go in the handoff and a short "Resource baselines" note in
     `phillysim/README.md`.
  5. **Estimate-accuracy review.** Add an "Estimate accuracy" table to
     `roadmap/milestones.md` (packet, estimate, actual sessions, ratio,
     note) with EP-1 through EP-4b, appended by every later checkpoint; then
     evaluate the three re-plan triggers ("Session model": any kill
     criterion fired; checkpoint finds drift; two consecutive packets over
     estimate by >2×) and record the result.
  6. **EP-5 pre-read and split decision.** Read
     [EP-5](EP-5-spine-adapters.md) against the one-session rule
     ([README](README.md) "Packet sizing and splitting"). Record the verdict;
     if it does not fit, author `EP-5a-…` / `EP-5b-…` from
     [_TEMPLATE.md](_TEMPLATE.md) with the split convention, add their rows
     to the M2 table, and leave the bare EP-5 file as the set's description.
     (No refinement-gate carry-ins apply: those start at M3.)
- out (explicit non-scope): any feature or refactor; real data or network
  access beyond PyPI and GitHub for the fresh clone (the same hosts CI
  uses); code fixes larger than a one-line documentation-driven correction
  (larger defects become findings for the owning packet); the CI
  performance-smoke test (deferred to the first packet with a non-trivial
  stage, the M3 spike).

## Prerequisites & locked decisions
- prerequisites: EP-4b (M1 done).
- locked decisions honored: milestones.md checkpoint definition and re-plan
  triggers; README packet-sizing and split conventions; ADR-0003 license
  buckets; ADR-0006 version axes; docs/CLAIMS.md wording rules for any prose
  touched.
- dependencies: none external.

## Safety preconditions
Standing policy (see EP-1). Packet-specific: the fresh clone is a scratch
directory deleted afterwards; no real data is acquired; nothing is written
under a tracked `public/` zone; documentation edits stay inside the claims
matrix; any license contradiction found is a stop condition, not something
to paper over in prose.

## Likely components & contracts (proposed)
Documentation only: `docs/data-dictionary.md`, `docs/DATA-LICENSES.md`,
`phillysim/README.md`, `roadmap/architecture.md`, `roadmap/milestones.md`
(new "Estimate accuracy" table), `CHANGELOG.md`; possibly new
`roadmap/EP-5a-*.md` / `EP-5b-*.md` and M2 table rows. No new modules; a
test or code change only as a one-line correction the re-run or sync
demands, recorded in the handoff.

## Implementation notes
Run the fresh-clone re-run first: its result decides whether the rest of the
session is a checkpoint or a stop. Keep each sweep as a literal checklist in
the handoff (item, evidence, pass/finding). "Drift" means a statement in a
document that the code or tests contradict; a missing statement is a gap,
not drift. The estimate-accuracy actuals come from the packet handoffs (all
five packets so far closed in one session, including the two M-sized ones):
say what that implies for the remaining M estimates rather than silently
re-sizing them. For the EP-5 pre-read, the split boundary its brief allows
is adapters (TIGER + CenPop + ACS acquisition) versus the curated spine,
invariant tests, and the CRS ADR; decide on evidence, not by default.

## Acceptance criteria & evidence
- [ ] Fresh-clone re-run green: `uv sync --locked`, `uv run pytest`,
      `phillysim run --fixture` (11 ran) then again (0 ran, 11 skipped),
      `status --fixture` (11 fresh), `verify --fixture` (8 of 8 snapshots,
      11 of 11 stages), with counts and timings in the handoff.
- [ ] Docs sync: every pipeline-written file documented or listed as
      intermediate by policy; architecture.md names the eleven stages; each
      checked statement recorded as pass or fixed; code gaps recorded as
      findings with an owning packet.
- [ ] License-label sweep checklist complete with no open contradiction;
      `git ls-files` shows no file under any `public/` zone.
- [ ] Baselines recorded in the handoff and `phillysim/README.md`, compared
      to the budgets.
- [ ] "Estimate accuracy" table in milestones.md holds EP-1..EP-4b; the
      three re-plan triggers evaluated and recorded (none fired, or which
      one and the owner's decision).
- [ ] EP-5 pre-read verdict recorded; if split, EP-5a/EP-5b exist, follow
      the convention, and have M2 table rows.
- Evidence: handoff payload; CI run on the checkpoint commit green on
  Windows + Linux.

## Tests / validation
`uv run pytest` in the fresh clone and in CI; the three fixture-pipeline
verbs from the fresh clone; no new tests expected.

## Resource budget
Trivial (fixture scale; a fresh clone is a few MB plus the uv environment).

## Risks, rollback, stop condition
Fresh-clone re-run fails → **stop**; that is the "checkpoint finds drift"
re-plan trigger, surfaced to the owner with the failure recorded. A license
contradiction or a tracked file under a `public/` zone → **stop** and
surface. Any re-plan trigger firing → record, stop, owner decides. Rollback
is trivial: documentation commits only.

## Documentation / ADR updates
The files listed under components; packet row in `roadmap/README.md`
"Checkpoints" table; if EP-5 is split, its rows in the M2 table and a
CHANGELOG line.

## Handoff payload (filled 2026-09-02)
- **Packet:** EP-9 — done at commit `84c9ec1` (+ this status commit).
  Planning Baseline v1.0. CI run
  [33672509920](https://github.com/willtfarrington/phillysim/actions/runs/33672509920)
  on `84c9ec1` green on `windows-latest` and `ubuntu-latest`, including the
  `run` / `status` / `verify --fixture` steps.
- **Files changed:** `roadmap/architecture.md` (stage table under "Data
  flow"); `docs/data-dictionary.md` (EP-5b reference; "Intermediate files
  (undocumented by policy)" and "Placeholder public export" sections);
  `docs/DATA-LICENSES.md` (labeling-status paragraph; manifest fields
  named under "What ships with each snapshot"); root `README.md` (status
  paragraph corrected; Windows `core.longpaths` setup note);
  `phillysim/README.md` (`core.longpaths` note; "Resource baselines"
  section); `phillysim/tests/fixtures/tinycity/README.md` (one line on
  `verify --fixture`); `roadmap/quality.md` (test-matrix "Exists at EP-9"
  column); `roadmap/milestones.md` ("Estimate accuracy" table, implication
  note, re-plan trigger evaluation); new `roadmap/EP-5a-spine-acquisition.md`
  and `roadmap/EP-5b-spine-curated.md`; `roadmap/EP-5-spine-adapters.md`
  (header and note: now the set's description); `roadmap/README.md`
  (M2 rows, sizing bullet, document index, Checkpoints table and note);
  `CHANGELOG.md`; this file. No code or test changed.
- **Commands/tests run + results (fresh clone of `main` at `a72d318`, in
  a scratch directory, deleted afterwards):** first `git clone` **failed at
  checkout** ("Filename too long" on two file names under the vendored
  `source material/` tree; the scratch path was about 140 characters
  deep); re-clone with `-c core.longpaths=true` → 1.7 s. `uv sync
  --locked` → 5.6 s (warm uv cache; `.venv` 363 MB). `uv run pytest` → 240
  passed in 10.0 s. `ruff check` / `ruff format --check` clean.
  `phillysim run --fixture` → preflight all checks passed (fixture-scale
  thresholds), 11 ran / 0 skipped, 1.5 s wall (`acquire` 0.1 s, `validate`
  0.1 s, every other stage 0.0 s). Second run → 0 ran / 11 skipped, 1.0 s.
  `status --fixture` → 11 fresh, 0 stale, 0 missing, 0 incomplete, 0.9 s.
  `verify --fixture` → 8 of 8 snapshots verified, 11 of 11 stages done and
  intact, 0.9 s. `git status` in the fresh clone clean after the run (the
  fixture root and state file are gitignored). In the working clone after
  the edits: 240 passed, ruff clean, `pre-commit run --all-files` all hooks
  passed, staged diff scanned for usernames / absolute paths → none, every
  `EP-*.md` link in the roadmap resolves.
- **Resource observations (baselines, also in `phillysim/README.md`):**
  fixture data root 148 KB after a run (raw 55 KB, curated 44 KB,
  intermediate 29 KB, state file 12 KB, public 4 KB); preflight on the
  development machine: 429 GB free disk, 68.1 GB physical RAM, Python
  3.13.15, six locked packages present (the real-run thresholds would also
  pass). All trivially within the architecture.md budgets; peak RSS is not
  measured until the M3 spike harness. Single session.
- **Docs / data-dictionary sync checklist:**
  - `intermediate/validation.json`, `acs_tracts.parquet`,
    `destinations.parquet`, `sites_conflated.parquet`, `network.json` →
    were undocumented → now listed as intermediate-and-undocumented by
    policy (gap closed).
  - `curated/tracts_spine.parquet`, `sites.parquet`,
    `travel_times.parquet`, `tract_metrics.parquet` → documented; columns
    checked against `fixtures/pipeline.py` → pass.
  - `public/tract_metrics.csv` → was undocumented → "Placeholder public
    export" section (gap closed); state file → documented (EP-4b) → pass.
  - `phillysim/README.md`: setup, layout list (every tracked module and
    test file present), data-root rules, EP-4a and EP-4b sections
    (fingerprint rule, staging + atomic rename, status states, verify
    exit codes, preflight thresholds, stub list, "no real pipeline
    registered" behavior) → all pass against `cli.py`, `runner.py`,
    `preflight.py`, `fixtures/pipeline.py` and the integration suite.
  - Fixture README: "all eight verify against it (`phillysim verify
    --fixture`)" → **drift** (since EP-4b that verb checks the fixture
    data root, the committed copy is checked by the tests) → fixed.
  - Root README "Status": "no pipeline logic exists yet" → **drift** →
    fixed (M0 and M1 done, eleven fixture stages, no real source yet).
  - `CHANGELOG.md`: test counts 24 → 76 → 207 → 240 add up; stage list,
    stub list, gitignore entries → pass.
  - `roadmap/architecture.md`: eleven stages named → done (new table); the
    "Data flow" line placing normalization in the intermediate zone while
    the spine lands in curated is clarified by the table, not changed.
  - `roadmap/quality.md` test matrix: rows checked → source contracts and
    integration exist; golden math partly (`test_cv_tier_rule`);
    invariants, UI, a11y, performance smoke not yet → recorded in a new
    column, no drift.
  - Code gaps found: none new (the `publish`, `hours`, `travel_times`,
    `conflate` stubs are already owned by EP-7, M4, M3, M4).
- **License-label sweep checklist:** fixture manifests' `license_bucket`
  (seven A, `osm_network` B) agree with `tinycity_contracts.py` and are
  checked by `tests/contracts/test_tinycity_sources.py` and the `validate`
  stage → pass. `docs/DATA-LICENSES.md` "What ships with each snapshot"
  now names `acquisition_url`, `acquisition_url_alt`, `terms_archive`,
  `license_bucket`, `license_note`, `schema_version`, per-file digests →
  done. Placeholder `publish` output flagged as unlabeled until EP-7 in
  DATA-LICENSES and the data dictionary → done. `git ls-files` → no file
  under any `public/` zone (the only matches are words inside vendored
  path names) → pass. `.gitignore` covers `data/pipeline_state.json` and
  `data/fixture/` (and the fresh clone stayed clean after a run) → pass.
  No contradiction found; no stop condition.
- **Estimate accuracy:** table added to `milestones.md` (EP-1–EP-4b all
  one session; M0 2 of 3–4; M1 3 of 4–6). Implication recorded: remaining
  M estimates likely at their low end but not re-sized (first real-data,
  network, and UI packets ahead); the pickup pre-read stays the sizing
  instrument.
- **Re-plan trigger evaluation:** (1) kill criterion: none exists before
  M3, not fired; (2) checkpoint finds drift: re-run green, two
  documentation-only contradictions fixed in-packet, no code contradicted
  a document, **not fired** (owner confirmed this reading); (3) two
  consecutive packets >2× over estimate: none over, not fired.
- **EP-5 pre-read verdict: does not fit one session → split.** Evidence:
  the brief holds two first-time subsystems, the outbound acquisition path
  (allowlist, timeouts/backoff, capped streaming, terms archiving, three
  adapters, contracts, CI samples, the first real pipeline registration)
  and the real-data spine (curated table, invariant tests, ADR for the
  analysis CRS, data cards), each at least the size of an EP-4 half, and
  each EP-4 half filled one session. Split at the boundary the brief's
  implementation notes allow: `EP-5a-spine-acquisition.md` (acquire) →
  `EP-5b-spine-curated.md` (curate; carries the set's milestone-level
  evidence). Both S, from `_TEMPLATE.md`, `Split from: EP-5` in the header;
  M2 table rows added; EP-6 depends on EP-5b; the bare EP-5 file describes
  the set so existing references stay valid.
- **Decisions made (revisable, below ADR level):** the quality.md test
  matrix gains a status column rather than a separate list; the
  intermediate files are documented as a policy list, not column by
  column; baselines record timings and sizes only (no machine identifiers
  beyond RAM and free disk); the Windows path-length finding is handled as
  a setup note in both READMEs (the vendored tree is never modified).
- **Owner decisions taken interactively (2026-09-02):** commit and push
  (yes: work commit `84c9ec1`, then this status commit after CI); keep
  the EP-5a / EP-5b split (yes); record the drift trigger as not fired
  (yes); the `core.longpaths` README note is sufficient (yes).
- **Unresolved risks/questions:** none new. Carried: the placeholder
  `publish` output must not be mistaken for the publish gate (EP-7); peak
  RSS unmeasured until M3; guard `Limits` unconfirmed until EP-5a.
- **No-go areas touched:** none — no real data, no network beyond GitHub
  (clone, push) and PyPI (locked sync), `source material/` untouched,
  nothing under a tracked `public/` zone, no machine identifiers or
  absolute paths in tracked files (scanned), the scratch clone deleted.
- **`roadmap/README.md`:** EP-9 row `[x] 84c9ec1` in the Checkpoints
  table; the next checkpoint falls due after EP-8 (about five more
  packets: EP-5a, EP-5b, EP-6, EP-7, EP-8) and takes the next free
  integer.
- **Exact next packet:** EP-5a (spine source adapters: acquisition path +
  TIGER/CenPop/ACS snapshots), then EP-5b.
