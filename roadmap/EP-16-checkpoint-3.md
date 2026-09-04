# EP-16 — Checkpoint 3: fresh-clone re-run with real data and the routing night, docs sync, license sweep, budgets with peak RSS, dependency triage, estimate accuracy with the M3 actual, M4 gate pre-read

**Status:** [ ] planned (authored 2026-09-04 by EP-15's closing session) · **Milestone:** — (checkpoint after M3, before the M4 refinement gate) · **Effort:** S (1 session, high confidence) · **Parallel with:** —

## Outcome & value
The third recurring checkpoint packet ([milestones.md](milestones.md)
"Spikes & gates": every ~5 packets, S-sized; the first was
[EP-9](EP-9-checkpoint-1.md), the second [EP-10](EP-10-checkpoint-2.md)).
Six packets in since EP-10 (EP-11 to EP-15 and EP-10 itself) and with M3
closed on a go verdict, this packet confirms that what the repository says
about the real pipeline is what the real pipeline does, **now including an
unattended routing stage**: the ten stages reproduce the curated zone and
the public zone byte for byte from a fresh clone, with the `travel_times`
stage routed as a night of its own on the pinned toolchain and its matrix
digests equal to the spike's night and the second night (the cross-clone
determinism repeat the M5 carry-in asks for); the data dictionary, data
cards, method cards, and READMEs match the code; every license label on the
real published output is traceable to a source record; resource use,
**peak process-tree RSS included for the first time at a checkpoint**, is
recorded against the budgets; the dependency set is triaged; and the effort
estimates are checked against the M3 actual (the first milestone read
against the high-bound rule EP-10 set). It ends with a pre-read of the M4
refinement gate and authors that gate as its own documentation-only packet,
EP-17, so the gate starts with its inputs and carry-ins listed. If any
re-plan trigger fires, the packet stops and surfaces it to the owner
instead of proceeding.

