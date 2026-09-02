# EP-9 — Checkpoint 1: fixture re-run, docs sync, license sweep, budgets, estimate accuracy

**Status:** [ ] planned · **Milestone:** — (checkpoint after M1, before M2) · **Effort:** S (1 session, high confidence) · **Parallel with:** —

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

## Handoff payload (fill at session end)
- packet ID + status; baseline/roadmap version
- files changed; commands/tests run + results (fresh-clone counts and
  timings; CI run ID)
- resource observations (the recorded baselines)
- decisions/ADRs made; unresolved risks/questions; the sweep checklists
  with findings; re-plan trigger evaluation
- no-go areas touched? (must be none)
- `roadmap/README.md` packet row updated to `[x] <commit>` in the
  Checkpoints table; the next checkpoint's due point noted (after ~5 more
  packets)
- exact next packet: EP-5 (or EP-5a if split)
