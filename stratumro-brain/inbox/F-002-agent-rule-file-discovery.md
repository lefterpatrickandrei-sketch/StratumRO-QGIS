---
id: F-002
type: fact
status: proposed
author: perplexity-computer
source_type: public
sources:
  - url: https://opencode.ai/docs/rules/
    retrieved: 2026-10-21
  - url: https://antigravity.google/docs/rules/
    retrieved: 2026-10-21
  - url: https://antigravity.google/docs/cli/commands/agents.md
    retrieved: 2026-10-21
  - url: https://arxiv.org/html/2602.11988v1
    retrieved: 2026-10-21
confidence: medium
created: 2026-10-21
recheck_by: 2026-12-21
cssclasses:
  - note-fact
supersedes: []
---
# F-002 How OpenCode and Antigravity find rule files

Claims [PUB]:
- OpenCode reads `AGENTS.md` in the project root first and uses `CLAUDE.md` only if no `AGENTS.md` exists. Extra files are added through the `instructions` list in `opencode.json`. It does not follow file references written inside `AGENTS.md`.
- Antigravity combines `AGENTS.md`, `GEMINI.md` and `.agents/rules/*.md`; files in `rules/` need YAML frontmatter with a trigger. Its CLI documentation places custom agents at `.agents/agents/<name>/agent.md`.
- A study of coding-agent context files found LLM-generated context files reduced task success by about 3% on average and raised cost by more than 20%; developer-written files improved success by about 4% on average and raised cost by up to 19%. The authors suggest keeping only minimal requirements.

Not verified: whether the 18 flat files in the repository's `.agents/agents/` are discovered by Antigravity.