## Scope
- in:
  1. **Integration re-run from a fresh clone, fixture and real, routing
     included.** Clone the pushed `main` into a scratch directory (`git
     clone -c core.longpaths=true`, not the working clone); `uv sync
     --locked --group routing` (the routing group is optional and CI never
     installs it; the real `travel_times` stage refuses without it);
     `phillysim toolchain install` and `toolchain check` (the pinned JDK
     and jar, ADR-0008, project-local); `uv run pytest` (the OSMnx-side
     tests run with the group installed); the fixture verbs (`run
     --fixture` twice, the second skipping all eleven stages; `status
     --fixture`; `verify --fixture`; `gate --fixture`; `site build
     --fixture`); then the **real pipeline from an empty data root**:
     `phillysim run` (all ten stages; the five spine sources plus the two
     routing sources acquired through the guarded path; the `travel_times`
     stage routes the two core runs as a night of about a quarter of an
     hour on the development machine, attended this once so the checkpoint
     sees it; keep the machine awake), `run` again (0 ran, 10 skipped),
     `status`, `verify`, `gate`, `site build`, `route status`, `route
     verdict --night <the new night>` (mechanical criteria only: the hand
     check and the concordance belong to the spike's night). Record counts
     and timings, and compare every raw data-file digest in the seven
     snapshot manifests and every public and curated digest against the
     EP-8b, EP-12, and EP-15 handoffs' reference lists; in particular
     `curated/travel_times.parquet`'s canonicalized-value digest and each
     core run's matrix digests against the spike's night
     (`20260903T223607Z-m3-spike`: walk value digest `100625cd…`, transit
     `e35b466d…`) and the second night (`20260904T191646Z-travel-times`,
     the EP-15 handoff). The archived terms pages are not byte-stable
     (recorded since EP-5a) and are excluded; r5py's network cache is
     rebuilt in the fresh clone, so its files are not compared.
  2. **Docs / data-dictionary sync, routing included.** Every file the
     real pipeline writes (the seven raw snapshots with manifests and
     archived pages, the intermediate files including
     `intermediate/network/` and `intermediate/travel_times.json`, the
     curated tables including `travel_times.parquet`, the public files, the
     state file, and the night directories under `runs/routing/` with their
     run records, `verdict.json`, `handcheck/`, and `concordance/`) is
     documented in `docs/data-dictionary.md` or listed there as
     intermediate by policy. Statements about the pipeline, the routing
     stage, the toolchain, the zone, and the page in `phillysim/README.md`,
     the root `README.md`, `site/README.md`, the seven data cards and their
     index, the three method cards (the travel-times stub included),
     `docs/DATA-LICENSES.md`, `docs/CLAIMS.md`, `roadmap/architecture.md`
     (stage table rows 1–11), `roadmap/quality.md` (test matrix, AM-2 band
     wording), `roadmap/sources.md`, `roadmap/methodology.md` ("Validation"
     as clarified at EP-15), ADR-0008, and `CHANGELOG.md` (test counts,
     stage lists, file lists) are checked against the code and tests; drift
     is fixed here if it is a documentation error, or recorded as a finding
     for the owning packet or gate if it is a code gap.
  3. **License-label sweep on real published output and the Bucket B
     zone.** For every file in the installed real `public/manifest.json`:
     its bucket equals the bucket derived from its listed sources' raw
     manifests, its attribution lines equal the adapters' citations and
     the DATA-LICENSES records, and the sources' `license_note` texts agree
     with those records; the public zone is still Bucket A only (nothing
     derived from the OSM network is published before M5; `publish` does
     not read the matrix); the curated matrix and the night records are
     Bucket B by derivation and say so where the dictionary says they do;
     `git ls-files` shows nothing under any `public/` zone, `site/dist/`,
     `data/`, or the toolchain directories (`phillysim/.jdk/`,
     `phillysim/.r5/`); the SEPTA feed's terms as recorded in
     DATA-LICENSES still hold; the ODbL notice sentence stays flagged for
     legal review at M6. Findings recorded as a checklist in the handoff.
     A contradiction is a stop condition.
  4. **Performance vs budgets, peak RSS included.** From the fresh clone:
     per-stage wall time of the real run, acquisition bytes and seconds per
     source, the routing night's walls and **peak process-tree RSS per
     run** (from the night's records, against the 20 GB budget and the
     22 GB kill), the toolchain install, the second run, `status` /
     `verify` / `gate` / `site build` times, full-suite time with the
     routing group, CI duration per platform, the real data root's size by
     zone (the cache under it, r5py's network cache and the concordance
     XML, against the 50 GB workspace budget), the public zone's size raw
     and gzipped, the built site's size, and the preflight report; compared
     to the budgets and appended to "Resource baselines" in
     `phillysim/README.md`.
  5. **Dependency triage.** List the open Dependabot pull requests and
     alerts and triage each with the owner (merge, defer, or close,
     recorded in the handoff); `uv lock --check` clean; note whether the
     vendored MapLibre GL JS, the SHA-pinned actions, and the routing
     group's wheels (r5py, JPype1, psutil, osmnx, scipy; an upgrade of
     r5py, R5, or the JDK re-measures the determinism band by the OQ-C
     procedure at the checkpoint that follows it) are current or behind,
     without upgrading anything inside the checkpoint unless the owner says
     so. A security alert is surfaced, never deferred silently.
  6. **Estimate-accuracy review.** Confirm the EP-15 and M3 rows of the
     "Estimate accuracy" table in `roadmap/milestones.md` (written by
     EP-15's closing session) and append EP-16 itself; rewrite the
     implication note with the M3 actual read against EP-10's rule (the
     gate's packet count replaces the range; the high bound is the planning
     number): EP-11 authored four S packets and the box (EP-13 to EP-15)
     took four attended sessions, so record what the count predicted and
     what it missed (the closing session the hand check's tally forced);
     evaluate the three re-plan triggers and record the result; **propose,
     not apply,** any re-sizing of the M4–M8 ranges for the owner's
     decision.
  7. **M4 refinement-gate pre-read and EP-17.** Read what the M4 gate will
     need: milestones.md's M4 row (all v1 sources snapshotted, conflated,
     hours parsed with a QA report; adapter contract tests; hours-coverage
     % published; conflation QA reviewed), the "M4 — SNAP retailer
     follow-ups" carry-in (the OSM `shop=supermarket` cross-check, the two
     out-of-tract rows, the thirteen coincident pairs, the farmers'-market
     overlap), sources.md's remaining v1 sources and their terms, OQ-D
     (market hours parse coverage) and OQ-E (the collaborative's name),
     methodology.md "Destination layers" and the hours model, the
     download-guard conventions (EP-5a) and per-source `SNAPSHOT_ID`s
     (EP-12), and the packet-sizing rule. Record the list of inputs, the
     questions the gate must answer, and any gap in the planning documents
     as findings. Then author `EP-17-m4-refinement-gate.md` from
     [_TEMPLATE.md](_TEMPLATE.md): a documentation-only S packet whose
     outcome is the M4 packet files (EP-18 onward, S each, carry-ins
     first), added to the README under a new "M4 — Full ingest" heading
     opened by this packet with EP-17 as its first row (a gate packet
     belongs to the milestone it refines, unlike a checkpoint, which
     belongs to none).
- out (explicit non-scope): any feature or refactor; code fixes larger
  than a one-line documentation-driven correction (larger defects become
  findings for the owning packet); authoring the M4 packets themselves
  (that is EP-17); dependency upgrades not asked for by the owner; the
  hand check and the concordance (done once on the spike's night, EP-15;
  not repeated); any controlled refresh of a snapshot (a provider-bytes
  mismatch is a finding and a stop, not a refresh); publishing any
  travel-time metric (M5); the M5 carry-in's second and third items.

## Prerequisites & locked decisions
- prerequisites: EP-15 (M3 closed on a go verdict; the second night
  finished and its digests recorded in the EP-15 handoff).
- locked decisions honored: milestones.md checkpoint definition and
  re-plan triggers; README packet-sizing and split conventions (every new
  packet S); ADR-0003 license buckets (the matrix is Bucket B); ADR-0005
  basemap; ADR-0006 version axes; ADR-0007 analysis CRS; ADR-0008 pins,
  band, and the routing group's layout; docs/CLAIMS.md wording rules for
  any prose touched; the download-path order and the terms-archive stop
  condition (EP-5a); the fixture-only screenshot policy (EP-8a, EP-8b);
  the walk gate's reading (EP-15, methodology.md "Validation").
- dependencies: the seven providers' files at their pinned URLs (the
  Census and USDA hosts, Geofabrik's dated extract, SEPTA's GTFS release)
  for the fresh acquisition; GitHub and PyPI for the clone, the locked
  sync, and the routing group's wheels; the JDK and R5 release hosts
  through `phillysim toolchain install`; the `gh` CLI for the Dependabot
  listing; the development machine awake for the routing night.

