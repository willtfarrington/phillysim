# EP-10 — Checkpoint 2: fresh-clone re-run with real data, docs sync, license sweep on published output, budgets, dependency triage, estimate accuracy, M3 gate pre-read

**Status:** [~] in progress (work done 2026-09-03; owner review pending) · **Milestone:** — (checkpoint after M2, before the M3 refinement gate) · **Effort:** S (1 session, high confidence) · **Parallel with:** —

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

## Handoff payload (filled 2026-09-03)
- **Packet:** EP-10 — work done 2026-09-03 in one session; Planning
  Baseline v1.0. Status and commit recorded in the owner-review section
  at the end of this payload.
- **Files changed (documentation only; no module, test, data, or
  dependency change):** new `roadmap/EP-11-m3-refinement-gate.md`;
  changed `roadmap/README.md` (EP-10 row; "M3 — Routing spike" heading
  opened with EP-11 as its first row; "M4–M8" placeholder; document index
  row; checkpoint due point), `roadmap/milestones.md` (M3 Packets column;
  "Spikes & gates" pointer; "Estimate accuracy" rows EP-9, EP-5a, EP-5b,
  EP-6, EP-7, EP-8a, EP-8b, M2; the implication note rewritten; the
  EP-10 re-plan evaluation; the re-sizing proposal), `roadmap/quality.md`
  (test matrix: five real sources, eight real stages, baselines row,
  column header), `roadmap/architecture.md` (`acquire` row names all five
  sources), `docs/DATA-LICENSES.md` (labeling status names the roads
  snapshot and records this sweep), `docs/data-dictionary.md` (contract
  note), `README.md` (dictionary line), `phillysim/README.md` ("Resource
  baselines": the EP-10 table), `CHANGELOG.md`, this file.
- **Commands/tests run + results (fresh clone of `main` at `deb21fc`,
  `git clone -c core.longpaths=true` into a scratch directory, deleted
  afterwards with its data root).** Clone 1.4 s. `uv sync --locked` 9 s
  cold. `uv run pytest` **461 passed, 3 skipped** in 47 s (cold caches; the
  3 skipped are the real-data tests). Fixture verbs: `run --fixture` 11
  ran / 0 skipped in 1.6 s; second `run --fixture` **0 ran / 11 skipped**
  in 1.0 s; `status --fixture` 11 fresh; `verify --fixture` 8 of 8
  snapshots, 11 of 11 stages; `gate --fixture` green, 5 files Bucket B
  (ODbL-1.0), 8 sources; `site build --fixture` `county_boundary (1)`.
  **Real pipeline from an empty data root:** `phillysim run` preflight
  passed on the real thresholds, then `acquire` 7.0 s (all five sources
  through the guarded path, every fetch one attempt: ACS 18,313,708 B in
  0.6 s and 65,043,091 B in 1.3 s, CenPop 144,662 B in 0.2 s, SNAP
  24,036,753 B in 1.2 s and its data page 44,082 B in 0.3 s, roads
  1,352,071 B in 0.3 s, tracts 13,109,450 B in 0.5 s, four copies of the
  311,057 B Census terms page in 0.5 s each; 123.3 MB in all), `validate`
  3.0 s (408 / 408 / 1,609 / 426 / 408 rows, no violation), `spine` 0.2 s,
  `demographics` 0.8 s, `snap_retailers` 2.3 s, `basemap` 0.3 s, `metrics`
  0.0 s, `publish` 0.5 s: **8 ran / 0 skipped, 15.1 s wall**; second
  `run` **0 ran / 8 skipped** in 1.1 s; `status` 8 fresh; `verify` 5 of 5
  snapshots, 8 of 8 stages; `gate` green, **5 files Bucket A
  (CC-BY-4.0), 4 sources**, methods `slice-qa-1`; `site build`
  `county_boundary (1), roads (426)`, MapLibre 6.7.0. `pytest
  tests/test_spine_invariants.py tests/test_basemap.py
  tests/test_slice_metric.py tests/test_destinations.py --real-data-root
  ../data` 57 passed in 1.9 s. Working clone: `pre-commit run
  --all-files` all hooks passed; diff scanned for usernames and absolute
  paths, none; `git ls-files` shows nothing under any `public/` zone or
  `site/dist/`.
- **Digest comparison (fresh clone versus the working clone's `data/`,
  whose digests are the EP-5a / EP-6 / EP-7 / EP-8b references): ALL
  EQUAL.** Provider data files: `acsdt5y2024-b01003.dat` `38d1a992…`,
  `acsdt5y2024-b08201.dat` `2f64e698…`, `CenPop2020_Mean_TR42.txt`
  `c5c3feea…`, `snap-retailer-locator-data2005-2025.zip` `872a6f81…`,
  `tl_2025_42_tract.zip` `818bdadf…`, `tl_2025_42101_roads.zip`
  `b0f60f79…`; every manifest's `license_bucket`, `license_note`, URLs,
  and `terms_archive` equal. Curated: `tracts_spine.parquet` `0c1d2349…`,
  `snap_retailers.parquet` `a2887ec3…`, `basemap_roads.parquet`
  `70469c4e…`, `tract_metrics.parquet` `fa8b8bdd…`;
  `intermediate/acs_tracts.parquet` `94cefd3a…`. Public: `manifest.json`
  `7f2a19d4…`, `tracts.geojson` `18e6f19c…`, `tracts.csv` `ce380762…`,
  `sites.geojson` `65962e53…`, `sites.csv` `ea3bdea9…`, `basemap.geojson`
  `04141abb…`. The four Census `terms.html` archives differ per fetch
  (recorded since EP-5a; excluded by the brief) and `acquire` admitted
  every one, so the checked sentence is still there; the SNAP
  `source-page.html` came back byte-identical (`fd7e5590…`), so the
  as-of sentence and the vintage are unchanged. **No refresh drift; no
  controlled refresh is due.** The intermediate reports agree with the
  data cards and method cards to the number (1,609 retailers, 164
  supermarket-format, 340 / 115 tracts, 2 unassigned; 426 roads, 46 /
  380, 1,044.371 km, 0.0 m outside; min / median / max 35.3 / 622.5 /
  3,150.6 m; quintile edges as published).
- **Resource observations (the table is in `phillysim/README.md`
  "Resource baselines", EP-10 block; all within budget).** Fresh clone in
  all 620 MB (`.venv` 477 MB, data root 125.9 MB, built site 2.77 MB,
  `.git` 4.6 MB; the packet's budget said about 0.6 GB). Data root: raw
  123.3 MB, public 1.56 MB, curated 891 KB, intermediate 22 KB, state file
  8 KB, cache and quarantine empty (workspace budget 50 GB). Public zone
  1,555,668 B raw, **331,050 B gzipped** (architecture.md: sub-MB
  gzipped). Preflight: 422.9 GB free (need ≥ 150), 68.1 GB RAM (need
  ≥ 25.8), Python 3.13.15, six locked packages present. CI run
  33795124091 on `deb21fc`: ubuntu 49 s (pytest 32 s), windows 96 s
  (pytest 54 s). Network 123 MB, the same five files as EP-8b. Peak RSS
  not measured: deferred to the M3 spike harness (owner decision at
  authoring, 2026-09-03). One session, at the S estimate.
- **Checklist 1, docs / data-dictionary sync (pass / fixed / finding).**
  Every file the real pipeline writes is documented or listed as
  intermediate by policy: the five raw snapshots with manifests and
  archived pages (dictionary "Snapshot manifest" and "Raw sources"; pass),
  `intermediate/acquisition.json`, `validation.json`,
  `acs_tracts.parquet`, `snap_retailers.json`, `basemap.json`,
  `slice_metric.json` ("Intermediate files"; pass), the four curated
  tables (pass), the six public files and the manifest ("Public zone",
  version 2; pass), the state file (pass). Statements checked against the
  code and tests: `phillysim/README.md` (layout, verbs, stage list, the
  122 MB / hosts, the gate rules, the site build; pass), root `README.md`
  (status paragraph pass; the documents table's dictionary line **fixed**
  to name the real tables and public schema 2), `site/README.md` (build
  steps, the manifest-member table, the stacking order, the contrast
  table pinned by test; pass), the five data cards and their index
  (numbers against the fresh reports; pass), the two method cards
  (mapping table rendered from the package and pinned by test; the slice
  numbers; pass), `docs/DATA-LICENSES.md` (records pass; the labeling
  status **fixed**: it named three source snapshots where the real zone
  now derives from four, `tiger_roads` included), `docs/CLAIMS.md`
  "Mechanical enforcement" (the nine prohibited terms equal
  `gate.PROHIBITED_NAME_TERMS`; the `qa_` rules; pass),
  `roadmap/architecture.md` stage table rows 1–11 with 4b and 4c (row 1
  **fixed**: it named only the three spine sources; the rest pass),
  `roadmap/quality.md` test matrix (**fixed**: "three real spine sources"
  → five real sources, "seven stages (EP-5a–EP-7)" → eight stages ending
  in a site driven in the browser (EP-5a–EP-8b); the baselines row and
  the column header dated), `roadmap/sources.md` (pass),
  `docs/data-dictionary.md` "Raw fake sources" (**fixed**: EP-6 had
  landed), `CHANGELOG.md` (test counts, stage lists, file lists; pass).
  Code gaps found: none (every fix was a documentation statement that had
  fallen behind; no code contradicted a document).
- **Checklist 2, license-label sweep on the real published output (all
  pass; no contradiction).** Every file in `public/manifest.json`
  (`basemap.geojson` 427 rows, `sites.csv` / `sites.geojson` 164,
  `tracts.csv` / `tracts.geojson` 408): sources `cenpop`,
  `snap_retailers`, `tiger_roads`, `tiger_tracts`, all Bucket A in their
  raw manifests, derived bucket A, label `CC-BY-4.0`, no notices, the
  file's label and attribution equal to the zone's; the three GeoJSON
  in-file `license` and `attribution` members equal the manifest's; the
  attribution lines equal the four adapters' `citation` strings and the
  attribution entries of the four DATA-LICENSES snapshot records; the
  four `sources[].license_note` texts equal the raw manifests'
  `license_note` (and the DATA-LICENSES records say the same in prose);
  the ACS snapshot feeds nothing published (its record says so). The
  fixture zone's Bucket B path (ODbL-1.0 label with the ODbL and
  OpenStreetMap notices) ran in this session's fresh clone and runs in CI
  (`gate --fixture`, `tests/test_publish.py`). The five CI samples'
  `license_note` texts each name the source, the subset, and the
  `2026-09-02` snapshot; their README names all five sources. `git
  ls-files`: nothing under any `public/` zone or `site/dist/`. The ODbL
  notice sentence in `phillysim.publish.bucket` ("Any rights in
  individual contents are licensed under the Database Contents License")
  is still flagged for legal review with the site's export UI at M6 (EP-7
  handoff); unchanged, confirmed.
- **Checklist 3, dependency triage.** Open Dependabot PRs: **none**
  (`gh pr list --author app/dependabot --state open`). Dependabot alerts:
  eight, all in the `dismissed` / `auto_dismissed` state (the vendored
  `source material/` JKAN tree's Ruby and npm lockfiles, dismissed by
  owner decision at EP-9 as "not used"; nothing open, nothing new since;
  no security alert to surface). `uv lock --check` clean (41 packages).
  Vendored MapLibre GL JS 6.7.0 is the **current** npm release (published
  2026-09-02; no newer version). `.github/workflows/ci.yml` pins
  `actions/checkout` at `3d3c42e5…` = tag v7.0.1 and `astral-sh/setup-uv`
  at `20cfd1bf…` = tag v10.0.1, both the **latest** releases of their
  repositories (2026-07-20 and 2026-08-14). Nothing to merge, defer, or
  upgrade; no decision needed beyond confirming the reading (owner review
  below). The EP-9 calendar reminder for the next Dependabot triage stays
  2026-10-05.
- **Checklist 4, estimate accuracy.** Rows appended in `milestones.md`
  from the packet handoffs: EP-9 1 of 1; EP-5a 1 of 1 (split); EP-5b 1
  of 1; EP-6 1 of 1–2 (0.67); EP-7 1 of 1–2 (0.67); EP-8a 1 of 1 (split);
  EP-8b 1 of 1; **M2 6 of 4–6 (1.20)**. Twelve of twelve packets one
  session each, by construction of the sizing rule; M2 at its high bound
  because the four M packets as authored resolved to two sessions each
  where split and one each where not (mean 1.5, the M midpoint), none
  under a session. Implication note rewritten: plan against the high
  bound of each remaining range; the gate's decomposition count replaces
  the range at the next checkpoint. **Re-plan triggers:** (1) no kill
  criterion exists before the M3 spike, not fired; (2) drift: re-run green
  and byte-identical, license sweep clean, five documentation statements
  fixed, no code contradicted a document, not fired; (3) no packet over
  its estimate, not fired. **Re-sizing proposed to the owner (not
  applied):** A, keep the M3–M8 ranges and plan against their high bounds
  (33 sessions; total about 44 of 34–46, inside the 40–50 contingency);
  or B, raise M4 5–7 → 6–8 and M6 6–10 → 8–12 now (total 39–51).
- **M3 gate pre-read.** *Inputs:* milestones.md M3 row (go = walk+transit
  within budgets; kill = documented fallback; wall ≤ 8 h, process-tree
  RSS ≤ 22 GB, determinism within band, sanity gates; 3 attended sessions
  plus unattended runs) and "Spikes & gates" (run matrix pre-scripted in
  session 1; unattended overnight runs outside the box; KILLED-BY-EVIDENCE
  versus TIMEBOX-EXHAUSTED, one owner-approved extension); methodology.md
  "Travel model" (r5py, pinned JDK 21, checksummed R5 jar, 12 GB heap, CPU
  only; walk 4.8 km/h and the 3.0 km/h sensitivity; walk+transit on SEPTA
  GTFS; pinned typical Wednesday 08:00–20:00, one departure per minute,
  median and 85th percentile; Saturday window; straight-line as QA only;
  fallback OSMnx 2.x + scipy sparse Dijkstra walk-only, partial fallback
  permitted), "Units and origins" (CenPop population-weighted centers,
  408 tracts; block-group sensitivity is M5's), "Validation" (≥ 95 %
  finite pairs; ≥ 80 % of hand-checked OD times within tolerance; walk
  concordance ρ ≥ 0.95 against the fallback engine); architecture.md
  "Stack" (Temurin JDK 21 exact build, `JAVA_HOME` per invocation, R5 jar
  by checksum) and "Resource budgets" (routine RAM ≤ 24 GB; routing
  budget 20 GB, kill 22 GB, sampled ≥ 1 Hz; workspace ≤ 50 GB; ≥ 150 GB
  free; ≤ 8 of 16 processors); ADR-0001; ADR-0003 (OSM content is Bucket
  B and contagious); ADR-0007; scope.md kill criteria; sources.md (OSM
  via Geofabrik, ODbL; SEPTA GTFS custom terms, pin releases, never
  republish, re-read terms each refresh; walk-only fallback if SEPTA
  terms become unusable); quality.md (AM-2 reproducibility wording;
  "Performance smoke" lands with the spike); open-questions.md OQ-C;
  "Refinement-gate carry-ins": **none names M3** (the M4, M5, and M5/M6
  entries stay). What exists to route between today: 408 spine origins
  and the SNAP layer (164 supermarket-format, 1,609 in all). *Questions
  the gate must answer* (written into EP-11, eight of them): the JDK
  build and R5 release with checksums and where they live, and whether
  r5py installs from wheels; the determinism measurement and band; the
  hand-check tolerance and reference; the run matrix the ≤ 8 h wall
  applies to; the OSM extent, the GTFS feed set, and the snapshot-ID rule
  for sources acquired after `2026-09-02`; whether the fixture's
  `network` / `travel_times` stubs get real bodies (which would put the
  JVM in CI); where the routing outputs land and whether the spike
  publishes anything (recommendation: nothing; the zone stays Bucket A
  until M5); the time box and who calls TIMEBOX-EXHAUSTED. *Gaps in the
  planning documents* (findings, owned by EP-11): no JDK build, R5
  version, or checksum value is pinned anywhere; the determinism band and
  the hand-check tolerance are unstated; the two routing sources have no
  adapter, allowlist, guard limits, terms sentence, data card, or CI
  sample, and their sizes (hundreds of MB) exceed every guard cap set so
  far; one `SNAPSHOT_ID` for all sources; the fixture's `network.json`
  and `travel_times.parquet` shapes are the generator's, not r5py's; the
  CI performance-smoke test has no defined measurement; peak RSS has
  never been measured. **EP-11 authored** from `_TEMPLATE.md` as a
  documentation-only S packet (scope: carry-ins, inputs, sources and
  licensing path, decomposition into S packets from EP-12, owner
  decisions recorded), with its README row under the new "M3 — Routing
  spike" heading.
- **Decisions made (routine, agent's call, logged):** the digest
  reference is the working clone's `data/` (whose digests the EP-5a,
  EP-6, EP-7, and EP-8b handoffs record) compared file by file, terms
  archives excluded per the brief; the four `pytest --real-data-root`
  modules run were the spine, basemap, slice-metric, and destinations
  invariants; the stale documentation statements were fixed in place
  (each a one-line-scale correction inside the claims matrix); the
  EP-9 implication note was kept below the new one, marked superseded,
  rather than deleted; the EP-11 questions are numbered so the gate's
  handoff can answer them by number; the third checkpoint's due point is
  written as "with the M3 verdict packet or EP-15, whichever comes
  first". No ADR.
- **Owner-level decisions (put to the owner at the end of the session;
  outcomes recorded here):** see "Owner review" below.
- **Unresolved risks / questions:** none new for the checkpoint. For
  EP-11: the eight questions above. For M6: the ODbL notice legal review
  (unchanged). The Census terms page's per-fetch variation means the
  archived `terms.html` digests will never match across acquisitions;
  the sentence check, not the digest, is the terms evidence (recorded
  since EP-5a; no action).
- **No-go areas touched:** none (no PHI, no secret, nothing deployed,
  nothing under a `public/` zone or `site/dist/` committed, no dependency
  changed, the acquisition went only through the guarded path into a
  scratch data root that was deleted, no third-party request beyond the
  five providers, GitHub, PyPI, and npm's registry metadata for the
  version check).
- **Next checkpoint due:** about five packets after EP-10 (with the M3
  verdict packet or EP-15, whichever comes first); recorded in
  `roadmap/README.md` "Checkpoints" and `milestones.md` "Spikes & gates".
- **Exact next packet: EP-11** (the M3 refinement gate, as authored).

### Owner review (2026-09-03)

Five decisions put to the owner interactively at the end of the session;
the recommended option was accepted for each:
- **Commit, push, CI, handoff:** yes. One work commit, CI on both
  platforms, then the status commit recording this payload (commit and
  run IDs in the status line at the top of this file and the CHANGELOG).
- **Dependency triage:** no action. Nothing to merge, defer, close, or
  upgrade (no open PR, no open alert, lock clean, MapLibre and the action
  pins current); the 2026-10-05 triage reminder stands.
- **Re-sizing:** option A. The M3–M8 ranges in the milestones table stay
  as written; the planning number is each range's high bound (M3–M8 33
  sessions, total about 44 of the 34–46 baseline, inside the 40–50
  contingency), and each refinement gate's packet count replaces its
  milestone's range at the next checkpoint. Recorded in `milestones.md`
  "What this implies (EP-10)"; no baseline amendment.
- **Re-plan triggers:** the reading that none fired is accepted; the
  roadmap proceeds to EP-11.
- **EP-11:** accepted as authored; it is the next packet.
