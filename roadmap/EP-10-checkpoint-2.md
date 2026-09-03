# EP-10 — Checkpoint 2: fresh-clone re-run with real data, docs sync, license sweep on published output, budgets, dependency triage, estimate accuracy, M3 gate pre-read

**Status:** [ ] planned · **Milestone:** — (checkpoint after M2, before the M3 refinement gate) · **Effort:** S (1 session, high confidence) · **Parallel with:** —

## Outcome & value
The second recurring checkpoint packet ([milestones.md](milestones.md)
"Spikes & gates": every ~5 packets, S-sized; the first was
[EP-9](EP-9-checkpoint-1.md)). Seven packets in since then (EP-5a, EP-5b,
EP-6, EP-7, EP-8a, EP-8b, and EP-9 itself) and with M2 closed, this packet
confirms that what the repository says about the real pipeline is what the
real pipeline does: the eight stages reproduce the public zone byte for
byte from a fresh clone **including a fresh acquisition from the
providers** (the refresh-drift check no earlier checkpoint could make), the
data dictionary, data cards, and READMEs match the code, every license
label on the real published output is traceable to a source record,
resource use is recorded against the budgets, the dependency set is
triaged, and the effort estimates are checked against seven more actuals.
It ends with a pre-read of the M3 refinement gate and authors that gate as
its own documentation-only packet, EP-11, so the gate starts with its
inputs and carry-ins listed and nothing to rediscover. If any re-plan
trigger fires, the packet stops and surfaces it to the owner instead of
proceeding.