## Safety preconditions
Standing policy (see EP-1). Packet-specific: the fresh clone is a scratch
directory deleted afterwards, its real data root, toolchain, and caches
with it; the acquisition goes only through the guarded path (allowlists,
caps, terms check, quarantine); nothing is written under a tracked
`public/` zone or `site/dist/`; no machine identifiers or absolute paths
enter tracked files (scan the diff); documentation edits stay inside the
claims matrix; a license contradiction, a provider-bytes mismatch, a
matrix digest that differs from the recorded nights, or a tracked file
under a public zone is a stop condition, not something to paper over in
prose; no dependency is upgraded without the owner's word; nothing from a
trip planner is touched.

## Likely components & contracts (proposed)
Documentation only: `docs/data-dictionary.md`, `docs/DATA-LICENSES.md`,
`docs/data-cards/*.md`, `docs/method-cards/*.md`, `phillysim/README.md`
("Resource baselines" appended), root `README.md`, `site/README.md`,
`roadmap/architecture.md`, `roadmap/quality.md`, `roadmap/sources.md`,
`roadmap/milestones.md` ("Estimate accuracy" rows, implication note,
re-plan evaluation, the M5 carry-in's first item confirmed and trimmed,
proposed re-sizing if any), `CHANGELOG.md`; new
`roadmap/EP-17-m4-refinement-gate.md` and its README row under a new M4
heading; possibly a Dependabot merge or a one-line lockfile / vendor change
on the owner's word. No new modules; a test or code change only as a
one-line correction the re-run or sync demands, recorded in the handoff.

