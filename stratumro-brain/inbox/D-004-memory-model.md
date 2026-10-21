---
id: D-004
type: decision
status: proposed
author: perplexity-computer
source_type: agent-inference
sources:
  - path: StratumRO Memory Architecture Report
confidence: medium
created: 2026-10-21
recheck_by: 2026-12-21
cssclasses:
  - note-decision
supersedes: []
---
# D-004 Memory model (PROPOSED, not yet approved)

Proposal: one private Git repository of Markdown files (this vault) is the source of truth; Obsidian is the human editor over the same folder; agents read it directly and, later, through an MCP server. Agents write only to `inbox/` on their own branch; the owner promotes notes to `canon/`.

Why: keeps a reviewable history, lets each tool read it without new software, and limits the damage if a wrong or poisoned note is written (see the report for sources).

Needs: owner approval.
