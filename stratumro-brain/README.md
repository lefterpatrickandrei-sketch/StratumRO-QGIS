# stratumro-brain (starter vault)

This folder is the shared memory for you and every AI agent that works on StratumRO. It is a normal Git repository full of Markdown files. Open the folder in Obsidian to read and edit it; agents read and write the same files.

Rules in one minute:

1. Truth lives in `canon/`. Only the owner moves a note there.
2. Agents write only to `inbox/` (shared) or `agents/<name>/` (private scratch), on their own branch.
3. Every note has frontmatter: who wrote it, where it came from, how sure it is, when to re-check it.
4. Nothing here is a secret. Passwords, API keys and private client data never go in this repository.
5. The full rules are in `MEMORY_RULES.md`. The map is `INDEX.md`.

Setup: paste the build prompt (`ANTIGRAVITY_PROMPT`) into Antigravity, or do it by hand:

1. Create a private Git repository (GitHub, GitLab or a self-hosted one) and push this folder to it.
2. Clone it on the workstation and on the laptop.
3. Open the folder as a vault in Obsidian on each machine.
4. In the StratumRO code repository, add the three lines from `MEMORY_RULES.md` (section "Pointer for AGENTS.md") to `AGENTS.md`.
5. Optional later: add an MCP server over this folder (see the report, section 6).