## Implementation notes
Run the fresh-clone re-run first: its result decides whether the rest of
the session is a checkpoint or a stop. The routing night is the new part:
install the group and the toolchain before `phillysim run`, expect the
stage to take about a quarter of an hour (both nights' numbers are in the
EP-15 handoff), and read its night with `route status` while it runs and
`route verdict` after. The reference digests are in the EP-8b handoff
(public and curated), the EP-12 handoff (the two routing snapshots and the
clip), and the EP-15 handoff (both nights' core-run matrix digests and the
curated matrix's digest); a provider file whose bytes differ is the
refresh-drift finding this checkpoint exists to catch, and the answer is
an owner decision on a controlled refresh, never an in-checkpoint re-pin;
a matrix digest that differs is a determinism finding for the owner (the
OQ-C procedure, ADR-0008), also a stop. Keep each sweep as a literal
checklist in the handoff (item, evidence, pass / fixed / finding). For the
estimate review, the actuals are in the handoffs (EP-11 to EP-14 one
session each, EP-15 two; the nights outside the box). For the dependency
triage, `gh pr list --author app/dependabot` and `gh api
repos/{owner}/{repo}/dependabot/alerts` are the sources; decisions belong
to the owner. For the M4 pre-read, the gate's job is to turn the M4 row
into S packets (the remaining sources through the guarded path with
per-source snapshot IDs, conflation with its QA report, hours parsing
with its coverage number); EP-17 should be written so that a fresh agent
can author those packets from it and the carry-in section without
re-reading the whole baseline. The owner review at the end of this packet
covers, at least: commit and push, any Dependabot decision, any proposed
re-sizing, the re-plan trigger reading, and EP-17 as authored.

## Acceptance criteria & evidence
- [ ] Fresh-clone re-run green, fixture and real: `uv sync --locked
      --group routing`, the toolchain installed and checked, `uv run
      pytest`, the fixture verbs (11 ran, then 0 ran / 11 skipped; 11
      fresh; 8 of 8 snapshots, 11 of 11 stages; gate green; site built),
      the real pipeline from empty (10 ran including a routing night, then
      0 ran / 10 skipped; 10 fresh; 7 of 7 snapshots, 10 of 10 stages; gate
      green; site built), with counts and timings in the handoff; every
      provider data-file digest and every public and curated digest equal
      to the recorded references, the matrix's included.
- [ ] Docs sync: every real-pipeline-written file documented or listed as
      intermediate by policy; each checked statement recorded as pass or
      fixed; code gaps recorded as findings with an owning packet or gate.
- [ ] License-label sweep checklist complete with no open contradiction;
      the public zone Bucket A only; `git ls-files` shows no file under any
      `public/` zone, `site/dist/`, `data/`, or the toolchain directories.
- [ ] Baselines recorded in the handoff and appended to
      `phillysim/README.md`, compared to the budgets, peak RSS included.
- [ ] Dependency triage recorded: each open Dependabot PR and alert with
      the owner's decision, `uv lock --check` clean, the pins noted.
- [ ] "Estimate accuracy" table confirmed for EP-15 and M3 and extended
      with EP-16; the implication note rewritten with the M3 actual; the
      three re-plan triggers evaluated and recorded; any re-sizing proposed
      to the owner and the answer recorded.
- [ ] M4 gate pre-read recorded (inputs, questions, gaps);
      `EP-17-m4-refinement-gate.md` exists, follows the template, is S, and
      has its README row under the new M4 heading.
- Evidence: handoff payload; CI run on the checkpoint commit green on
  Windows + Linux.

## Tests / validation
`uv run pytest` in the fresh clone (with the routing group, so the
OSMnx-side tests run); the fixture and real verbs listed above;
`pre-commit run --all-files`; a scan of the diff for paths and
identifiers; CI on the commit.

## Resource budget
Attended: one session; the routing night about a quarter of an hour of it
(the machine awake). Unattended: none. Network: the seven providers once,
PyPI and the toolchain hosts once.

## Risks, rollback, stop condition
Fresh-clone re-run fails → **stop**; that is the "checkpoint finds drift"
trigger. A provider file's bytes differ → a finding and an owner decision
on a controlled refresh, never a re-pin here. A matrix digest differs from
the recorded nights → a determinism finding for the owner (OQ-C's
procedure), a stop. A license contradiction → stop. A re-plan trigger
fires → stop and surface it. Rollback: documentation only (revert the
commit); the scratch clone and its data root are deleted whatever the
outcome.

## Documentation / ADR updates
The files under "Likely components"; `roadmap/README.md` (the EP-16 row
closed, the Checkpoints paragraph's pointer to the fourth checkpoint, the
new M4 heading with EP-17's row); `roadmap/milestones.md` ("Spikes &
gates" checkpoint pointer, "Estimate accuracy", the M5 carry-in's first
item trimmed once confirmed). No ADR unless a pin is found behind and the
owner asks for an upgrade (then the ADR that holds the pin is amended).

## Handoff payload
_To be filled by the session that executes this packet: packet, files
changed, commands and tests with results, resource observations, decisions
and ADRs, owner-level decisions and answers, unresolved risks, no-go areas
touched, README row, the next checkpoint's due point, exact next packet
(EP-17)._
