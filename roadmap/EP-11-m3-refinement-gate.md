# EP-11 — M3 refinement gate: decompose the routing spike into S packets

**Status:** [ ] planned · **Milestone:** M3 · **Effort:** S (1 session, high confidence) · **Parallel with:** —

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

## Handoff payload (fill at session end)
- packet ID + status; baseline/roadmap version
- files changed; commands/tests run + results
- the carry-in check; the answers to the eight questions and the gaps
  closed; the packets authored (ID, slug, one line each, sequence)
- resource observations
- decisions/ADRs made; unresolved risks/questions
- no-go areas touched? (must be none)
- `roadmap/README.md` packet row updated to `[x] <commit>`
- exact next packet: EP-12 (the first M3 packet as authored)
