---
type: guide
cssclasses:
  - note-guide
---
# Where each tool reads its files

Obsidian shows Markdown, Bases, Canvas, images, audio, video and PDF. Folders that start with a dot (`.agents`, `.obsidian`) and files like `.json`, `.py` or `.css` are not shown in the file list by default. This page is the visible map of those places.

## In this vault (stratumro-brain)

| What | Path | Read by |
|---|---|---|
| Agent rules for the vault | `AGENTS.md` | OpenCode, Antigravity, Claude Code (falls back to CLAUDE.md), others |
| Shared skills (5 custom + 3 Obsidian skills) | `.agents/skills/<name>/SKILL.md` | Antigravity and OpenCode both scan this path |
| Memory rules | `MEMORY_RULES.md` | humans and agents, linked from AGENTS.md |
| Templates | `_templates/*.md` | you, in Obsidian |
| Look and feel | `.obsidian/snippets/stratumro.css`, `.obsidian/appearance.json` | Obsidian |
| Checker | `scripts/lint_vault.py` | agents and you, from a terminal |
| Code repository map generator | `scripts/code_map.py` | agents and you, from a terminal |

## In the code repository (StratumRO-QGIS)

| What | Path | Read by |
|---|---|---|
| Rules | `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.agents/rules/*.md` | OpenCode, Claude, Antigravity |
| Agent definitions (18 today) | `.agents/agents/*.md` | Antigravity (see the Rebuild Blueprint for reducing them) |
| Skills | `.agents/skills/<name>/SKILL.md` | Antigravity, OpenCode |
| OpenCode config | `opencode.json` (planned in the Rebuild Blueprint) | OpenCode |
| MCP config | `mcp_config.json` | the client that is set to use it |

## Global places on your computer

| What | Path | Note |
|---|---|---|
| Antigravity skills (app and IDE) | `~/.gemini/config/skills/` | the IDE also accepts the older `~/.gemini/antigravity/skills/` |
| Antigravity CLI skills | `~/.gemini/antigravity-cli/skills/` | |
| Antigravity global rule | `~/.gemini/GEMINI.md` | |
| OpenCode skills | `~/.config/opencode/skills/`, `~/.agents/skills/`, `~/.claude/skills/` | OpenCode also reads project `.opencode/skills/`, `.claude/skills/`, `.agents/skills/` |

On Windows `~` is your user folder, for example `C:\Users\<you>`.

## How to open non-Markdown files

1. Turn on Settings, Files and links, Show all file types. Files appear in the file list but open in your default program.
2. Or read the generated pages in `code-map/`, which list code and data files with links to the repository.
