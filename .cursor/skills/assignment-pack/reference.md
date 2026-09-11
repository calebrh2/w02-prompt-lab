# Assignment-pack reference

## Pack vs product

Identify files by **role**, then by filename or heading. Do not assume a claims-intake tree.

Search, in order: the folder the user named, then `docs/`, `docs/assignment*/`, `assignments/`.

| Kind | How to recognize | Role |
| --- | --- | --- |
| Instructions | `instructions`, `overview`, or `assignment` in the name or title; not acceptance/rubric | What this day asks and the step order |
| Acceptance | `acceptance-criteria` | Binary pass/fail list |
| Rubric | `rubric`, with `##` cells | Graded cells; one grader per `##` |
| Contract | `contract` in the name or title | Interface / field authority |
| Constraints | `relevant-changes`, `constraints` | Error types, retry, deliverables, what not to change |
| Feedback | `feedback.md` | Optional extra checks |
| Method | `articles/` | How to work; not the spec |
| Scratch | `notes/` | Never authority |

Required: instructions + acceptance criteria. Rubric required for cell graders; if absent, AC gate only.

**Slug:** pack folder name, shortened if it already contains a day id (e.g. `assignment-week2-day2` or `w02-02`). If the pack is a single file under `assignments/`, slug from the stem (`W02_Day1_Assignment_LOCAL` → `w02-day1`).

Examples in this lab: `docs/instructions.md` + `docs/acceptance-criteria.md` + `docs/callRecordContract.md`; `docs/assignment-week2-day2/w02-02-*.md`.

## Agent naming

Gate: `<slug>-acceptance-criteria` at `.cursor/agents/<slug>-acceptance-criteria.md`.

Cell graders: `<slug>-<cell-slug>` at `.cursor/agents/<slug>-<cell-slug>.md`.

Reuse files when they already exist **for this pack** and the pack is unchanged. Do not overwrite agents whose names belong to a different pack.

## Task launch

This chat: `Task` `subagent_type: generalPurpose`, prompt = the agent file body (system prompt plus “score now”). Newly written custom types often are missing from the enum until a new conversation.

Next chat: `subagent_type` equal to the agent `name` if listed.

Launch several graders in parallel. They must not edit the repo.

## Git commits

Commits are in-scope only when the assignment grades sequence (for example: failing tests committed before the matching implementation). Then follow that order in the history. Do not squash tests and implementation. Do not commit when the pack does not grade history.
