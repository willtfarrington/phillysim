# EP-11 — M3 refinement gate: decompose the routing spike into S packets

**Status:** [x] c6b5372 (done 2026-09-03) · **Milestone:** M3 · **Effort:** S (1 session, high confidence) · **Parallel with:** —

## Outcome & value
After this packet the M3 routing spike exists as issue-ready packet files,
`EP-12-<slug>.md` onward, one session each, authored from
[_TEMPLATE.md](_TEMPLATE.md) and listed under the README's "M3 — Routing
spike" heading, so that the first spike session starts with its inputs,
budgets, run matrix, and stop conditions written down and nothing to
rediscover. The gate is documentation only: it decides *how* the spike is
run (which sources, which pins, which runs, which numbers decide) and
records the owner's answers to the questions below; it runs no routing.
It is the first refinement gate of the roadmap (milestones.md: M3+ carry a
mandatory gate that decomposes to packet standard before implementation
begins), authored here so that the procedure the M4–M8 gates follow is
written once. The pre-read that feeds it is in the EP-10 handoff
([EP-10](EP-10-checkpoint-2.md), "M3 gate pre-read").

## Scope
- in:
  1. **Apply the carry-ins.** Read `milestones.md` "Refinement-gate
     carry-ins" and apply every entry that names M3. As of 2026-09-03
     there is none (the M4, M5, and M5/M6 entries stay for their gates);
     say so in the handoff, since the README's reading order requires the
     check.
  2. **Fix the spike's inputs** in the packet files, from the documents the
     pre-read lists: the go/no-go and numeric criteria (milestones.md M3
     row and "Spikes & gates": wall ≤ 8 h for the pre-scripted run
     matrix, process-tree RSS ≤ 22 GB with the 20 GB budget and the 22 GB
     kill, determinism within a band, the sanity gates of methodology.md
     "Validation": ≥ 95 % finite origin–destination pairs, ≥ 80 % of
     hand-checked OD times within tolerance, walk-network concordance
     ρ ≥ 0.95 against the fallback engine; the outcome codes
     KILLED-BY-EVIDENCE and TIMEBOX-EXHAUSTED with one owner-approved
     extension before the fallback); the travel model (methodology.md
     "Travel model": r5py, pinned JDK 21 and checksummed R5 jar, 12 GB
     heap, CPU only; walk 4.8 km/h with the 3.0 km/h sensitivity;
     walk+transit on SEPTA GTFS; a pinned typical Wednesday 08:00–20:00,
     one departure per minute, median and 85th-percentile summaries;
     Saturday window for market metrics); the origins (methodology.md
     "Units and origins": the spine's CenPop population-weighted centers,
     408 tracts, plus the block-group sensitivity that is M5's, not the
     spike's); the destinations that exist today (the 164 supermarket-format
     SNAP retailers and the 1,609-row all-retailer variant in
     `curated/snap_retailers.parquet`); the stack pins (architecture.md
     "Stack", ADR-0001: project-local Temurin JDK 21 exact build with
     `JAVA_HOME` set per invocation, R5 jar pinned by checksum, everything
     Python from wheels, the GDAL / fiona ban); the resource budgets
     (architecture.md: routine peak RAM ≤ 24 GB, workspace ≤ 50 GB,
     preflight ≥ 150 GB free, parallelism ≤ 8 of 16 logical processors,
     unattended overnight runs accounted separately from session time);
     the fallback (methodology.md: OSMnx 2.x + scipy sparse Dijkstra,
     walk only, partial fallback permitted; scope.md kill criteria;
     milestones.md risk table; the AM-2 wording: pinned seeds or a
     documented variance band, "checksum-identical within the pinned
     Windows environment; canonicalized-value hashes cross-platform",
     quality.md); and OQ-C (R5 determinism), which the spike resolves.
  3. **Fix the sources the spike needs and their licensing path.** Two new
     real sources, each through the guarded acquisition path with its own
     adapter, allowlist, guard limits, terms page, contract, data card,
     DATA-LICENSES record, and CI sample: the street network, OpenStreetMap
     via Geofabrik (ODbL, **Bucket B**: the first Bucket B source of the
     real pipeline, so every file of the public zone that carries a
     column computed over it becomes ODbL with the OpenStreetMap notices,
     which the gate already enforces and the fixture zone already
     exercises), and SEPTA GTFS (custom terms: revocable, redistribution
     permitted, fees reservable; pin the release, archive the terms page
     at every acquisition, **never republish the feed**; computed travel
     times are facts, matrices carry no feed contents). Decide the extract
     (a Pennsylvania or a clipped Philadelphia-area extract; the guard
     caps and the ≤ 50 GB workspace size it), the GTFS feed set (bus, rail,
     and which static feed URL), the snapshot IDs (a new date, not the
     pinned `2026-09-02` of the five existing sources: the pipeline's
     single `SNAPSHOT_ID` becomes per-source or the constant is bumped
     with a changelog note; an owner decision), and how the terms-page
     sentence check is written for each provider.
  4. **Decompose into S packets and author them.** The expected shape,
     from the EP-10 pre-read (adjust on the evidence, never above one
     session each): the routing toolchain and harness (JDK and R5 pins
     with checksums, r5py in the locked stack behind the wheel-only rule,
     the process-tree RSS sampler at ≥ 1 Hz, the wall clock, the run
     record, a smoke route on the tinycity fixture or a tiny real subset,
     the CI performance-smoke test quality.md defers to this milestone);
     the two source adapters (one packet each, or one for both if the
     evidence says they fit); the pre-scripted run matrix and the
     unattended runs (a script that runs the matrix overnight, records
     every number the criteria need, and writes the outcome code; the
     unattended time is outside the session box); the verdict packet
     (reads the run records against the criteria, resolves OQ-C with the
     measured determinism band, records go or kill with the evidence,
     invokes the walk-only fallback if killed, and closes M3 in the README
     with the go/no-go evidence). Each packet gets the template's every
     section, its own safety preconditions, and its README row.
  5. **Record the owner's decisions** on the questions below in the
     handoff and, where they are architecture-level or hard to reverse
     (the JDK and R5 pins, the determinism band, the OSM extent), as an
     ADR or an amendment to methodology.md / architecture.md.
