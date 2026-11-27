---
ep: 16a
title: Dependency triage with the owner (certifi first), the lock checked, the pins noted
size: M
model: claude-opus-5-5
effort: max
status: done
---

# EP-16a — Dependency triage with the owner (certifi first), the lock checked, the pins noted

**Milestone:** — (checkpoint 3, after M3, before the M4 refinement gate) · **Size:** M · **Depends on:** EP-15 (M3 done) · **Parallel with:** — · **Split from:** EP-16 (2026-11-26, at pickup; the first of six parts, EP-16a to EP-16f)

## Outcome & value
The first part of the third checkpoint ([EP-16](EP-16-checkpoint-3.md),
its item 5), put first by the owner at the sweep's push (2026-11-25) so
that the fresh-clone re-run ([EP-16b](EP-16b-fresh-clone-rerun.md)) tests
the lock this part leaves. GitHub reported 42 open Dependabot alerts on
`main` and 11 open Dependabot pull requests. After this packet each has the
owner's decision (upgrade, defer, close or dismiss), the approved upgrades
are in `phillysim/uv.lock` (and in the CI workflow where an action moves)
with the suite green, `uv lock --check` is clean, and the pins the
checkpoint watches (the vendored MapLibre GL JS, the SHA-pinned actions,
the routing group's wheels, the JDK and the R5 jar) are recorded as current
or behind. A security alert is surfaced and decided, never deferred
silently.

## Scope
- in:
  1. List the open alerts (`gh api repos/{owner}/{repo}/dependabot/alerts`)
     and pull requests (`gh pr list`), grouped by package, with severity,
     fixed version, manifest and role in the tree (`uv tree --invert`):
     core runtime, the `routing` group, the `dev` group, CI, or the vendored
     `source material/` copy.
  2. Put each package's decision to the owner, one question each, certifi
     (critical) first, the recommended option first, every option grounded
     in checked facts.
  3. Apply what the owner approves: `uv lock --upgrade-package …` in
     `phillysim/`, an action's SHA in `.github/workflows/ci.yml`, and on
     GitHub only what the owner names (closing a pull request, dismissing an
     alert).
  4. Check: `uv lock --check`; `uv sync --locked` with the routing group;
     `ruff check` and `ruff format --check`; the full suite; `pre-commit run
     --all-files`; `phillysim route smoke` if a package r5py imports moves.
  5. Note the pins (MapLibre GL JS, the actions, the routing group's five
     wheels, the JDK, the jar) as current or behind, upgrading none of them.
  6. One documentation correction found at pickup: `.github/dependabot.yml`
     says `open-pull-requests-limit: 0` stops security-update pull requests
     against the vendored tree; GitHub's documentation says the key limits
     version-update pull requests only (security updates have their own
     fixed limit of ten), which is why PRs #5 and #16 exist.
- out (explicit non-scope): any upgrade the owner has not approved; the
  routing pins (r5py, JPype1, psutil, osmnx, scipy), the JDK and the jar (an
  upgrade of r5py, R5 or the JDK re-measures the determinism band by the
  OQ-C procedure, ADR-0008); the vendored MapLibre; the fresh-clone re-run
  and everything after it (EP-16b to EP-16f); pushing (the owner's).

## Prerequisites & locked decisions
- prerequisites: EP-15 (M3 closed on a go verdict).
- locked decisions honored: ADR-0001 / ADR-0002 (the stack; the GDAL and
  fiona ban that `tests/test_dependency_policy.py` enforces); ADR-0008 (the
  routing group's exact pins and layout; CI never installs it);
  CONTRIBUTING.md (the `source material/` tree is never built, executed or
  modified); governance.md "Maintenance" (uv lock and Dependabot); every
  upgrade waits for the owner's word (the sweep's push, 2026-11-25).
- dependencies: the `gh` CLI (read-only listing; GitHub writes only on the
  owner's word); PyPI for the resolver; the working clone's data root for
  the smoke route.

## Safety preconditions
Standing policy (see EP-1). Packet-specific: no upgrade without the owner's
word; nothing pushed (the push is the owner's, an owner task gated before
EP-16b); GitHub writes (closing a pull request, dismissing an alert) only as
the owner names them, with a short factual comment; the vendored `source
material/` tree is not modified; no machine identifier or absolute path in a
tracked file (the diff scanned); the real data root is read, never reset
(the smoke route writes only its own run directory).

## Likely components & contracts (proposed)
`phillysim/uv.lock` (the approved upgrades); `.github/workflows/ci.yml` (an
action's SHA, if approved); `.github/dependabot.yml` (the comment);
`CHANGELOG.md` (under Unreleased); this brief; `roadmap/README.md` (the
split's rows and notes, this row closed); `roadmap/owner-tasks.md` (the
push); `roadmap/inbox.md` (IN-3's disposition). No code.

## Implementation notes
Facts checked at pickup. The acquisition path (`phillysim.download`) uses
the standard library's `urllib.request`, so the system trust store, not
certifi. certifi and urllib3 reach the tree through `requests` (osmium in
core; osmnx and r5py in the routing group) and through pyogrio, pyproj and
rasterio. virtualenv comes in only through pre-commit (dev); filelock
through virtualenv and r5py, whose `util/working_copy.py` takes a
`filelock.FileLock` around its cached copy of the network inputs; filelock
4.0.0's one breaking change is `SoftReadWriteLock`'s on-disk protocol, which
r5py does not use. The runtime version updates (geopandas, pyproj, duckdb)
compute the curated and public tables whose digests EP-16b compares with the
references, so an upgrade before the re-run would make a digest change
ambiguous. No test compares screenshots, and CI's browser tests drive the
runner's preinstalled browser. Upgrading in the local lock rather than
merging on GitHub keeps `main` linear until the owner pushes; Dependabot
usually closes a pull request whose update is already on `main` (not
confirmed in the documentation read at pickup), and any it leaves is closed
by hand.

## Acceptance criteria & evidence
- [x] Every open alert and Dependabot pull request listed with the owner's
      decision and its outcome.
- [x] The approved upgrades in the lock; `uv lock --check` clean; ruff, the
      full suite and pre-commit green.
- [x] The pins noted as current or behind.
- [x] The `dependabot.yml` comment corrected.
- Evidence: the handoff payload; the commit; CI on it after the owner's push
  (read by EP-16b).

## Tests / validation
`uv lock --check`; `uv sync --locked --group routing`; `uv run ruff check .`;
`uv run ruff format --check .`; `uv run pytest`; `uv run --project phillysim
pre-commit run --all-files`; `uv run phillysim route smoke` if filelock
moves.

## Resource budget
Attended: one M session. Network: the GitHub API and PyPI. The smoke route:
about a minute and a few GB of RAM.

## Risks, rollback, stop condition
An upgrade breaks a test → that upgrade is reverted in the lock and
recorded as deferred with the reason, never worked around in code here. A
security alert with no fixed version, or a fix the resolver cannot reach →
surfaced to the owner and recorded, never deferred silently. Rollback:
revert the commit (lock and documentation only). Stop: an upgrade that would
move the routing pins, the JDK or the jar.

## Documentation / ADR updates
`CHANGELOG.md` (Unreleased: the upgrades and the comment); the README's
Checkpoints table (the six rows, this one closed) and brief notes; this
brief's payload and completion note. No ADR (no ADR's pin moves).

## Handoff payload (filled 2026-11-26)
- **Packet:** EP-16a, done; its commit is recorded in the README row by the
  commit that follows it. Planning Baseline v1.0. No code changed.
- **The split, before any work.** EP-16, "S (1 session)" with seven scope
  items, was split at this pickup (D-2; its brief note's segment "From
  IN-1"; the cut the session's call) into six M parts along its own items:
  EP-16a the dependency triage (first, the owner's choice at the sweep's
  push), EP-16b the fresh-clone re-run with the resource use it measures
  (items 1 and 4), EP-16c the license sweep with the data-facing documents
  (item 3, item 2's data half), EP-16d the rest of the documentation sync,
  EP-16e the estimate review with v1 counted in briefs (item 6, IN-2,
  IN-3), EP-16f the M4 pre-read and EP-17 (item 7), the last carrying the
  set's acceptance evidence. Each part is a complete packet from the
  template with front matter; the planned ones carry no completion note,
  since Roadmap Wrangler reads any brief that has one as complete (checked
  in its parser, `brief.rs`). The parent file names the set; the README's
  EP-16 row became six rows and its brief note moved to the parts. `crw
  roadmap` afterwards: house profile, 24 rows, 18 done, next EP-16a (M), 27
  briefs (18 complete), no problems.
- **Inbox.** IN-3 (the portfolio card's floor of 57) parked, as the owner
  confirmed, in EP-16e's brief note; not under 57 (the tables now hold 24
  rows, 62 by IN-3's own sum), so nothing was said to prime at once.
- **What was open on GitHub (read 2026-11-26 with `gh`).** 42 alerts and 11
  Dependabot pull requests:

  | Package | Where | Alerts | Pull request | Role in the tree |
  |---|---|---|---|---|
  | certifi | `phillysim/uv.lock` | 1 critical | #14 → 2026.10.18 | through requests (osmium core; osmnx, r5py routing), pyogrio, pyproj, rasterio |
  | urllib3 | `phillysim/uv.lock` | 2 high, 1 medium | none | through requests only |
  | virtualenv | `phillysim/uv.lock` | 10 high, 6 medium, 3 low | #12 → 21.14.13 | dev only, through pre-commit |
  | filelock | `phillysim/uv.lock` | 1 high, 9 medium, 2 low | #13 → 4.2.1 (major) | through virtualenv (dev) and r5py (routing) |
  | addressable | `source material/…/Gemfile.lock` | 5 medium, 1 low | #16 | vendored, never built or run |
  | baseline-browser-mapping | `source material/…/package-lock.json` | 1 medium | #5 | vendored, never built or run |
  | geopandas, pyproj, duckdb | `phillysim/uv.lock` | — | #6, #7, #8 (version updates) | core runtime: compute the curated and public tables |
  | playwright, ruff | `phillysim/uv.lock` | — | #10, #11 (version updates) | dev |
  | astral-sh/setup-uv | `ci.yml` | — | #15 (version update) | CI, SHA-pinned |

- **Owner decisions (2026-11-26, through `AskUserQuestion`, one per
  package; every answer the recommended option) and their outcomes.**
  1. *certifi:* upgrade in the lock now → 2026.7.22 → **2026.11.20**
     (latest; the fix is 2026.10.18). Applied.
  2. *urllib3:* upgrade now → 2.7.0 → **2.8.0**. Applied.
  3. *virtualenv:* the latest now → 21.7.8 → **21.15.13**, with
     python-discovery 1.6.0 → 1.9.7. Applied.
  4. *filelock:* 4.3.1, smoke-tested → 3.32.5 → **4.3.1**. Applied; the smoke
     route completed and its result equals EP-13's (below).
  5. *The vendored tree:* close the pull requests and dismiss the alerts →
     #5 and #16 closed with a one-line comment (2026-11-27T04:10Z); alerts
     9 and 45 to 50 dismissed as "not used" with a comment; the
     `dependabot.yml` comment corrected (as EP-10 had dismissed the earlier
     vendored-tree alerts).
  6. *geopandas, pyproj, duckdb (#6 to #8):* deferred to EP-17, after the
     re-run → the pull requests stay open; EP-16f's brief note carries them
     into EP-17's inputs as a deliberate upgrade with the references
     re-recorded.
  7. *playwright, ruff, setup-uv (#10, #11, #15):* the pull requests'
     versions now → playwright **1.63.0**, ruff **0.16.9**, `setup-uv`
     **v10.3.3** at `68559e99cc807c1eb7e9238fd43a15bba460eec2` (checked: the
     `v10.3.3` tag points at that commit). Applied.
  8. *IN-3:* park it in EP-16e's note → done (above).
  The commits are under the autopilot (the owner's standing yes, crw D-22);
  the push is the owner's (OT-1, before EP-16b).
- **Files changed.** `phillysim/uv.lock` (seven packages);
  `.github/workflows/ci.yml` (the `setup-uv` SHA); `.github/dependabot.yml`
  (the comment); `CHANGELOG.md` (Unreleased: Security, and the split under
  Changed); `roadmap/_TEMPLATE.md` (one guard sentence: the completion note
  only at the close); `roadmap/EP-16-checkpoint-3.md` (now the set's name);
  new `roadmap/EP-16a-dependency-triage.md` to `EP-16f-m4-gate-preread.md`;
  `roadmap/README.md` (the six rows, the set's note and the parts' bullets,
  the references to EP-16); `roadmap/inbox.md` (IN-3);
  `roadmap/owner-tasks.md` (OT-1).
- **Commands and results.** `uv lock --check` clean before and after; `uv
  lock --upgrade-package certifi … --upgrade-package "ruff==0.16.9"
  --upgrade-package "playwright==1.63.0"`: exactly the seven moves above;
  `uv sync --locked --group routing`; `ruff check .` clean, `ruff format
  --check .` 98 files formatted; `pytest` with the routing group **664
  passed, 3 skipped** in 207 s (the skips: the three manual
  `--real-data-root` tests; the OSMnx concordance and the browser tests
  ran); `pre-commit run --all-files` green, its hook environment built
  afresh by virtualenv 21.15.13 (a scratch `PRE_COMMIT_HOME`, so the
  owner's cache was not touched); `phillysim route smoke --repeats 1`
  completed: wall 60.0 s, peak RSS 4.08 GB, value digest `cab6893edad3…`,
  **equal to EP-13's three smoke runs of 2026-09-03**, so the routing result
  is unchanged under the new lock; after the dismissals, 35 open alerts, all
  on `phillysim/uv.lock` and all fixed by the local lock once pushed.
- **The pins (the parent's item 5), none upgraded.**

  | Pin | Here | Upstream (2026-11-26) | Reading |
  |---|---|---|---|
  | MapLibre GL JS (vendored) | 6.7.0 | 6.19.0 | behind |
  | `actions/checkout` | v7.0.1 | v7.0.1 | current |
  | `astral-sh/setup-uv` | v10.3.3 (this packet) | v10.4.0 | one minor behind |
  | `pre-commit/pre-commit-hooks` | v6.0.0 | v6.0.0 | current |
  | r5py, jpype1, psutil, scipy | 1.1.7, 1.7.1, 7.2.2, 1.18.1 | the same | current |
  | osmnx | 2.1.1 | 2.2.0 | behind |
  | Temurin JDK 21 | 21.0.12.1+1 | 21.0.13.1+2 | one update behind |
  | R5 jar | v7.5.1-r5py | v7.5.2-r5py, v7.6-r5py | behind (ADR-0008 chose v7.5.1 over v7.6) |

  An upgrade of r5py, R5 or the JDK re-measures the determinism band by the
  OQ-C procedure at the checkpoint that follows it (ADR-0008).
- **Resource observations.** The suite 207 s with the routing group; the
  smoke route 60 s and 4.08 GB; the lock resolved in under a second.
- **Unresolved risks / questions.** (1) That Dependabot closes the six pull
  requests the local lock supersedes (#10 to #15) once the push lands is its
  usual behaviour but was not confirmed in the documentation read; EP-16b
  checks, with the 35 alerts' state (its brief note). (2) No setting stops
  security-update pull requests or alerts for the vendored tree (GitHub's
  documentation; whether `ignore` reaches security updates it did not
  settle), so each new advisory there is closed and dismissed by hand, as
  `dependabot.yml` now says. (3) The deferred runtime updates and the pins
  behind wait for their gates: EP-17 for the former, the next checkpoint's
  triage for the latter.
- **No-go areas touched:** none. No code; no upgrade without the owner's
  word; the vendored tree unmodified; nothing pushed; the real data root
  read only, except the smoke route's own run directory
  (`runs/routing/20261127T041523Z-smoke/`); no machine identifier or
  absolute path in a tracked file (the diff scanned).
- **`roadmap/README.md`:** the EP-16a row `☑` with its commit (by the commit
  that follows); EP-16b to EP-16f `☐`.
- **Exact next packet: EP-16b**, the fresh-clone re-run, once the owner has
  pushed `main` (OT-1).

> **Completion note (2026-11-26; claude-opus-5-5/max; ≈ 45 min to the
> commit).** EP-16 was split at its pickup into six M parts along its own
> items, the dependency triage first. Then the 42 open Dependabot alerts
> and 11 pull requests were triaged with the owner. Owner decisions, each
> the recommended option: certifi (the critical alert), urllib3, virtualenv
> and filelock upgraded in the lock to their latest releases, filelock
> smoke-tested (the route's result equals EP-13's); the vendored tree's two
> pull requests closed and its seven alerts dismissed as not used, the
> `dependabot.yml` comment corrected; geopandas, pyproj and duckdb deferred
> to EP-17, after the re-run has confirmed the reference digests; ruff,
> playwright and `setup-uv` taken at the pull requests' versions; inbox
> IN-3 parked in EP-16e's note. Commit under the autopilot; the push is the
> owner's (OT-1, before EP-16b). Routine choices: the six-way cut; a scratch
> `PRE_COMMIT_HOME` so the new virtualenv built the hook environment; one
> guard sentence in `_TEMPLATE.md`. The effort is the launch's suggestion;
> the panel's setting is not visible to the session. The handoff payload
> above is the detailed record.

> **Handed on (to clauderoadmapwrangler).** From phillysim EP-16a
> (2026-11-26), read in the parser's code rather than seen in a run: a brief
> that carries the house template's closing placeholder, `> **Completion
> note (YYYY-MM-DD; model/effort; duration).**`, counts as complete
> (`brief.rs`: `kind_of` takes any "Completion note" label, dated or not,
> and `completion()` returns the first). A session that copies the template
> whole at its start, or a gate that authors planned briefs from it, would
> see them read as complete. phillysim's `_TEMPLATE.md` now says to write the
> note only at the close. The parser could skip a note whose label still
> reads `YYYY-MM-DD`, or the house template could give the placeholder as an
> instruction rather than as a blockquote.
