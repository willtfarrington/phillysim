# phillysim — session rules

The project's own rules, above Roadmap Wrangler's block; where the two differ, these win. The
roadmap and its conventions are in `roadmap/README.md`, the process decisions in `DECISIONS.md`,
the architecture-level choices in the ADRs under `roadmap/adr/`.

- **Briefs keep the work-packet shape** (D-3). A new brief (a split part such as `EP-16a`, or the
  next free number) is written from `roadmap/_TEMPLATE.md`: its YAML front matter, the packet's
  sections from Outcome & value to the Handoff payload, then the completion note. Those sections
  stand for the block's Context, In scope, Out of scope and Verification / acceptance; the Safety
  preconditions and the stop condition stay, and the payload's unresolved risks are the residual
  risk a re-plan walks. The briefs written before 2026-11-25 keep their header lines and payloads
  (D-1).

<!-- roadmap-wrangler:begin -->
## Roadmap house style

Written by Roadmap Wrangler (`crw formalise`; clauderoadmapwrangler D-4, D-10 … D-13) between
these markers, which it may rewrite: edit outside them. This file's own rules win where they
differ.

- **Read first:** `roadmap/README.md` (the next unchecked EP in table order and its brief notes
  under the phase table), `DECISIONS.md`, the last executed brief's completion note,
  `roadmap/owner-tasks.md` and `roadmap/inbox.md`.
- **Inbox triage:** for each open message, `- [ ] IN-n (from <project> EP-k, date) text`, roll it
  into this session if it fits the brief and is at most S-sized; otherwise add it to the brief
  notes of a named later EP or propose a new row in the right phase, confirming with the owner
  through `AskUserQuestion`; or decline it with a reason. Write the disposition on its line and
  tick its box.
- **Brief first:** an EP session starts by writing `roadmap/EP-N-<slug>.md` from
  `roadmap/_TEMPLATE.md`: YAML front matter (`ep`, `title`, `size`, `model`, `effort`, `status`),
  then Context, In scope, Out of scope and Verification / acceptance.
- **Completion note:** the brief ends with
  `> **Completion note (YYYY-MM-DD; model/effort; duration).**`, recording each owner decision and
  its outcome. A message for another project follows as a `> **Handed on (to <project>).**` block,
  which the tool delivers into that project's `roadmap/inbox.md` once the brief is committed.
- **Owner tasks:** what only the owner can do is appended to `roadmap/owner-tasks.md` as
  `- [ ] OT-n (EP-k, date) text`, ending `[before EP-m]` only when EP-m builds on it.
- **The roadmap:** phase tables `| # | Brief | Size | Depends on | Core | Done |`, a done row's
  cell `☑` and one backticked commit hash; each upcoming EP's detail is a `- **EP-n.** …` bullet
  under `**Brief notes.**`.
- **Sizes:** a brief is S (about 30 minutes of active work) or M (about 45): an S where its shape
  is known at planning and it touches a handful of files, an M for an investigation, a state
  machine or the choice of a tool. A row is not cut only to make it smaller, and a row that
  proves larger at pickup is split there, never run long.
- **Manual:** a project the owner calls working well enough to owe one keeps `docs/manual.md`
  (reference chapters, then a walkthrough of the routes no real use has met) and
  `docs/manual-changes.md`, where each brief that changes what a user sees or does adds a
  `## EP-n — <title> (date)` section before its close; the phase's re-plan folds that file into
  the manual and empties it. `crw manual` builds the PDFs, which are never tracked.
<!-- roadmap-wrangler:end -->