## Scope
- in:
  1. **Integration re-run from a fresh clone, fixture and real.** Clone
     the pushed `main` into a scratch directory (`git clone -c
     core.longpaths=true`, not the working clone); `uv sync --locked`; `uv
     run pytest`; the fixture verbs (`run --fixture` twice, the second
     skipping all eleven stages; `status --fixture`; `verify --fixture`;
     `gate --fixture`; `site build --fixture`); then the **real pipeline
     from an empty data root**: `phillysim run` (all eight stages, the five
     sources acquired through the guarded path, about 122 MB), `run` again
     (0 ran, 8 skipped), `status`, `verify`, `gate`, `site build`. Record
     counts and timings, and compare every raw data-file digest in the five
     snapshot manifests and every public and curated digest against the
     EP-8b handoff's reference list. The archived terms pages are not
     byte-stable (recorded since EP-5a) and are excluded from the digest
     comparison; that they still carry the checked sentences is proven by
     `acquire` admitting them.
  2. **Docs / data-dictionary sync, real pipeline included.** Every file
     the real pipeline writes (the five raw snapshots with their manifests
     and archived pages, `intermediate/acquisition.json`,
     `validation.json`, `acs_tracts.parquet`, `snap_retailers.json`,
     `basemap.json`, `slice_metric.json`, the four curated tables, the six
     public files, the state file) is documented in
     `docs/data-dictionary.md` or listed there as intermediate by policy.
     Statements about the pipeline, the zone, and the page in
     `phillysim/README.md`, the root `README.md`, `site/README.md`, the
     five data cards and their index, the two method cards,
     `docs/DATA-LICENSES.md`, `docs/CLAIMS.md` ("Mechanical enforcement"),
     `roadmap/architecture.md` (stage table rows 1–11 with 4b and 4c),
     `roadmap/quality.md` (test matrix), `roadmap/sources.md`, and
     `CHANGELOG.md` (test counts, stage lists, file lists) are checked
     against the code and tests; drift is fixed here if it is a
     documentation error, or recorded as a finding for the owning packet
     or gate if it is a code gap.
  3. **License-label sweep on real published output.** For every file in
     the installed real `public/manifest.json`: its bucket equals the
     bucket derived from its listed sources' raw manifests, its
     attribution lines equal the adapters' citations and the attribution
     lines in the DATA-LICENSES snapshot records, and the five sources'
     `license_note` texts agree with those records; the fixture zone's
     Bucket B path (ODbL + OpenStreetMap notices) is exercised in CI; the
     CI samples' `license_note` texts and their README name every source;
     `git ls-files` shows nothing under any `public/` zone or `site/dist/`;
     the ODbL notice sentence in `phillysim.publish.bucket` is confirmed
     still flagged for legal review at M6 (EP-7 handoff). Findings recorded
     as a checklist in the handoff. A contradiction is a stop condition.
  4. **Performance vs budgets.** From the fresh clone: per-stage wall time
     of the real run, acquisition bytes and seconds per source, the second
     run, `status` / `verify` / `gate` / `site build` times, full-suite
     time, CI duration per platform, the real data root's size by zone, the
     public zone's size raw and gzipped (architecture.md: sub-MB gzipped
     payload), the built site's size, and the preflight report; compared
     to the budgets and appended to "Resource baselines" in
     `phillysim/README.md`. Peak RSS stays deferred to the M3 spike harness
     (owner decision at authoring, 2026-09-03: the real run is seconds of
     pandas work; the budget bites with r5py).
  5. **Dependency triage.** List the open Dependabot pull requests and
     triage each with the owner (merge, defer, or close, recorded in the
     handoff); `uv lock --check` clean; note whether the vendored MapLibre
     GL JS (6.7.0, `site/vendor/maplibre-gl/VENDOR.md`) and the SHA-pinned
     actions in `.github/workflows/ci.yml` are current or behind, without
     upgrading anything inside the checkpoint unless the owner says so
     (an upgrade is a one-line lockfile or vendor change with CI as the
     test, done in this packet only on the owner's word). A security
     alert is surfaced, never deferred silently.
  6. **Estimate-accuracy review.** Append EP-5a, EP-5b, EP-6, EP-7, EP-8a,
     EP-8b, EP-9, and the M2 roll-up to the "Estimate accuracy" table in
     `roadmap/milestones.md` (actuals from the packet handoffs); rewrite
     the implication note with the real-data, network, and browser actuals
     EP-9 said were missing; evaluate the three re-plan triggers ("Session
     model") and record the result; **propose, not apply,** any re-sizing
     of the M3–M8 effort ranges in the milestones table for the owner's
     decision.
  7. **M3 refinement-gate pre-read and EP-11.** Read what the M3 gate will
     need: the routing spike's numeric criteria (milestones.md M3 row and
     "Spikes & gates": wall ≤ 8 h, process-tree RSS ≤ 22 GB, determinism
     band, sanity gates, KILLED-BY-EVIDENCE vs TIMEBOX-EXHAUSTED),
     methodology.md's travel model and origins, architecture.md's r5py /
     JDK 21 / R5 jar pins and budgets, ADR-0001, the open questions and the
     "Refinement-gate carry-ins" that name M3 (none as of 2026-09-03; the
     M4 and M5/M6 entries stay for their gates), the walk-only fallback
     wording (AM-2), and the streets and transit sources the spike needs
     (OSM via Geofabrik, ODbL, Bucket B; SEPTA GTFS terms). Record the list
     of inputs, the questions the gate must answer, and any gap in the
     planning documents as findings. Then author
     `EP-11-m3-refinement-gate.md` from [_TEMPLATE.md](_TEMPLATE.md): a
     documentation-only S packet whose outcome is the M3 packet files
     (EP-12 onward, S each, carry-ins first), added to the README with a
     new "M3 — Routing spike" heading in the README (opened by EP-10 with
     EP-11 as its first row: a gate packet belongs to the milestone it
     refines, unlike a checkpoint, which belongs to none) and filled in by
     EP-11 with the packets it authors.
- out (explicit non-scope): any feature or refactor; code fixes larger
  than a one-line documentation-driven correction (larger defects become
  findings for the owning packet); authoring the M3 packets themselves
  (that is EP-11); dependency upgrades not asked for by the owner; peak-RSS
  measurement; the CI performance-smoke test (still the M3 spike's); any
  controlled refresh of a snapshot (a provider-bytes mismatch is a finding
  and a stop, not a refresh).

## Prerequisites & locked decisions
- prerequisites: EP-8b (M2 done).
- locked decisions honored: milestones.md checkpoint definition and
  re-plan triggers; README packet-sizing and split conventions (every new
  packet S); ADR-0003 license buckets; ADR-0005 basemap; ADR-0006 version
  axes; ADR-0007 analysis CRS; docs/CLAIMS.md wording rules for any prose
  touched; the download-path order and the terms-archive stop condition
  (EP-5a); the fixture-only screenshot policy (EP-8a, EP-8b).
- dependencies: the five providers' files at their pinned URLs
  (`www2.census.gov`, `www.census.gov`, `www.fna.usda.gov` and its
  content-delivery host) for the fresh acquisition; GitHub and PyPI for the
  clone and the locked sync; the `gh` CLI for the Dependabot listing.

## Safety preconditions
Standing policy (see EP-1). Packet-specific: the fresh clone is a scratch
directory deleted afterwards, its real data root with it; the acquisition
goes only through the guarded path (allowlists, caps, terms check,
quarantine); nothing is written under a tracked `public/` zone or
`site/dist/`; no machine identifiers or absolute paths enter tracked files
(scan the diff); documentation edits stay inside the claims matrix; a
license contradiction, a provider-bytes mismatch, or a tracked file under a
public zone is a stop condition, not something to paper over in prose; no
dependency is upgraded without the owner's word.

## Likely components & contracts (proposed)
Documentation only: `docs/data-dictionary.md`, `docs/DATA-LICENSES.md`,
`docs/data-cards/*.md`, `docs/method-cards/*.md`, `phillysim/README.md`
("Resource baselines" appended), root `README.md`, `site/README.md`,
`roadmap/architecture.md`, `roadmap/quality.md`, `roadmap/sources.md`,
`roadmap/milestones.md` ("Estimate accuracy" rows, implication note,
re-plan evaluation, proposed re-sizing if any), `CHANGELOG.md`; new
`roadmap/EP-11-m3-refinement-gate.md` and its README row; possibly a
Dependabot merge or a one-line lockfile / vendor change on the owner's
word. No new modules; a test or code change only as a one-line correction
the re-run or sync demands, recorded in the handoff.

## Implementation notes
Run the fresh-clone re-run first: its result decides whether the rest of
the session is a checkpoint or a stop. The reference digests are in the
EP-8b handoff (public and curated) and the EP-5a / EP-6 handoffs and the
raw manifests (the provider files); a provider file whose bytes differ is
the refresh-drift finding this checkpoint exists to catch, and the answer
is an owner decision on a controlled refresh (a `SNAPSHOT_ID` bump in a
later packet), never an in-checkpoint re-pin. Keep each sweep as a literal
checklist in the handoff (item, evidence, pass / fixed / finding). "Drift"
means a statement in a document that the code or tests contradict; a
missing statement is a gap, not drift. For the estimate review, the
actuals are in the handoffs: every packet since EP-9 closed in one session,
the two remaining M-sized ones (EP-6, EP-7) at the low end, and EP-8 was
split at pickup; say what that implies for the M3–M8 ranges and propose
numbers for the owner rather than silently editing the milestones table.
For the dependency triage, `gh pr list --author app/dependabot` and `gh api
repos/{owner}/{repo}/dependabot/alerts` are the sources; decisions belong
to the owner. For the M3 pre-read, the gate's job is to turn the spike
outcome (milestones.md M3 row) into S packets: the harness and the run
matrix, the unattended runs, the verdict and fallback; EP-11 should be
written so that a fresh agent can author those packets from it and the
carry-in section without re-reading the whole baseline. The owner review
at the end of this packet covers, at least: commit and push, any
Dependabot decision, any proposed re-sizing, the re-plan trigger reading,
and EP-11 as authored.

## Acceptance criteria & evidence
- [ ] Fresh-clone re-run green, fixture and real: `uv sync --locked`, `uv
      run pytest`, the fixture verbs (11 ran, then 0 ran / 11 skipped; 11
      fresh; 8 of 8 snapshots, 11 of 11 stages; gate green; site built),
      the real pipeline from empty (8 ran, then 0 ran / 8 skipped; 8
      fresh; 5 of 5 snapshots, 8 of 8 stages; gate green, 5 files Bucket A;
      site built with `county_boundary (1), roads (426)`), with counts and
      timings in the handoff; every provider data-file digest and every
      public and curated digest equal to the recorded references.
- [ ] Docs sync: every real-pipeline-written file documented or listed as
      intermediate by policy; each checked statement recorded as pass or
      fixed; code gaps recorded as findings with an owning packet or gate.
- [ ] License-label sweep checklist complete with no open contradiction;
      every published file's label and attribution traced to its sources'
      manifests and the DATA-LICENSES records; `git ls-files` shows no file
      under any `public/` zone or `site/dist/`.
- [ ] Baselines recorded in the handoff and appended to
      `phillysim/README.md`, compared to the budgets; peak RSS recorded as
      deferred to M3 by owner decision.
- [ ] Dependency triage recorded: each open Dependabot PR with the owner's
      decision, `uv lock --check` clean, MapLibre and action pins noted.
- [ ] "Estimate accuracy" table holds EP-5a through EP-9 and the M2
      roll-up; the implication note rewritten; the three re-plan triggers
      evaluated and recorded; any re-sizing proposed to the owner and the
      answer recorded.
- [ ] M3 gate pre-read recorded (inputs, questions, gaps);
      `EP-11-m3-refinement-gate.md` exists, follows the template, is S, and
      has its README row.
- Evidence: handoff payload; CI run on the checkpoint commit green on
  Windows + Linux.

## Tests / validation
`uv run pytest` in the fresh clone and in CI; the fixture and real verbs
from the fresh clone; `pytest --real-data-root <fresh clone's data root>`
for the invariant modules on the freshly built real layers; no new tests
expected.

## Resource budget
Network: about 122 MB for the fresh acquisition (the same five files EP-8b
measured) plus the clone and the locked sync. Disk: the fresh clone with
its environment and data root, about 0.6 GB, deleted afterwards. Runtime:
minutes.

## Risks, rollback, stop condition
Fresh-clone re-run fails → **stop**; that is the "checkpoint finds drift"
re-plan trigger, surfaced to the owner with the failure recorded. A
provider data file whose bytes differ from the pinned manifest → the
guarded path quarantines it and the run fails → **stop** and surface as a
refresh-drift finding (owner decides on a controlled refresh in a later
packet). A terms-page sentence gone → quarantine, **stop**. A license
contradiction or a tracked file under a public zone → **stop** and surface.
A Dependabot security alert → surface before anything else in the triage.
Any re-plan trigger firing → record, stop, owner decides. Rollback is
trivial: documentation commits only (plus at most a Dependabot merge the
owner asked for, revertible by commit).

## Documentation / ADR updates
The files listed under components; packet row in `roadmap/README.md`
"Checkpoints" table; EP-11's file and row; `milestones.md` "Spikes & gates"
pointer to the next checkpoint (due after about five more packets); a
CHANGELOG line.

## Handoff payload (fill at session end)
- packet ID + status; baseline/roadmap version
- files changed; commands/tests run + results (fresh-clone counts,
  timings, and the digest comparison, provider files included)
- resource observations (the baselines, compared to budgets)
- the four checklists (docs sync, license sweep, dependency triage,
  estimate accuracy) with pass / fixed / finding per item
- re-plan trigger evaluation; any re-sizing proposed and the owner's answer
- M3 gate pre-read: inputs, questions, gaps; EP-11 authored
- decisions/ADRs made; unresolved risks/questions
- no-go areas touched? (must be none)
- `roadmap/README.md` packet row updated to `[x] <commit>`; the next
  checkpoint's due point recorded
- exact next packet: EP-11 (the M3 refinement gate)
