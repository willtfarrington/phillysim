# Security policy

## Reporting a vulnerability

Please report suspected vulnerabilities privately via **GitHub's private
vulnerability reporting** on this repository (Security tab → "Report a
vulnerability"). Please do not open a public issue for a security report.

This is a solo-maintained project: reports are handled best-effort, with
acknowledgment targeted within 7 days. There is no bug bounty.

## Scope

The project is a local data pipeline plus a static site — there is no server,
no accounts, and no user data. Reports most likely to matter:

- Untrusted-input handling in the pipeline (malicious or malformed downloads:
  archive extraction, decompression bombs, schema/content validation
  bypasses).
- CSV formula injection via source-derived names in exports.
- Output escaping in site popups/panels (XSS via source-derived text).
- Supply-chain issues in pinned dependencies, the pinned JDK/R5 jar, or CI
  actions.
- Any credential, token, or private data accidentally committed to the
  repository.

Out of scope: server-side classes of issues (auth, multi-tenancy, SSRF beyond
the documented outbound allowlist) — no server exists. The threat model is
documented in [roadmap/architecture.md](roadmap/architecture.md) (Security).

## If a secret or private datum is committed

Per [roadmap/governance.md](roadmap/governance.md): rotate/revoke the
credential, purge history, and document the incident; prevention is secret
scanning plus push protection on the repository.
