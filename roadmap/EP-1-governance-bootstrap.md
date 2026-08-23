# EP-1 — Repository governance bootstrap

**Status:** [ ] planned · **Milestone:** M0 · **Effort:** S (1 session, high confidence) · **Parallel with:** —

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
- [ ] Every file passes a read-through against charter.md + governance.md.
- [ ] Repo description updated (or owner action recorded in handoff).
- [ ] `git status` clean at session end.
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

## Handoff payload (fill at session end)
- packet ID + status; baseline/roadmap version
- files changed; commands/tests run + results
- resource observations
- decisions/ADRs made; unresolved risks/questions
- no-go areas touched? (must be none)
- exact next packet: EP-2
