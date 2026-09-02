# Correction and delisting policies

These policies apply to all published project content: the repository, the
public data files, and the site (once it exists). They implement the
community-safety commitments in
[roadmap/governance.md](../roadmap/governance.md).

## Correction / feedback channel

- **How to reach the project:** open a GitHub Issue on this repository. A
  dedicated data-correction issue template will be added before any public
  data ships; until then, a plain issue is fine. A public contact email will
  be designated alongside the first public release.
- **What happens:** best-effort triage by the maintainer; there is no SLA.
  This is a solo public-interest project.
- **Versioning consequence:** corrections affecting published aggregates bump
  the data snapshot or metric version — never a silent edit — and are
  recorded in the changelog.

## Delisting / takedown policy

Any listed site or organization may request removal of its listing via the
correction channel above.

- **Response:** an expedited rebuild of the site and the public data files
  with the listing removed, targeted **within 7 days** of receiving the
  request, plus a changelog note recording the removal.
- **Safety-motivated requests** (e.g., a site whose exposure creates risk)
  are targeted **within 72 hours** and additionally trigger retraction and
  re-issue of the affected release artifacts. Raw snapshots are retained
  privately for reproducibility but are no longer republished.
- These windows are stated targets for a solo-maintained project, not a
  service guarantee; the maintainer monitors the correction channel on a
  best-effort basis and records every removal in the changelog.
- No justification is demanded for a delisting request from a listed
  organization; the default is removal.

## Data-provider takedown

If a data originator (e.g., the City of Philadelphia) objects to this
project's reuse of its data, the affected layers are removed on the same
expedited path, the source row in
[DATA-LICENSES.md](DATA-LICENSES.md) is updated, and the change is recorded
in the changelog. See the City-license caveat in that document.

## Scope notes

- The project publishes aggregate and facility-level public data only; there
  is no personal-data subject here in the GDPR/CCPA sense, and no accounts,
  analytics, or user data exist to delete.
- Volunteering or advocacy interest prompted by the project is routed to
  established organizations' own channels (link-outs); the project never
  directs outreach at households.