- out (explicit non-scope): running r5py, downloading any source,
  installing a JDK, or changing any code; authoring M4 packets (M4
  parallels M3 and gets its own gate, which applies the M4 carry-ins);
  resolving OQ-C by argument (the spike measures it); changing the
  numeric criteria or the budgets (a change there is a baseline change,
  not a gate decision).

## Prerequisites & locked decisions
- prerequisites: EP-10 (checkpoint 2; its M3 pre-read), M2 done.
- locked decisions honored: milestones.md M3 row and "Spikes & gates";
  methodology.md "Travel model", "Units and origins", "Validation";
  architecture.md "Stack" and "Resource budgets"; ADR-0001 (stack, pinned
  JVM), ADR-0003 (license buckets; OSM-derived content is Bucket B and
  contagious), ADR-0006 (version axes: dependencies, snapshots, methods),
  ADR-0007 (analysis CRS EPSG:26918; routing inputs and outputs are
  projected from it, WGS 84 only at publication); README packet-sizing
  rule (every new packet S, one session); docs/CLAIMS.md wording rules for
  any prose the packets carry; the download-path order and the
  terms-archive stop condition (EP-5a); the fixture's `network` and
  `travel_times` stubs stay stubs until a packet replaces them.
- dependencies: none outside the repository (documentation only). The
  packets it authors will depend on Geofabrik (`download.geofabrik.de`),
  SEPTA's developer site for the GTFS feed and its terms page, Adoptium
  for the Temurin JDK 21 build, and the R5 release for the jar.

## Safety preconditions
Standing policy (see EP-1). Packet-specific: no code, data, or dependency
changes; the packets authored must each carry their own safety
preconditions, and at least these: the OSM extract and the GTFS feed enter
`raw/` only through the guarded path (allowlist, size caps sized for files
of hundreds of megabytes, zip and PBF handled without extraction where the
reader allows it, terms archived and checked); the GTFS feed is never
copied under `public/` or `site/`; any file that carries a value computed
over the OSM network is labeled Bucket B by derivation, never by hand; the
JDK and the R5 jar are downloaded once, verified against recorded
checksums, and installed project-local (never on `PATH` or in the system);
the RSS sampler kills the process tree at 22 GB; unattended runs write
only under the data root and a run-record directory; CI stays offline and
never runs the JVM unless a packet decides otherwise with the owner; no
machine identifier or absolute path enters a tracked file (run records
scrub the data root like the state file does).

