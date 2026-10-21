---
name: stratumro-memory-review
description: Helps the owner run the weekly review of the stratumro-brain inbox. Lists pending notes, checks them against the repo and sources, and prepares promotion to canon. Use when the user says review the inbox, promote notes, weekly memory review, or approve a note.
---

# Weekly review gate

The agent prepares; the owner decides. Never move a note into `canon/` unless the user has said, in this conversation, which note ids to approve.

1. Run `git fetch --all` and list branches named `agent/*`. For each, show `git diff main --stat` for `inbox/`.
2. Check that each branch changed only `inbox/` and `agents/<name>/`. A branch that touches `canon/`, `MEMORY_RULES.md`, `scripts/` or `.agents/` is held back and reported. Run `python scripts/lint_vault.py` in a worktree of each branch. Report errors first.
3. For each pending note give: id, title, author, confidence, sources, and a verdict among promote, reject, needs more evidence.
   - Open at least one source of every fact marked high confidence and confirm the quoted claim is on the page.
   - For [REPO] claims, check the file or number in the code repository at the cited commit.
4. Show the table to the owner and wait for the list of ids to approve.
5. For each approved id: move the file to `canon/decisions|facts|lessons/`, set `status: approved` (or `verified` if the check in step 3 passed), set `recheck_by`, update `INDEX.md`, and run the linter again.
6. For each rejected id: move it to `archive/` and add one line at the top saying why.
7. After the owner agrees, merge the clean agent branches into the review branch (they only add notes to `inbox/` and `agents/`). Commit on a review branch with the message `review: promote <ids>, archive <ids>` and tell the owner to merge it.
8. Never force-push, never rewrite history, never delete a note.
