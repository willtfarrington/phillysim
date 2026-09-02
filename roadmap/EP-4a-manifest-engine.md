# EP-4a — Manifest/snapshot engine + zones + download guards

**Status:** [~] in progress (work complete; awaiting owner review) · **Milestone:** M1 · **Effort:** S (1 session, medium confidence) · **Parallel with:** — · **Split from:** EP-4 (2026-09-02; EP-4b is the other half)

## Outcome & value
The data half of the pipeline backbone: snapshot IDs and the immutable
raw→intermediate→curated→public zone layout under `data/` (plus quarantine
and cache), checksummed manifests carrying the ADR-0006 version-axis fields
(acquisition URL + dual-URL field, terms-archive pointer, schema version,
license bucket, per-file SHA-256), a quarantine path for validation
failures, and download guards (size caps, zip-slip, decompression-bomb,
domain allowlist) — proven against the tinycity raw snapshots. EP-4b builds
the stage runner on top of this.

## Scope
- in: zone layout + snapshot IDs; manifest model, writer, reader, and
  checksum verification; quarantine-on-failure; download/extraction guards
  with negative tests; `phillysim verify --fixture` at the snapshot level
  (every raw snapshot matches its manifest); promotion of the tinycity
  manifest shape from "proposed" to owned (regenerate the fixture if the
  shape changes).
- out (explicit non-scope): stages, fingerprints, resume/cancel, preflight,
  `phillysim run/status` (EP-4b); real adapters (EP-5/6); drift detection
  beyond schema-hash comparison.

## Prerequisites & locked decisions
- prerequisites: EP-3.
- locked decisions honored: architecture.md zones & identifiers; ADR-0006
  version-axis fields in manifests; ADR-0002 storage; ADR-0003 license
  bucket recorded per snapshot; EP-2's data-root resolution (resolution
  never creates directories).
- dependencies: none external.

## Safety preconditions
Standing policy (see EP-1). Packet-specific: quarantine-on-failure is
default-deny; `data/` gitignored; manifests contain no machine identifiers
or absolute paths; guards are tested against crafted malicious inputs, never
against real downloads (no network in this packet).

## Likely components & contracts (proposed)
`src/phillysim/{zones,manifest,guards}.py`; `phillysim verify --fixture`
(snapshot-level; EP-4b extends it with stage state); tests
`tests/test_zones.py`, `tests/test_manifest.py`, `tests/test_guards.py`.
Input contract: the tinycity `raw/<source>/<snapshot-id>/manifest.json`
shape in `docs/data-dictionary.md` (schema version 1). Output contract: a
manifest the reader round-trips byte-for-byte and `verify` accepts.

## Implementation notes
Snapshot ID = date-stamped per-source identifier (architecture.md); the
manifest is the only place version-axis fields are recorded. Quarantine
moves the offending snapshot directory whole and writes a reason file next
to it; nothing in quarantine is ever read by a later stage. Guards operate
on local file objects so they are testable offline: size cap before and
during extraction, path normalization against the target root (zip-slip),
compression-ratio ceiling (bomb), and an allowlist check on the acquisition
URL host. Keep the module free of adapter knowledge.

## Acceptance criteria & evidence
- [x] All eight tinycity raw snapshots verify against their manifests; a
      tampered byte in one data file makes `verify` fail naming the file. —
      `test_all_eight_fixture_snapshots_verify` and
      `test_cli_verify_fixture_is_green` (8 of 8); a flipped bit in `acs.csv`
      fails with a `digest` problem naming the file
      (`test_tampered_byte_fails_naming_the_file`) and the CLI exits 1 with
      `FAIL osm_network/2026-01-01` + the file name
      (`test_cli_verify_raw_names_the_tampered_file`). Missing, unlisted,
      relocated, and stray entries are each covered too.
- [x] Injected oversized, zip-slip, decompression-bomb, and off-allowlist
      inputs are each refused and quarantined (negative tests, one per
      guard). — `tests/test_guards.py`: `test_oversized_input_…`,
      `test_zip_slip_input_…`, `test_decompression_bomb_…`,
      `test_off_allowlist_input_…` each stage a crafted snapshot, call
      `admit`, and require the snapshot gone from `raw/`, present under
      `quarantine/<source>/`, and a reason file naming the guard and the
      offending file/member/host. Each guard is also unit-tested in
      isolation (nine zip-slip member forms, ratio / declared-size /
      member-count bombs, symlink members, streaming caps, gzip).
- [x] Manifest round-trip is byte-identical; missing or malformed
      version-axis fields are rejected. —
      `test_fixture_manifest_round_trips_byte_for_byte` (all eight),
      `test_write_then_read_is_identity`; `test_every_field_is_required`
      (each of the eleven fields) and `test_malformed_fields_are_rejected`
      (twenty-three malformed forms incl. bucket `Z`, string / zero / boolean
      schema versions, non-UTC timestamps, `file:` and credentialed URLs,
      path-bearing file names, short digests, an unlisted terms archive);
      unknown fields rejected too.
- Evidence: `uv run pytest` → 207 passed locally (76 before the packet);
  CI run recorded in the handoff once pushed; data dictionary manifest
  section now "Owned by the manifest engine".

## Tests / validation
`uv run pytest`; guard negative tests; fixture regeneration if the manifest
shape changed (`phillysim gen-tinycity --out …` for both variants, then
`test_committed_fixture_matches_regeneration`).

## Resource budget
Trivial at fixture scale.

## Risks, rollback, stop condition
Manifest-shape churn → hold to the data-dictionary shape plus ADR-0006
fields; anything else belongs to EP-4b or later. Stop if the guards need
network access to test — they must not.