## Likely components & contracts (proposed)
Documentation only: `roadmap/EP-12-….md` onward (from `_TEMPLATE.md`),
`roadmap/README.md` (the "M3 — Routing spike" table filled in; the
"M3–M8" placeholder section shortened to M4–M8), `roadmap/milestones.md`
(M3 row's Packets column; the carry-in check recorded; a new
"Refinement-gate carry-ins" entry only if a packet defers something),
`roadmap/open-questions.md` (OQ-C pointed at the verdict packet), possibly
`roadmap/adr/0008-….md` (JDK / R5 pins and the determinism band, if the
owner decides them here rather than in the toolchain packet),
`CHANGELOG.md`, this file's handoff. No module, test, or data change.

## Implementation notes
Read, in this order, before writing anything: the EP-10 handoff's "M3 gate
pre-read" (inputs, questions, gaps); milestones.md (M3 row, "Spikes &
gates", "Session model", "Risks & contingencies", "Refinement-gate
carry-ins"); methodology.md ("Units and origins", "Travel model",
"Validation"); architecture.md ("Stack", "Resource budgets", "Security");
ADR-0001, ADR-0003, ADR-0007; sources.md (the OSM and SEPTA rows and the
refresh strategy); quality.md (the version axes, the test matrix's
"Performance smoke" and "Integration" rows); scope.md (kill criteria);
open-questions.md (OQ-C); the EP-5a and EP-6 packet files as the pattern
for a source adapter packet; `phillysim/README.md` "Resource baselines"
for what the machine and the pipeline do today.

**Questions the gate must answer** (each with the owner unless marked
routine; record every answer in the handoff):
1. Which Temurin JDK 21 build and which R5 release, with checksums, and
   where they live (`<repo>/.jdk/`, `<repo>/.r5/`, or under the data
   root's `cache/`); how `JAVA_HOME` is set per invocation; whether r5py
   and its Java bridge install from wheels on Windows (the dependency
   policy test must stay green).
2. The determinism band: what is measured (identical checksums of the
   matrix across two runs on the pinned environment; the distribution of
   per-pair differences if not), how many repeat runs, and what band is
   "within" for the go verdict (AM-2 allows a documented variance band;
   OQ-C is closed by the number the spike measures).
3. The tolerance in "≥ 80 % of hand-checked OD times within tolerance"
   (methodology.md leaves it unstated) and how many pairs are hand-checked
   against which reference (a public trip planner is a manual spot check,
   never a data source).
4. The run matrix that the ≤ 8 h wall applies to: 408 origins × the
   destinations that exist (164 supermarket-format, or all 1,609), two
   modes, the 720 departures of the pinned window, plus the 3.0 km/h
   sensitivity and the Saturday window; which of these are in the spike
   and which wait for M5.
5. The OSM extent and the GTFS feed set (item 3 above) and the snapshot ID
   rule for sources acquired after `2026-09-02`.
6. Whether the fixture pipeline's `network` and `travel_times` stubs get
   real bodies in M3 (r5py on the synthetic tinycity network, which would
   put the JVM in CI) or stay stubs with the real bodies tested only by
   the spike's own records (the offline-CI policy favours the latter; the
   CI performance-smoke test then measures the fixture stages, not
   routing).
7. Where the routing outputs land and in what shape
   (`curated/travel_times.parquet` per the data dictionary's travel-time
   matrix section: `origin_geoid`, `site_id`, `mode`, `time_median_min`,
   `time_p85_min`, censored at 120) and which public file, if any, the
   spike publishes (recommendation: none; the spike's evidence is its run
   records and the curated matrix; publication of travel-time metrics is
   M5, so the public zone stays Bucket A until then).
8. The time box: three attended sessions plus unattended runs; what one
   owner-approved extension is; who calls TIMEBOX-EXHAUSTED and when the
   fallback packet starts.

