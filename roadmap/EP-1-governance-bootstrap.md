# EP-1 — Repository governance bootstrap

**Status:** [x] 102af00 · **Milestone:** M0 · **Effort:** S (1 session, high confidence) · **Parallel with:** —

## Outcome & value
The public repo is honest and governed at every commit: reframed README
("measuring access, not modeling outcomes"; the "sim" definition; AI
disclosure; non-endorsement), GitHub repo description updated to match,
comprehensive .gitignore, DATA-LICENSES stub with the City-license caveat and
license-bucket rules, CLAIMS.md instantiated from the charter's claims rows,
and CONTRIBUTING / SECURITY / correction-and-delisting policy stubs.

## Scope
- in: the documents above; .gitignore; repo-description wording.
- out (explicit non-scope): any Python code; CI (EP-2).

## Prerequisites & locked decisions
- prerequisites: none — first packet.
- locked decisions honored: charter.md claims rows; AM-1/AM-4 vocabulary
  (format-based store categories, license buckets); governance.md delisting
  policy; ADR-0003.
- dependencies: none.

## Safety preconditions
Standing policy: no source datasets committed; no machine identifiers or
absolute local paths in tracked files; license buckets respected; no outbound
calls beyond the documented allowlist. Packet-specific: claims wording must
match charter.md exactly; no affiliation implications; vendored
`source material/` untouched.

## Likely components & contracts (proposed)
README.md rewrite; .gitignore; docs/CLAIMS.md; docs/DATA-LICENSES.md;
CONTRIBUTING.md; SECURITY.md; docs/policies.md (correction + delisting).

## Implementation notes
.gitignore must cover: data/ zones, secrets/.env, caches, logs, notebook
outputs, local databases. Repo-description update is a GitHub-settings owner
action — note it in the handoff if not performed in-session.

## Acceptance criteria & evidence
- [x] Every file passes a read-through against charter.md + governance.md.
- [x] Repo description updated (or owner action recorded in handoff). — owner
      action recorded below (no `gh` CLI in-session).
- [x] `git status` clean at session end.
- Evidence: review checklist recorded in handoff; changelog started.

## Tests / validation
Manual review checklist; markdown lint if trivially available.

## Resource budget
Trivial.

## Risks, rollback, stop condition
Wording drifts from the claims matrix → stop, reconcile charter.md first.
Rollback: git revert; no state outside git.

## Documentation / ADR updates
This packet IS documentation; CHANGELOG.md started.

## Handoff payload (filled 2026-08-23)
- **Packet:** EP-1 — done at commit `102af00` (+ this status commit).
  Planning Baseline v1.0.
- **Files changed:** README.md (rewritten to charter framing), .gitignore
  (new), docs/CLAIMS.md, docs/DATA-LICENSES.md, docs/policies.md,
  CONTRIBUTING.md, SECURITY.md, CHANGELOG.md (all new).
- **Commands/tests run:** read-through of every file against charter.md +
  governance.md; scripted verbatim check that all six CLAIMS.md anchor rows
  match charter.md exactly (all pass; whitespace-normalized). Markdown lint
  not run — no linter installed and installing one is out of packet scope.
  `git status` clean at session end.
- **Resource observations:** trivial, as budgeted. Single session.
- **Decisions made (revisable, below ADR level):**
  - Delisting rebuild window stated as **7 days** in docs/policies.md
    (governance.md required "a stated window" but fixed none).
  - Public contact email deliberately **not** published yet; GitHub Issues is
    the interim channel, email to be designated at first public release.
  - SECURITY.md routes reports via GitHub private vulnerability reporting.
- **Owner actions (not performable in-session):**
  1. Update the GitHub repo description (Settings → About). Suggested text:
     "Measuring access to health-relevant community resources across
     Philadelphia — a descriptive civic-data atlas. Measures access; does not
     model outcomes." (`gh` CLI not installed locally.)
  2. Enable secret scanning + push protection and private vulnerability
     reporting in repo settings (SECURITY.md and governance.md assume both).
  3. Send the opendata@phila.gov license-confirmation draft (already in Gmail
     drafts, from the planning engagement).
  4. Push when desired — commits are local only.
- **Unresolved risks/questions:** City-license caveat stands (documented in
  docs/DATA-LICENSES.md) pending the City's reply; the 7-day delisting window
  should be confirmed or adjusted by the owner.
- **No-go areas touched:** none — no source data, no code, `source material/`
  untouched, no machine identifiers or absolute paths in tracked files, no
  outbound calls.
- **Exact next packet:** EP-2 (scaffold + CI).
