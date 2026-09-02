# Open questions & consciously deferred items

| ID | Item | Owner | Latest responsible decision point | Effect if unresolved |
|---|---|---|---|---|
| OQ-A | City Open Data Program reply to derivative-reuse confirmation email. 2026-08-23 attempt to opendata@phila.gov bounced (address does not exist); re-sent 2026-09-02 to maps@phila.gov, the contact listed on the City's Open Data Program page, cc info@opendataphilly.org; awaiting reply. Fallbacks: the OpenDataPhilly Google group (public thread); CopyrightAgent@phila.gov (website Terms-of-Use permission contact; last resort, since it frames the question under the website terms rather than the open-data terms) | owner (sent/managed by author) | before v1.0.0 release notes finalize the licensing prose | None blocking — documented contextual-inference position stands; a reply upgrades inference to fact |
| OQ-B | Dietitian-colleague review availability for clinical narrative | owner | M7 harm/claims review | Narrative held out of demo; tool ships without it |
| OQ-C | R5 determinism behavior | M3 spike | M3 verdict | Pinned seeds / documented variance band; wording already scoped |
| OQ-D | Market hours parse coverage threshold ("good enough" %) | owner + M4 QA report | M4 acceptance | Tier 2 limited to meal sites; markets Tier 1 with disclosed gap |
| OQ-E | "Philadelphia Food Access Collaborative" exact org name | author of community-context doc | before any public prose names it | Omit the name; describe the hospital collaboration generically |
| OQ-F | PMTiles-on-Pages range-request behavior | v1.x enhancement packet | at that packet | Enhancement stays unpursued; ADR-0005 default stands |
| OQ-G | Spanish localization scope | owner | v2 gate | Stays a v2 candidate (human-reviewed translation required) |
| OQ-H | Whether to deploy work-in-progress slice page (EP-8) publicly before M7 | owner | EP-8 | Defaults to not deployed |
| OQ-I | Reliability conventions assumed by the tinycity fixture and `phillysim.contracts.ANALYTIC_TABLE`, to confirm or revise: (1) CV = (MOE / 1.645) / estimate, i.e. a 90 % MOE per the ACS handbook; (2) tier edges 12 % / 40 % applied as tier 1 below 12 %, tier 2 from 12 % to below 40 %, tier 3 at or above 40 %; (3) `reliability_action = interval-only` exactly when the tier is 3, else `none` (methodology.md fixes only the set, not the rule); (4) `moe` and `cv_tier` null for quantities with no sampling error (decennial-weighted, travel times) | M5 metrics packet author + owner | first M5 packet, before any metric is published | Fixture conventions stand as the published rule; any later change bumps `methods_version` and regenerates the fixture |

Deferred-by-design (not open): police/crime data (v2 gate with justification
requirement); pharmacy/telehealth modules (five promotion criteria);
scenario layer; suburban catchment; formal research output.
