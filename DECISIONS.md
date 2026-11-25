# phillysim — decision log

The project's decisions in the form shared by every project under `DATA`:
`**D-n Title.** Decision. *Why.* *Alternatives.*`, one entry per decision,
never rewritten, amended by a dated addendum
(`> **Addendum (date, EP-n).** …`) under the entry it changes.
Architecture-level and hard-to-reverse choices made before this log existed
are the ADRs in [roadmap/adr/](roadmap/adr/) (ADR-0001 … ADR-0008); they
stay in force and continue to take such choices, with the decision numbers
ADR-0008 pins. This log takes the process and convention decisions, starting
with the roadmap's migration to the house tables.

**D-1 Roadmap tables in the house style.** From 2026-11-11 the phase tables
of `roadmap/README.md` use the header
`| # | Brief | Size | Depends on | Core | Done |`: one row per brief, kept
where it was with its id (letter suffixes included), its linked title, its
Size cell and its Depends-on cell as written; `core` in every Core cell, since
no row was marked optional; a done row's cell `☑` and one backticked commit
hash, an open row's `☐`; the milestone headings carry the same marks; the next
brief is the first unchecked row in table order. Each of the 18 done briefs
(EP-1 to EP-15, the split halves EP-4a/4b, EP-5a/5b and EP-8a/8b included)
ends with a `> **Completion note (<date>).**` block dated by its handoff
payload, naming its commit and the payload it comes from; the one open brief,
EP-16, has a `- **EP-16.** …` bullet under `**Brief notes.**` beneath the
Checkpoints table. The payloads, the briefs' wording and their packet-style
header lines (`**Status:** [x] <hash> · **Milestone:** …`), `_TEMPLATE.md`
and every file name are unchanged; nothing was renamed, moved or deleted; no
row was in progress (`[~]`) at the migration, and EP-5 and EP-8, the names of
split sets rather than rows, got no note. The closing "Phase overview" table
of the README, not a phase table to the parser, keeps its `[x]` and `[ ]`
cells (the owner's choice), and the migration is also recorded under
`## [Unreleased]` in `CHANGELOG.md`, the project's habit for every change. The files Roadmap Wrangler's
formalise step writes (a `CLAUDE.md` rule block, `roadmap/owner-tasks.md`,
`roadmap/inbox.md`, the house brief template) were not created here; they are
the owner's `crw formalise` step. *Why.* Roadmap Wrangler reads the
work-packet form read-only (clauderoadmapwrangler D-9) and the house tables
are the form its sessions, launch prompts and status reading are written
against; the owner asked for the migration from Roadmap Wrangler on
2026-11-11. The tool's reading was checked before and after with
`crw roadmap`: the same next EP (EP-16), the same counts (18 of 19 rows done;
21 briefs, 18 complete), no problem, the profile `packet` before and `house`
after. *Alternatives.* Keeping the packet form, which the tool reads but
treats as read-only; rewriting the briefs into the house brief shape (front
matter, Context, In scope), rejected because the tool reads the old forms and
the handoff payloads are the project's record of each packet; recording this
decision as ADR-0009, rejected because the ADRs hold architecture-level
choices and the house style keeps its log here.
