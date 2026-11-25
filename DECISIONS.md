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

**D-2 Brief sizes: S about 30 minutes, M about 45, no L.** From 2026-11-25 a
packet is S (about 30 minutes of active work) or M (about 45), as the Sizes
bullet of Roadmap Wrangler's rule block in `CLAUDE.md` says: an S where its
shape is known when it is written and it touches a handful of files, an M
for an investigation, a state machine or the choice of a tool. L stays
invalid. A packet is not cut only to make it smaller, and one that proves
larger at pickup is split there by the README's split convention (the
parent's number kept, letter suffixes), never run long. The Size cells of
the rows written before (EP-1 to EP-16) stay as written, sized under the
rule of 2026-09-02 (one packet, one session); the one open row, EP-16,
written as "S (1 session)" with seven scope items, is split at its pickup.
*Why.* The owner settled it in Roadmap Wrangler's sweep (inbox IN-1, from
its EP-55) on 2026-11-25: these are the sizes of the owner's projects
(clauderoadmapwrangler D-4 and its addenda), for predictable time and usage
per session, where a packet sized "one session" ran as long as its work did
(EP-15's row took two sessions). *Alternatives.* Keeping "S = one session"
as a project rule over the block's Sizes bullet, rejected as against the
rule the owner keeps across projects; splitting EP-16 in the sweep itself,
left to its pickup as the rule says.

**D-3 Formalised, with briefs on the work-packet template.** On 2026-11-25
Roadmap Wrangler's formalise step wrote `CLAUDE.md` (a title and the tool's
rule block between the `roadmap-wrangler` markers, which the tool may
rewrite) and
`roadmap/owner-tasks.md` (its header), and kept `roadmap/inbox.md` and
`roadmap/_TEMPLATE.md`. The project's own rules sit in `CLAUDE.md` above the
markers and win where they differ. The first keeps the work-packet shape for
every new brief: `_TEMPLATE.md` now opens with YAML front matter (`ep`,
`title`, `size`, `model`, `effort`, and `status`: `planned` when a gate
authors the packet, `in progress`, `done`), its header line carries the
milestone, size, dependencies and parallel work, its sizing note follows
D-2, its payload's README line reads the `☑` form of D-1, and it ends with
the completion note; the packet's sections stand for the block's Context,
In scope, Out of scope and Verification / acceptance. The briefs written
before keep their header lines and payloads (D-1). *Why.* The owner
settled both in the sweep (IN-1): the house files make the project read
like the others in Roadmap Wrangler, and the packet template carries what
the house template has no place for, each packet's safety preconditions,
stop condition and handoff payload, which every brief so far has used. The
formalise step was run with the project's full folder path, because from
the repository root the bare name `phillysim` resolves to the package
folder `phillysim/` (reported to Roadmap Wrangler, its IN-18).
*Alternatives.* The house brief template, with the safety preconditions
moved into `CLAUDE.md`, a larger change; settling the shape at EP-16's
pickup, which would have left the block and the template disagreeing until
then; leaving the formalise step to the project's row in Roadmap Wrangler.
