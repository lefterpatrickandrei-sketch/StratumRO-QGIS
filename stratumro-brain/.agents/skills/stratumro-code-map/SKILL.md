---
name: stratumro-code-map
description: Generates Markdown map pages of the StratumRO-QGIS code repository inside the vault (overview, documents, agents and skills, scripts, packages) so the owner can browse the repository from Obsidian. Use when the user wants to see the code repository or its files in Obsidian, after the code repository changed, or when a note needs a link to a code file.
---

# Code map

1. Find the local clone of the code repository. Ask the owner for the path if it is not obvious. Do not clone a second copy unless the owner asks.
2. Run from the vault root: `python scripts/code_map.py --repo <path-to-clone> --out code-map`.
3. The script reads tracked files only and never writes into the code repository. Run it with `--help` if unsure; do not read its source.
4. Check the output pages open without errors: `code-map/README.md`, `overview.md`, `documents.md`, `agents-and-skills.md`, `scripts-and-tools.md`, `packages.md`.
5. Commit on a branch with the message `code-map: refresh <commit>`. Generated pages are never edited by hand.
6. In notes, link code files with the GitHub link from the code map pages (it is pinned to a commit) or write the repo path in `sources` with the commit.
7. Optional local link so Obsidian can show the real files: create a folder junction named `code` in the vault root that points to the clone (Windows: `mklink /J code <path>`). The folder `code/` is in `.gitignore`. Test that `code/README.md` opens in Obsidian; if not, remove the link and rely on the code map pages.
