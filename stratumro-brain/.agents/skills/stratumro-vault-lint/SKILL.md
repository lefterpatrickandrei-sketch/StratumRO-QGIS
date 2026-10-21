---
name: stratumro-vault-lint
description: Validates the stratumro-brain vault with scripts/lint_vault.py (frontmatter, ids, status per folder, stale re-check dates, broken links, possible secrets). Use before every commit to the vault, after editing notes, or when the user asks whether the memory is healthy.
---

# Lint the vault

1. From the vault root run `python scripts/lint_vault.py` (on Windows `py scripts\lint_vault.py`). Run it with `--help` first if you need the options.
2. Do not read the script source; read its output.
3. Errors must be fixed before any commit:
   - missing or invalid frontmatter fields
   - `proposed` notes inside `canon/` (move them to `inbox/`)
   - duplicate ids
   - possible secrets (remove the text and tell the owner; rotate the secret if it was real)
4. Warnings are reported to the owner, not silently fixed: stale notes (past `recheck_by`), broken links, notes over 450 words.
5. When you change the rules in `MEMORY_RULES.md`, ask the owner before changing the linter.
