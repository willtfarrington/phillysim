# EP-8 — Minimal slice page

**Status:** split 2026-09-02 into [EP-8a](EP-8a-slice-page.md) and [EP-8b](EP-8b-basemap-roads.md) · **Milestone:** M2 · **Effort:** M (1–2 sessions, medium confidence), as authored · **Parallel with:** —

> **This file names the set, not a packet.** The pickup pre-read on
> 2026-09-02 (README "Packet sizing and splitting") found that this brief
> holds two first-time subsystems: the static page itself, with its build
> step, dev server, vendored map library, and a browser test harness
> (Playwright + axe) that CI had never run; and a new raw source, the TIGER
> roads the basemap's "major roads" need, which means an adapter, a terms
> archive, contract tests, CI samples, a data card, and a public-zone layer
> (the same shape of work EP-5a and EP-6 each filled a session with). It was
> split at that boundary: **EP-8a** builds the page, the table, the
> county-boundary basemap, the vintage and attribution blocks, and the
> Playwright + axe check in CI; **EP-8b** adds the TIGER major-roads layer
> to the basemap, meets the contrast spec against it, and carries this set's
> milestone-level evidence (M2 closes with it). References to "EP-8"
> elsewhere mean both parts; the text below is the brief as authored on
> 2026-08-23.

## Outcome & value
A minimal static page (MapLibre + vanilla JS/TS — no framework creep)
rendering the public slice GeoJSON over the public-domain minimal basemap
(first cut: county boundary + major roads from TIGER, meeting the contrast
spec), with an HTML table of the same data, a vintage line, and an
attribution block — served by a local dev server. Deployed to Pages only if
the owner opts to show work-in-progress (default: **not deployed**; see
open-questions OQ-H).

## Scope
- in: page, table, basemap first cut, vintage/attribution, Playwright + axe
  smoke.
- out (explicit non-scope): the full Explore UI, detail panel, deep links,
  exports (M6).

## Prerequisites & locked decisions
- prerequisites: EP-7.
- locked decisions honored: ADR-0005 basemap; the UI palette/contrast spec;
  the table-parity principle (even the slice page has the table).
- dependencies: none external at runtime (no third-party calls).

## Safety preconditions
Standing policy (see EP-1). Packet-specific: no third-party calls;
attribution present; page labeled work-in-progress and makes no claims.

## Likely components & contracts (proposed)
`site/` (index.html, main.js, styles); `src/phillysim/publish/sitebuild.py`;
Playwright smoke + axe check in CI.

## Implementation notes
This page is the seed of M6, not a throwaway: keep the map/table fed from the
same public-zone artifacts (the parity mechanism starts here).

## Acceptance criteria & evidence
- [ ] Page renders map + table from public-zone artifacts fully offline.
- [ ] axe: no violations; keyboard reaches all controls.
- Evidence: Playwright + axe green in CI against the fixture-built site;
  screenshot committed (own work).

## Tests / validation
Playwright + axe in CI against fixture-built site.

## Resource budget
Trivial.

## Risks, rollback, stop condition
UI scope creep — anything beyond "render + table + vintage + attribution"
belongs to M6; stop there.

## Documentation / ADR updates
Site README section; screenshot into repo.

## Handoff payload (fill at session end)
- packet ID + status; baseline/roadmap version
- files changed; commands/tests run + results
- resource observations
- decisions/ADRs made; unresolved risks/questions
- no-go areas touched? (must be none)
- exact next packet: M3 refinement gate (author EP-9+ from _TEMPLATE.md)
