# Brain / worker orchestration (Claude brain, Gemini worker) - design

Status: DRAFT for owner review, 2026-10-26. Additive: does not change architecture v2, the golden
rules in [AGENTS.md](../../../AGENTS.md) or any `canon/` decision. Complements
[HYBRID_DEV_WORKFLOW.md](../../HYBRID_DEV_WORKFLOW.md) (section 5 routing).

## 1. Intent

The owner works inside the Antigravity IDE with two agents side by side: Claude Code (Opus or
Sonnet) and the Gemini agent in the Antigravity panel (Gemini 3.8 Flash, called "Argon" by the
owner). Today the owner relays work between them by hand.

Three roles (owner correction, 2026-10-26):
- **Brain: Claude** (Opus or Sonnet). Plans, writes the task brief, makes the final decision.
- **Worker: Gemini 3.8 Flash.** Scaffolding, tests, docs, repetitive edits.
- **Verifier: Gemini 4 Argon** (available only in Antigravity 2.0). Does not write code; only checks
  whether the worker's output is done well and writes an independent verdict.

Success: the owner pastes one line per task into the matching agent (Flash to do, Argon to verify),
and Claude can decide from the repo alone. Argon's verdict is evidence, not the decision: Claude
re-runs the checks and decides, and the owner's verdict still overrides.

Constraints (from AGENTS.md): work in the shared repo, do not touch other agents' files, no
reset/stash/checkout of others' changes, worker output is a proposal until reviewed, never stamp
`ADMIS`, no new cloud service.

Assumptions: neither agent can call the other; both read and write the same working tree. The
channel is therefore files in the repo. Not automatic; automation is out of scope (see 7).

## 2. Layout

```
tasks/orchestration/
  README.md                  protocol summary and status values
  T-NNN-<slug>/
    brief.md                 written by Claude (brain)
    report.md                written by Gemini 3.8 Flash (worker)
    verify.md                written by Gemini 4 Argon (verifier, read-only)
    review.md                written by Claude (brain, final)
```

`tasks/` is currently untracked; the folder is created inside it. Committing it is a separate owner
decision.

## 3. Documents

`brief.md` (front matter + body):
- `id`, `title`, `created` (UTC), `status: BRIEFED`
- Goal in 1-3 sentences.
- `allow_paths`: exact files or globs the worker may create or edit. Anything else is forbidden.
- Steps: numbered, concrete.
- Verification commands the worker must run and paste output for (e.g. `python -m unittest ...`).
- Applicable rules: pointer to `.agents/rules/orchestration.md` plus any task-specific ones.

`report.md`: `status: DONE | BLOCKED`, files changed, commands run with real output, anything not
done, questions. No claims without output.

`verify.md`: written by Argon against the brief's acceptance checks. `verdict: PASS | FAIL |
UNCERTAIN`, a checklist of each step and acceptance check with the evidence seen (file and line,
command output it re-ran), and anything in the diff outside `allow_paths`. Argon edits no files other
than `verify.md`.

`review.md`: `verdict: ACCEPTED | REVISE | REJECTED`, the diff scope checked, commands re-run by
Claude, whether Claude agrees with `verify.md` and why. Only Claude writes it; the owner's verdict
still overrides.

Status flow: `BRIEFED -> DONE|BLOCKED -> VERIFIED -> ACCEPTED|REVISE|REJECTED`; `REVISE` loops back
with a dated addendum in `brief.md`.

## 4. Worker rules (`.agents/rules/orchestration.md`)

New rule file with `trigger: model_decision` front matter (existing rules show Antigravity needs a
valid `trigger`). Verifier clause: Argon reads brief, report and diff, re-runs the verification
commands, writes only `verify.md`, never fixes code, and says `UNCERTAIN` rather than guessing.
Worker content: read the brief first; edit only `allow_paths`; run the listed
verification; write `report.md` before stopping; never reset, stash, checkout or delete files; do not
commit unless the brief says so, and then only by explicit path; do not mark anything `ADMIS` or
accepted; stop and report `BLOCKED` instead of guessing. It does not extend `hybrid-routing.md`,
which is specific to Colab jobs.

## 5. Tool: `scripts/orch.py`

Standard library only. Subcommands:
- `new <slug> --title ...` creates `T-NNN-<slug>/brief.md` from a template (next free number).
- `status` lists tasks with their status from front matter.
- `review T-NNN` prints `git status --short` and `git diff` limited to the task's `allow_paths`,
  and flags any changed file outside them (changes by other agents are listed separately, not
  attributed to the worker).

Tests in `stratum_ro/test/` style (unittest) for numbering, front-matter parsing and the
out-of-scope detection, using a temporary git repo.

## 6. Flow

1. Owner states the goal to Claude. Claude decomposes and runs `orch.py new` per step.
2. Owner pastes into the Gemini 3.8 Flash panel: `Do tasks/orchestration/T-001-<slug>/brief.md and write report.md`.
3. Owner pastes into the Gemini 4 Argon panel: `Verify tasks/orchestration/T-001-<slug>/ and write verify.md only`.
4. Claude runs `orch.py review T-001`, reads `verify.md`, re-runs the verification, writes `review.md`.
5. `REVISE`: Claude appends an addendum and the owner re-pastes the worker line.

## 7. Out of scope

Automatic triggering of the Gemini panel; the Gemini CLI (`gemini -p`, installed at 0.50.0) as a
second worker over the same briefs (possible later, same format); concurrent workers on
overlapping `allow_paths`; committing or pushing.

## 8. Risks

- The worker may ignore the allow-list: mitigated by `orch.py review` diff scoping, not by trust.
- The verifier may rubber-stamp or hallucinate a pass: its verdict never decides alone; Claude
  re-runs the checks, and `verify.md` must cite evidence per item.
- Dirty tree (other agents' edits, e.g. `stratumro-brain/.obsidian/graph.json`): review reports them
  separately and never attributes them to the worker.
- Antigravity may not load the rule file: the brief itself repeats the key rules, so the protocol
  works even if the rule is not loaded.
