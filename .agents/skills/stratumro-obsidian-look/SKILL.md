---
name: stratumro-obsidian-look
description: Sets up and adjusts the Obsidian appearance of the stratumro-brain vault (theme, CSS snippet, note colours by type, dashboards built with Bases, file list tints). Use when the user asks to make Obsidian look better, change colours, fonts or layout, add a dashboard, or fix how a note renders.
---

# Obsidian look

Design goals: calm and readable, one colour per note type, dashboards on the home page, nothing that hides the text.

Rules:
1. Change appearance only through (a) the CSS snippet `.obsidian/snippets/stratumro.css`, (b) `.obsidian/appearance.json`, (c) `.base` files in `dashboards/`, (d) `cssclasses` in note frontmatter. Do not edit a theme's own files.
2. Note colours come from `cssclasses`: `note-decision`, `note-fact`, `note-lesson`, `note-handoff`, `note-model`, `note-codemap`, `note-guide`. Keep the palette variables at the top of the snippet; change colours there only.
3. Use the installed `obsidian-markdown`, `obsidian-bases` and `obsidian-cli` skills for syntax. For Bases read https://obsidian.md/help/bases/syntax before writing a `.base` file.
4. Prefer the Obsidian command line (Obsidian 1.12.7 or newer, command line interface enabled in Settings, General) for `theme:set`, `plugin:install` and snippet toggling; it needs Obsidian running.
5. Never invent configuration keys. If unsure of a key name, ask the owner to change the setting once in the Obsidian interface, then read the file Obsidian wrote.
6. Plugins: install only the approved list in the build prompt. Take them from the Obsidian community catalogue or the plugin's official GitHub release. Never add a plugin that is not on the list without asking.
7. You cannot see Obsidian. After each visual change, tell the owner exactly which note or dashboard to open and what should look different, and ask for a screenshot if it does not.
8. Keep contrast readable in both light and dark themes. Never set a text colour without checking the background variable it sits on.