## Documentation / ADR updates
`docs/data-dictionary.md` manifest section (proposed → owned; schema
version unchanged unless a field is added, then bump with a migration note);
package README layout list; packet row in `roadmap/README.md`.

## Handoff payload (filled 2026-09-02)
- **Packet:** EP-4a — work complete; status and commit recorded on the
  owner's decision (see "Owner decisions"). Planning Baseline v1.0.
- **Files changed:** new `phillysim/src/phillysim/{zones,manifest,guards,quarantine}.py`;
  `phillysim/src/phillysim/cli.py` (`verify` command; module docstring);
  `phillysim/src/phillysim/fixtures/tinycity.py` (manifests built through
  `phillysim.manifest.Manifest`; JSON serialization shared with the engine's
  `canonical_bytes`); new `phillysim/tests/{test_zones,test_manifest,test_guards}.py`;
  `docs/data-dictionary.md` (manifest section proposed → owned with field
  rules; new quarantine reason-file section); `phillysim/README.md` (layout
  list; "Raw snapshots, manifests, and guards" section);
  `phillysim/tests/fixtures/tinycity/README.md` (one line); `CHANGELOG.md`;
  `roadmap/README.md` packet row; this file. No fixture file changed.
- **Commands/tests run + results:** `uv run pytest` → 207 passed (131 new);
  `uv run ruff check .` and `ruff format --check .` clean; both fixture
  variants regenerated with `phillysim gen-tinycity` → `git status` shows
  no fixture change (shape promoted without a byte moving; schema version
  stays 1); `phillysim verify --fixture` → 8 of 8, exit 0; `phillysim
  verify` with no raw zone → "nothing to verify", exit 1, data root not
  created; `pre-commit run --all-files` with the new files staged → all
  hooks passed; scan of the new files for usernames / absolute paths →
  none.
- **Resource observations:** trivial, as budgeted; single session. The
  bomb tests build a 512 KB zero payload in memory and the gzip cap test
  2 MB; the whole suite runs in about three seconds.
- **Decisions made (revisable, below ADR level):**
  - Snapshot ID grammar: `YYYY-MM-DD`, with `-N` (N = 1, 2, …, no zero
    padding) for a further acquisition of the same source on the same day;
    `next_snapshot_id` never reuses an existing directory (raw zone
    immutable). Source identifiers are lowercase slugs. Both are validated
    wherever a directory name is built, so no name can carry a path.
  - Manifest validation is strict: every field required, unknown fields
    rejected (so a hostname or absolute path cannot be smuggled in), file
    names must be bare names, URLs must be http(s) with a host and no
    credentials, timestamps must carry a UTC designator. Validation lives in
    `Manifest.from_dict` / `validate`; the fixture generator constructs
    through the model so any future shape change surfaces in the golden
    test.
  - Admission is one function, `quarantine.admit`, ordered manifest →
    guards → checksums, and is the only intended way into `raw/`. Repeat
    quarantines of the same snapshot ID get `-q2`, `-q3`, … names; the
    reason file is canonical JSON with no absolute path.
  - Allowlist semantics: https only, exact host or subdomain of a listed
    domain, no IP literals, no credentials; both the acquisition URL and the
    alternate URL are checked. There is deliberately no default allowlist —
    EP-5 declares the first real domains in its adapters; the module has no
    adapter knowledge.
  - Default `Limits` (4 GB per file, 16 GB extracted, 200:1 ratio, 10 000
    members) are placeholders sized around a regional OSM extract; every
    caller passes its own limits and the tests use small ones. To be
    confirmed per source in EP-5/EP-6.
  - Symlinks are refused both as zip members and as entries in a staged
    snapshot. Guarded gzip extraction is included alongside zip because it
    was cheap and some Census/USDA files ship gzipped.
  - `phillysim verify --fixture` verifies a *fresh* tinycity generation in a
    temporary directory (the committed copy is verified by the test suite);
    `--raw DIR` verifies any raw zone; bare `verify` uses the resolved data
    root and never creates it. EP-4b re-targets `--fixture` at the fixture
    data root and adds stage-state coherence.
  - Stray-entry listing sorts by name bytes, not by `Path`, so the report
    is identical on Windows and Linux.
- **Owner decisions taken interactively (2026-09-02):** commit and push
  (yes — work commit, then this status commit, CI run recorded above);
  keep `phillysim verify --fixture` as built, verifying a fresh generation,
  with EP-4b re-targeting it at the fixture data root (yes); keep the
  default guard limits as documented placeholders to be confirmed per
  source in EP-5/EP-6 rather than removing or tightening them now (yes).
- **Unresolved risks/questions:** default guard limits unconfirmed until a
  real adapter exists; the streaming size cap is a primitive
  (`copy_capped`) with no HTTP client behind it yet (EP-5 wires it into
  the download path, allowlist check first); no immutability enforcement on
  the file system (read-only bits) — immutability is by policy plus
  `verify`, and EP-4b's runner may add a seal step if it proves useful.
- **No-go areas touched:** none — no network calls (guards tested on
  crafted local inputs only), no real data, `source material/` untouched,
  no machine identifiers or absolute paths in tracked files (scanned;
  manifest validation now rejects them structurally), `data/` still
  gitignored.
- **`roadmap/README.md` packet row:** set to `[~]` with the work; becomes
  `[x] <commit>` in the handoff commit.
- **Exact next packet:** EP-4b (stage runner: fingerprints, resume/cancel,
  preflight, `run/status/verify --fixture`; M1 go/no-go).
