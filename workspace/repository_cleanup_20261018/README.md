# Repository cleanup — 2026-10-18

Owner-approved scope: consolidate documentation, retain historical files in tracked `junk/`, preserve product code, data, QGIS projects and other agents' work. StratumRO integrates specialist software such as QGIS; reusing its tools is intentional.

## Evidence before changes

- `baseline.json`: local HEAD, foreign dirty-file hashes, nine registered worktrees, Git storage and LFS state. Captured before migration.
- `file_inventory.json`: 2015 tracked and 936 nonignored untracked paths, excluding this task's new audit files. Inventory is not classification as junk or approval to publish.
- `python_structure.json`: static AST index; no product module imported or executed.
- `migration_manifest.json`: the 13 owner-approved moves and 3 exact entry-document snapshots, SHA-256, sizes and inbound filename mentions. This remains an immutable pre-migration record; completion is recorded separately.
- `remote_snapshot.json`: public GitHub `main` checked through a read-only connector. Local remote-tracking refs alone do not establish remote state.

`audit_repository.py` creates these four local snapshots once; it refuses to overwrite them. It never migrates, stages, deletes, runs inference or accesses secret values. Git metadata commands are its only subprocesses.

## Protected material

Keep all 16 previously dirty tracked paths and all existing untracked work intact. Do not move live QGIS/GIS results, raw data, models, production modules, nested worktrees, or ignored environment configuration. No automatic `git add -A`, reset, stash, clean, LFS migration, remote push or branch deletion.

The cleanup is not a runtime validation. Known code concerns remain: parallel cadastral product implementations, incomplete common raster contract, automatically assigned `ADMIS`, simulated manual timings and approximate PUG attributes. Document those concerns without claiming they were repaired.

## Publication

No GitHub write is authorized by the choice of `junk/` alone. The separate question about publication through a pull request versus direct main remains pending. The 35 pre-existing local commits also require publication review; a documentation PR based on local main would include them.

## Applied documentation work

The owner approved the exact 13 moves and original entry-document snapshots, then separately approved thin Kilo/Gemini entry points. `migration_applied.json` and `agent_entries_approval.json` record the actions. The existing `docs/readme.md` was preserved, replaced with a concise index and normalized to `docs/README.md` using two explicit Git moves, so links also work on case-sensitive GitHub. `case_rename.json` records this detail. Production source paths were not reorganized.

`update_document_links.py` repaired explicit moved-report links in nine existing documentation files; the archived report bodies were not edited. `link_updates.json` lists the touched paths. The product-identity document now points to the shared QGIS project and reflects the owner's clarification about reusing specialist software.

`verify_cleanup.py` checks the 18 original archive files, protected dirty-file hashes, presence of all 936 pre-existing untracked paths, the shared QGIS project, unchanged product diff and current navigation links. Its first pre-staging run incorrectly omitted this task's two new JSON targets from its link candidate set; that checker issue and its failed record are preserved as `verification_initial.json`. It was corrected before delivery. Diagram syntax was inspected as Markdown/Mermaid; no Mermaid renderer or product test suite was executed in this documentation task.

## References used

The installed `find-skills` workflow (`C:/Users/lefpa/.agents/skills/find-skills/SKILL.md`) was used for discovery. The official [GitHub awesome-copilot README skill](https://github.com/github/awesome-copilot/blob/main/skills/readme-blueprint-generator/SKILL.md) was read as a reference, not installed. Its template expects Copilot-specific source documents; StratumRO documentation is instead derived from actual local code and dated evidence.

[GitHub documentation on README files](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes), [Mermaid diagrams](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/creating-diagrams), and [Google documentation guidance](https://google.github.io/styleguide/docguide/best_practices.html) inform concise entry points, versioned diagrams and avoiding duplicated current instructions. The owner's preservation request takes precedence over generic advice to delete old documentation.
