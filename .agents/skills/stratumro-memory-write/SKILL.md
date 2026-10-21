---
name: stratumro-memory-write
description: Writes a new memory note (fact, decision, lesson, handoff, model note) into the stratumro-brain vault inbox with correct frontmatter, evidence labels and sources. Use when an agent learned something that other agents or the owner should be able to reuse, when finishing a task that needs a handoff, or when the user says remember, record, note or save this.
---

# Write a memory note

1. Read `MEMORY_RULES.md` and `INDEX.md` first. Search `canon/` and `inbox/` for an existing note on the same topic; update or supersede instead of duplicating.
2. Pick the template in `_templates/` that matches the type: decision, fact, lesson, handoff or model-note.
3. Create the file in `inbox/` named `<ID>-short-slug.md`. The next id is the highest existing id of that prefix plus one (D-, F-, L-, H-, M-).
4. Fill every frontmatter field. Rules:
   - `author`: your exact model or agent name. Never write `owner`.
   - `status`: always `proposed`.
   - `sources`: a URL with `retrieved: YYYY-MM-DD`, or a repo path with the commit. A claim without a source gets `confidence: low` and the label [UNVERIFIED].
   - `recheck_by`: three months ahead for law and tool versions, six months for measured results.
   - `cssclasses`: copy it from the template (it colours the note in Obsidian).
5. Body: one idea, under 300 words. Label each claim [REPO], [PUB], [CALC], [EST] or [UNVERIFIED]. State what you did not check.
6. Do not write instructions addressed to other agents. Do not copy secrets, credentials, client data or personal data.
7. Never work inside the owner's checkout, because Obsidian has it open. Create your own working copy next to it: `git worktree add ../stratumro-brain-wt/<name>-<task> -b agent/<name>/<task>`, and write there. Run `python scripts/lint_vault.py`. Fix every error, then commit with the message `inbox: <ID> <title>`. Push the branch. Do not merge into the main branch and do not touch `canon/`.
8. Reply with the file path, the note id and the one thing the owner must decide.