**Gaps the pre-read found in the planning documents** (the gate fixes each
by answering the question above or by recording it as an open question):
no JDK build, R5 version, or checksum is pinned anywhere yet (architecture
and ADR-0001 say "pinned" without values); the determinism band and the
hand-check tolerance are unstated; the two routing sources have no
adapter, allowlist, guard limits, terms-page sentence, data card, or CI
sample, and their file sizes (hundreds of megabytes) exceed every guard
cap set so far; the pipeline pins one `SNAPSHOT_ID` for every source; the
fixture's `network.json` and `travel_times.parquet` shapes are the
fixture generator's, not r5py's; the CI performance-smoke test has no
defined measurement; peak RSS has never been measured (the sampler is the
spike's first deliverable).

A fresh agent should be able to author the M3 packets from this file, the
EP-10 handoff, and the documents named above without re-reading the whole
baseline. Keep each authored packet to one session by construction: if a
packet's outcome needs two, author two packets with consecutive integers.
The owner review at the end of this packet covers, at least: every
question above, the packet decomposition as authored, any ADR, and commit
and push.

## Acceptance criteria & evidence
- [ ] The M3 carry-in check is recorded (none as of 2026-09-03, or applied
      and deleted if one appeared since).
- [ ] The M3 packet files exist from EP-12 onward, each from the template
      with every section filled, each S, each with its README row under
      "M3 — Routing spike", sequenced so that the toolchain and sources
      precede the runs and the runs precede the verdict.
- [ ] Every question above has a recorded answer (or is recorded as an
      open question with its decision point) in this file's handoff, and
      the hard-to-reverse ones are in an ADR or a document amendment.
- [ ] The numeric criteria, budgets, outcome codes, and fallback wording
      appear verbatim in the packets that apply them, traceable to
      milestones.md, methodology.md, and architecture.md.
- [ ] `milestones.md` M3 row names its packets; `open-questions.md` OQ-C
      names the verdict packet; `CHANGELOG.md` has the line.
- Evidence: the files; the owner review recorded in the handoff; CI green
  on the commit (documentation only, so the suite is unchanged).

## Tests / validation
`uv run pytest` and `pre-commit run --all-files` on the commit (no test
changes expected); a read-through of each authored packet against
`_TEMPLATE.md` (every heading present, the sizing note deleted); a scan of
the diff for machine identifiers and absolute paths.

## Resource budget
Trivial: documentation only. The packets it authors carry the spike's
budgets (architecture.md).

## Risks, rollback, stop condition
A question the owner cannot answer at the gate → record it as an open
question with its latest decision point and author the packet that
resolves it first; do not guess a pin or a band. A carry-in that names M3
appears → apply it first. The decomposition exceeding about five S
packets → still author them all (the number is the estimate; EP-10
proposed that the gate's count replaces the milestone range), and record
the count for the next checkpoint's estimate review. Rollback: revert the
documentation commit.

## Documentation / ADR updates
`roadmap/README.md` ("M3 — Routing spike" table, the M4–M8 placeholder,
the document index row for EP-12 onward), `roadmap/milestones.md` (M3
Packets column), `roadmap/open-questions.md` (OQ-C), `CHANGELOG.md`, a
possible ADR-0008; this file's status and handoff.

## Handoff payload (filled 2026-09-03)
- **Packet:** EP-11 — done at commit `c6b5372` (+ this status commit),
  2026-09-03, one session; Planning Baseline v1.0. CI run
  [33799859669](https://github.com/willtfarrington/phillysim/actions/runs/33799859669)
  on `c6b5372` green on `ubuntu-latest` (55 s) and `windows-latest`
  (132 s); the suite is unchanged (documentation only). Owner review at
  the end of this payload.
- **Files changed (documentation only; no module, test, data, or
  dependency change):** new `roadmap/EP-12-routing-sources.md`,
  `roadmap/EP-13-routing-toolchain-harness.md`,
  `roadmap/EP-14-routing-run-matrix.md`, `roadmap/EP-15-routing-verdict.md`,
  `roadmap/adr/0008-routing-toolchain-pins.md`; changed
  `roadmap/README.md` (the "How to read" pointer; the document index row
  for EP-12–EP-15 and the ADR-0008 mention; the "M3 — Routing spike"
  paragraph and table with four rows; the "M4–M8" placeholder naming the
  procedure and the next gate), `roadmap/milestones.md` (M3 row's
  Packets column; the "Spikes & gates" M3 bullet; the EP-11 packet count
  under "What this implies (EP-10)"; a new "M5 — routing outputs and the
  sensitivity runs" carry-in), `roadmap/open-questions.md` (OQ-C: the
  measurement, the band, the owner EP-15), `CHANGELOG.md`, this file.
- **Commands/tests run + results.** Working clone: `uv run pytest` →
  **461 passed, 3 skipped** in 30.6 s (unchanged); `pre-commit run
  --all-files` all hooks passed (after `git add -A`; `site/dist/` is
  ignored, no scratch build dir existed); each authored packet checked
  against `_TEMPLATE.md` by script: every heading present in the
  template's order, the sizing note absent, the header line S; the diff
  and the five new files scanned for user names, machine identifiers,
  and absolute paths → none (the one hit, `LOCALAPPDATA`, is the
  environment-variable name r5py reads its cache directory from). No
  routing was run, nothing was downloaded into the data root, no JDK
  installed, no code changed. Pin values were read from the providers'
  release records over the network (Adoptium's API and the
  `temurin21-binaries` release, the `r5py/r5` and `septadev/GTFS` release
  assets through `gh api`, r5py's source on GitHub, Geofabrik's region
  page and the `.md5` sibling of the dated extract, SEPTA's developer
  page) and wheel availability was checked with `uv pip compile
  --only-binary :all:` for Windows and Linux on Python 3.13 in the
  scratchpad (nothing installed).
- **Carry-in check (scope item 1).** `milestones.md` "Refinement-gate
  carry-ins" read on 2026-09-03: the entries are M4 (SNAP follow-ups),
  M5 (supermarket-format sensitivity), M5 / M6 (the QA slice column and
  the public schema), and M5 (OQ-I reliability conventions). **None
  names M3; nothing to apply or delete.** One new entry was added by
  this gate for the M5 gate (routing outputs and the sensitivity runs;
  EP-15 completes it with the verdict).
- **The eight questions, answered (owner-reviewed; recorded in
  ADR-0008).**
  1. *Toolchain.* Temurin JDK **21.0.12.1+1** (Windows x64 zip
     205,073,461 B, SHA-256 `f9d6e191…8b4e`; Linux tarball recorded for
     the WSL2 fallback) and the R5 jar **`r5-v7.6-r5py-all.jar`** from the
     `r5py/r5` release `v7.6-r5py` (65,104,016 B, SHA-256 `bb3935be…0eb5`,
     the jar r5py 1.1.7 pins in its own `util/classpath.py`), installed
     by a `phillysim toolchain install` verb through the guarded download
     path into `<repo>/phillysim/.jdk/jdk-21.0.12.1+1/` and
     `<repo>/phillysim/.r5/` (gitignored: `.jdk/` and `*.jar` already,
     `.r5/` added by EP-13); `JAVA_HOME` set only in the routing child
     process's environment, plus `JAVA_TOOL_OPTIONS=-XX:ActiveProcessorCount=8`,
     the 12 GB heap, and r5py's cache and temporary directory under the
     data root. **r5py 1.1.7, JPype1 1.7.1, and psutil 7.2.2 resolve as
     wheels** on Windows and Linux for Python 3.13 (with rasterio,
     scikit-learn, geohexgrid, simplification, joblib, requests,
     filelock, configargparse; none is `GDAL` or `fiona`, so the
     dependency policy test stays green); they go in an optional
     `routing` dependency group that CI never installs, because
     **importing r5py starts the JVM** (`r5/transport_network.py` calls
     `start_jvm()` at import) and would download the jar if absent.
     psutil and pyosmium become core dependencies (the sampler; the clip).
  2. *Determinism band.* Measured pair by pair between a core run and
     its repeat on the pinned Windows environment, in integer minutes,
     with the canonicalized-value digest and the byte digest both
     recorded; **within band = every pair identical, or ≥ 99.9 % of
     pairs identical with no difference above 1 minute**; the measured
     numbers become AM-2's documented variance band; wider goes to the
     owner. Repeats: three smoke runs (EP-13), one repeat of each core
     run in the first night (EP-14); the second night's stage run is a
     cross-night repeat verified by the M5 gate.
  3. *Hand-check tolerance.* Ten OD pairs by rule, two departures
     (08:30, 17:30) on the pinned Wednesday, both modes = 40 checks
     against a public trip planner by hand (never a data source; only
     the tally and minute differences recorded); **walk within 3 min or
     15 %, walk+transit within 10 min or 25 % (the larger); gate 32 of
     40**. Reference: SEPTA's own planner for transit, a general planner
     for walking.
  4. *Run matrix.* Origins the 408 CenPop centers; destinations **all
     1,609 SNAP retailers** (the 164 supermarket-format rows are a
     subset; R5's cost is in origins and departures); runs `walk-48-wed`,
     `transit-48-wed` (core), their repeats, `walk-30-wed`,
     `transit-30-wed`, `transit-48-sat`; **the ≤ 8 h wall applies to the
     two core runs together**; the rest run the same night, timed and
     reported for M5, not judged. Block-group origins are M5's.
  5. *Extent, feeds, snapshot IDs.* The Geofabrik **dated** extract
     `pennsylvania-260831.osm.pbf` (345,912,530 B; provider MD5
     `a779d2ef14c8addce6eac207ab9cd851`; no sub-region exists), stored
     as delivered, **clipped to the county bounds + 5 km** with pyosmium
     (`osmium` 4.3.1, wheels on both platforms) into
     `intermediate/network/`; the whole-state build is the recorded
     fallback. SEPTA GTFS from the GitHub release **`v202609060`**
     (`gtfs_public.zip`, 21,555,258 B, SHA-256 `4d3fa20e…07ab`; bus/metro
     authoritative 2026-09-06 to 2027-02-20, rail to 2026-10-17), **both
     feeds**; terms page `www3.septa.org/developer/` archived and checked
     for the two "SEPTA reserves the right …" sentences; never
     republished; the CI sample for GTFS is synthetic for that reason.
     Pinned dates **Wednesday 2026-09-23, Saturday 2026-09-26**.
     **Snapshot IDs become per-source** (`SNAPSHOT_IDS`; the five keep
     `2026-09-02`).
  6. *Fixture stubs.* **Stay stubs; CI never runs the JVM.** The CI
     performance-smoke test (EP-13) measures `run --fixture` wall and
     peak process-tree RSS under the sampler; a test asserts no
     CI-imported module imports r5py.
  7. *Outputs and publication.* Run records under `<data root>/runs/
     routing/<night>/<run>/`; on go the matrix becomes
     `curated/travel_times.parquet` in the dictionary's shape through a
     registered `travel_times` stage (Bucket B by derivation); **nothing
     is published in the spike**, so the public zone stays Bucket A until
     M5.
  8. *Time box.* Three attended spike sessions = EP-13, EP-14, EP-15;
     EP-12 (the two adapters) precedes the box as ingest work; nights
     outside it; **the one extension = one further attended packet plus
     one night**; EP-15's session calls KILLED-BY-EVIDENCE or
     TIMEBOX-EXHAUSTED and the owner confirms interactively; the fallback
     packet is authored by EP-15 and follows it.
- **Gaps the pre-read found, closed:** JDK build, R5 release, and
  checksums pinned (ADR-0008); the band and the tolerance stated
  (ADR-0008, OQ-C); the two routing sources' adapters, allowlists, guard
  limits (1 GiB for the PBF, which is not an archive; 128 MiB / 1 GiB /
  ratio 50 / 50 members for the nested GTFS zip), terms sentences, data
  cards, DATA-LICENSES records, and CI samples specified (EP-12); the
  single `SNAPSHOT_ID` replaced by per-source IDs (EP-12); the fixture
  stub shapes stay the generator's by decision (question 6) and the real
  matrix shape is the dictionary's (EP-14); the CI performance-smoke
  measurement defined (EP-13); peak RSS measured first by EP-13's smoke
  route. Two gaps found here and written into the packets: r5py's
  default walking speed is 3.6 km/h and must be set on every call
  (EP-13); r5py expires its cache after two weeks, so a network rebuild
  between nights must be accounted for (EP-13, EP-14).
- **Packets authored (sequence):** EP-12 `routing-sources` (OSM +
  GTFS adapters, per-source snapshot IDs, the clipped network; no JVM)
  → EP-13 `routing-toolchain-harness` (pins installed, routing group,
  sampler, records, smoke route, CI performance smoke) → EP-14
  `routing-run-matrix` (plan file, driver, rehearsal, first night) →
  EP-15 `routing-verdict` (criteria, band, hand check, concordance,
  code, M3 closes; the fallback packet only on a kill). Sources precede
  the toolchain because the smoke route needs a real PBF and tinycity
  has none; the brief's expected shape was adjusted on that evidence.
  **Count: four S packets after the gate** (three in the attended box),
  against the milestone's "3 attended"; recorded in `milestones.md` for
  the checkpoint after EP-15.
- **Resource observations:** trivial (documentation); one session.
  Network: provider metadata only (release records, one 32-byte MD5
  file, two HTML pages). The packets carry the spike's budgets.
- **Decisions / ADRs made:** ADR-0008 (accepted, owner-reviewed).
  Routine (agent's call, logged): the four packets share one `routing`
  package namespace proposal; the plan file is tracked and tested
  against ADR-0008; the first night carries the repeats so the second
  night can be the pipeline's stage run; the GTFS CI sample is
  synthetic; the OSM CI sample is a real clip under the ODbL notice; the
  concordance engine is built in EP-15 so a kill inherits working
  fallback code; the M5 carry-in was pre-authored here rather than left
  to EP-15 alone.
- **Unresolved risks / questions:** Geofabrik's retention of dated
  daily extracts is not documented (yearly files persist; the
  `260831` file may be removed before EP-12 runs → EP-12's stop
  condition re-pins with the owner). The SEPTA download bypasses the
  page's click-through form by using SEPTA's own GitHub release; the
  agreement text is what is archived and accepted (DATA-LICENSES will
  say so). The rail feed's authoritative window ends 2026-10-17: the
  pinned dates stay valid because the feed is pinned, but a later
  refresh moves the dates (ADR-0008). Whether the clipped network's
  build fits the budget is what EP-13 measures. The third checkpoint
  falls due after EP-15 and takes the next free integer at that time
  (on a kill, the owner decides whether the fallback packet precedes
  it). For M6: the ODbL notice legal review (unchanged).
- **No-go areas touched:** none (no PHI, no secret, nothing deployed,
  nothing under a `public/` zone or `site/dist/` committed, no
  dependency, code, or data change, no source downloaded, no JDK
  installed).
- `roadmap/README.md` packet row updated to `[x] c6b5372`; the M3
  heading stays open (EP-12–EP-15 remain).
- **Exact next packet: EP-12** (`roadmap/EP-12-routing-sources.md`).

### Owner review (2026-09-03)

Twelve decisions put to the owner interactively at the end of the
session (the eight questions, with question 5 split into extent, feeds
and dates, and snapshot IDs; the decomposition with ADR-0008; commit and
push); **the recommended option was accepted for every one**:
- Q1 project-local toolchain under `phillysim/` with the pins above;
  Q2 the band; Q3 the tolerance and the forty checks; Q4 the wall on the
  two core runs with the sensitivities timed, not judged; Q5a the dated
  extract clipped to the county + 5 km; Q5b both feeds at `v202609060`
  with 2026-09-23 / 2026-09-26; Q5c per-source snapshot IDs; Q6 stubs
  stay and CI never runs the JVM; Q7 run records plus the curated
  matrix on go, nothing published; Q8 the box EP-13–EP-15 with one
  extension and EP-15 calling the code for the owner to confirm.
- **EP-12–EP-15 and ADR-0008 accepted as authored;** ADR-0008's status
  set to accepted.
- **Commit, push, CI, handoff:** yes. Work commit `c6b5372`, CI run
  33799859669 green on both platforms, then this status commit.
