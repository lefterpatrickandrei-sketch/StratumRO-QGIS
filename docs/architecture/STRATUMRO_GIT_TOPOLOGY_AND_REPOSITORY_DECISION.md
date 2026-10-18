# STRATUMRO — PHASE 3.5: GIT TOPOLOGY AUDIT & REPOSITORY CONSOLIDATION DECISION

**Document Type:** Formal Git Forensic Audit & Repository Architecture Decision  
**Project:** StratumRO (Cadastral & Geomatics Platform)  
**Phase:** Phase 3.5 — Git Topology Audit & Repository Consolidation Decision  
**Mode:** Strict Read-Only Inspection (Zero Git mutations executed)  
**Status:** `PASS`  
**Consolidation Required:** `NO` (All internal worktrees belong to the same Git repository; all historical branches are already merged/ancestors of `main`)

---

## 1. Executive Summary

A comprehensive forensic audit of the Git topology across the local development environment (`C:\Users\lefpa\Downloads\QGIS-AI`, `C:\Users\lefpa\Downloads\`, and `C:\Users\lefpa\.gemini\antigravity\worktrees\`) was performed to clarify entries displayed in the Antigravity Source Control interface.

**Core Findings:**
1. **The Canonical Repository** is `C:\Users\lefpa\Downloads\QGIS-AI`, tracking remote `origin` at `https://github.com/lefterpatrickandrei-sketch/StratumRO-QGIS.git` on branch `main` (`c976864`).
2. **`geode-barber`** is **NOT** an independent repository. It is a secondary Git worktree located at `C:\Users\lefpa\Downloads\QGIS-AI\.kilo\worktrees\geode-barber`, created by the Kilo review subagent. It is currently at detached HEAD pointing to commit `c976864` (identical to `main`).
3. **`mlops_qgis_pipeline_integration`** is **NOT** an independent repository. It is a secondary Git worktree located at `C:\Users\lefpa\.gemini\antigravity\worktrees\QGIS-AI\mlops_qgis_pipeline_integration`, created by Antigravity. It points to commit `c193e6a`, which is a direct linear ancestor of `main` (49 commits behind `main`). All its commits are already part of `main`.
4. **External Repositories** in `C:\Users\lefpa\Downloads\` (`pug-geodesy-gis-toolkit`, `OmniScan3D`, `nova-tech-models`, `website`) share zero Git history ($0$ common commits) with StratumRO and are intentionally separate projects with independent lifecycles.
5. **Zero Consolidation Merge is Required:** There are no divergent branches or orphaned external repositories containing StratumRO production code that need merging.

---

## 2. Canonical Repository

Forensic verification of the primary active workspace:
- **Working Tree Directory:** `C:\Users\lefpa\Downloads\QGIS-AI`
- **Git Common Directory:** `.git`
- **Is Inside Work Tree:** `true`
- **Current Branch:** `main`
- **HEAD Commit:** `c9768641acb0bef0806593c84f549acba5960703`
- **Remote Origin URL:** `https://github.com/lefterpatrickandrei-sketch/StratumRO-QGIS.git`
- **Last Commit Message:** `feat: implement Geospatial Platform App, FastAPI backend, and Closed-Loop Development System`
- **Verification Verdict:** `C:\Users\lefpa\Downloads\QGIS-AI` is unequivocally the **sole authoritative canonical repository** for StratumRO.

---

## 3. Source Control Entries

The entries visible in the IDE Source Control interface are automatically populated by VS Code / Antigravity Git extension scanning registered `.git/worktrees/` entries:
1. `QGIS-AI` (`main` branch) — The root workspace.
2. `geode-barber` — Registered in `.git/worktrees/geode-barber` (detached HEAD).
3. `mlops_qgis_pipeline_integration` — Registered in `.git/worktrees/mlops_qgis_pipeline_integration`.
4. `lowly-vanilla` — Registered in `.git/worktrees/lowly-vanilla`.

These are not multiple independent projects; they are parallel working directory checkouts sharing the exact same object database (`.git/objects`).

---

## 4. Repository Inventory

The forensic scan across `C:\Users\lefpa\Downloads\` discovered the following Git repositories:

| Repository Name | Path | Remote URL | Active Branch | Relationship to StratumRO |
| :--- | :--- | :--- | :--- | :--- |
| **StratumRO-QGIS** | `C:\Users\lefpa\Downloads\QGIS-AI` | `https://github.com/lefterpatrickandrei-sketch/StratumRO-QGIS.git` | `main` | **CANONICAL PLATFORM** |
| **pug-geodesy-gis-toolkit** | `C:\Users\lefpa\Downloads\pug-geodesy-gis-toolkit` | `https://github.com/lefterpatrickandrei-sketch/pug-geodesy-gis-toolkit.git` | `main` | Related Support Project (MDLPA PUG/RLU 904/2023) |
| **OmniScan3D** | `C:\Users\lefpa\Downloads\OmniScan3D` | `https://github.com/lefterpatrickandrei-sketch/OmniScan3D.git` | `main` | Unrelated (Hardware 3D scanner interface) |
| **nova-tech-models** | `C:\Users\lefpa\Downloads\nova-tech-models` | `https://github.com/lefterpatrickandrei-sketch/nova-tech-models.git` | `main` | Unrelated (3D Web asset showcase) |
| **website** | `C:\Users\lefpa\Downloads\website` | `https://github.com/lefterpatrickandrei-sketch/ugr-sector1-website.git` | `main` | Unrelated (Sector 1 municipal web portal) |

---

## 5. Branch Inventory

Inspection of all branches in the canonical repository (`git branch -a`):

| Branch Name | Type | Head Commit | Ahead of `main` | Behind `main` | Purpose / Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`main`** | Local (Active) | `c976864` | `0` | `0` | Canonical release and development tip |
| **`lowly-vanilla`** | Local | `0c840d3` | `0` | `15` | Historical vectorization sprint (fully in `main`) |
| **`smart-particle`** | Local | `0c840d3` | `0` | `15` | Historical vectorization sprint (fully in `main`) |
| **`mlops_qgis_pipeline_integration`** | Local | `c193e6a` | `0` | `49` | Historical MLOps pipeline sprint (fully in `main`) |
| **`origin/main`** | Remote tracking | `c976864` | `0` | `0` | Remote canonical reference |
| **`origin/mlops_qgis_pipeline_integration`** | Remote tracking | `c193e6a` | `0` | `49` | Remote historical branch |
| **`origin/add/test-llm-orchestrator`** | Remote tracking | `5f4c4ce` | `0` | `47` | Historical NIM harness PR (fully in `main`) |

**Critical Observation:** Every single local and remote branch is an **ancestor** of `main` (`ahead = 0`). There are zero unmerged branch commits anywhere in the repository.

---

## 6. Worktree Inventory

Inspection of `git worktree list`:

| Worktree Name | Filesystem Location | Branch / HEAD | Commit SHA | Working Tree State |
| :--- | :--- | :--- | :--- | :--- |
| **Root (QGIS-AI)** | `C:/Users/lefpa/Downloads/QGIS-AI` | `main` | `c976864` | Active workspace (Phase 3 Core extracted, clean tracked files) |
| **geode-barber** | `C:/Users/lefpa/Downloads/QGIS-AI/.kilo/worktrees/geode-barber` | Detached HEAD | `c976864` | Completely Clean (`git status --short` empty) |
| **lowly-vanilla** | `C:/Users/lefpa/Downloads/QGIS-AI/.kilo/worktrees/lowly-vanilla` | `lowly-vanilla` | `0c840d3` | Has uncommitted model-name edits from old Kilo session |
| **mlops_qgis_pipeline_integration** | `C:/Users/lefpa/.gemini/antigravity/worktrees/QGIS-AI/mlops_qgis_pipeline_integration` | `mlops_qgis_pipeline_integration` | `c193e6a` | Completely Clean (`git status --short` empty) |

All 3 secondary worktrees point back to `C:/Users/lefpa/Downloads/QGIS-AI/.git`.

---

## 7. Remote Inventory

Verification of `git remote -v`:
```text
origin  https://lefterpatrickandrei-sketch@github.com/lefterpatrickandrei-sketch/StratumRO-QGIS.git (fetch)
origin  https://lefterpatrickandrei-sketch@github.com/lefterpatrickandrei-sketch/StratumRO-QGIS.git (push)
```
- Only one remote exists (`origin`).
- Points directly to the intended public authoritative GitHub repository.
- Remote URL is correct: `YES`.

---

## 8. Commit History Relationships

Evaluation using `git merge-base`:
1. `git merge-base main mlops_qgis_pipeline_integration` = `c193e6a`
   - `git merge-base --is-ancestor mlops_qgis_pipeline_integration main` -> **`True`**
2. `git merge-base main lowly-vanilla` = `0c840d3`
   - `git merge-base --is-ancestor lowly-vanilla main` -> **`True`**
3. `git merge-base main remotes/origin/add/test-llm-orchestrator` = `5f4c4ce`
   - `git merge-base --is-ancestor remotes/origin/add/test-llm-orchestrator main` -> **`True`**
4. External repos (`pug-geodesy-gis-toolkit`, `OmniScan3D`, `nova-tech-models`, `website`):
   - Common commits with StratumRO: **`0`** (Unrelated histories).

---

## 9. `geode-barber` Analysis

- **What is it?** A secondary Git worktree allocated by the Kilo adversarial reviewer tool under `.kilo/worktrees/geode-barber`.
- **Where is it?** `C:\Users\lefpa\Downloads\QGIS-AI\.kilo\worktrees\geode-barber`.
- **What Git repository is it?** Canonical StratumRO (`StratumRO-QGIS`).
- **What remote does it use?** `origin` (`https://github.com/lefterpatrickandrei-sketch/StratumRO-QGIS.git`).
- **Does it contain StratumRO code?** Yes.
- **Does it share Git history with StratumRO?** Yes, it is checked out at commit `c976864`, which is identical to `main`.
- **Is it required by StratumRO?** No. It was used as a scratch review sandbox.
- **Should it remain separate?** It is already in the same repository. It can be safely pruned when Kilo review operations are completed.

---

## 10. `mlops_qgis_pipeline` Analysis

- **What is it?** A secondary Git worktree created by Antigravity under `.gemini/antigravity/worktrees/QGIS-AI/mlops_qgis_pipeline_integration` to isolate the `mlops_qgis_pipeline_integration` branch.
- **Where is it?** `C:\Users\lefpa\.gemini\antigravity\worktrees\QGIS-AI\mlops_qgis_pipeline_integration`.
- **What Git repository is it?** Canonical StratumRO (`StratumRO-QGIS`).
- **What remote does it use?** `origin` (`https://github.com/lefterpatrickandrei-sketch/StratumRO-QGIS.git`).
- **Does it contain StratumRO code?** Yes.
- **Does it share Git history with StratumRO?** Yes, commit `c193e6a` is a direct linear ancestor of `main`.
- **Is it required by StratumRO?** No. All of its commits were merged into `main` 49 commits ago.
- **Should it remain separate?** It is already in the same repository.

---

## 11. StratumRO File Overlap

Comparing file trees across the external projects:
- `pug-geodesy-gis-toolkit` contains PUG/MDLPA 904/2023 schemas, e-Urbanism parceling rules, and FME pipelines. It does **not** contain SAM2 ONNX engines, TopoLT DXF coordinate block generators, PAD tables, or QGIS dockwidget code.
- `OmniScan3D`, `nova-tech-models`, and `website` have 0% file overlap with `stratum_ro/`.
- Therefore, there is no code split across multiple repositories. All StratumRO assets reside exclusively in `QGIS-AI`.

---

## 12. Data / Model Repository Analysis

Inspection of large files in `QGIS-AI`:
- **Model Checkpoints:**
  - `models/sam2/sam2_hiera_tiny.pt` (148.7 MB) -> Gitignored (`.gitignore:61`).
  - `models/sam2/sam2_encoder.onnx` (104.2 MB) -> Gitignored (`.gitignore:63`).
  - `models/sam2/sam2_decoder.onnx` (15.8 MB) -> Gitignored (`.gitignore:63`).
- **Spatial Geodata:**
  - `workspace/output/cladiri_stereo70.gpkg` (18.4 MB), `workspace/output/cache_tile_Cluj-*.tif` (15.5 MB each) are tracked in Git (committed in `ddc0edc`).
  - While these provide immediate out-of-the-box reproducibility for the Cluj benchmark, future dataset scaling (> 100 MB) should utilize Git LFS or external cloud buckets (e.g. S3/HuggingFace).

---

## 13. QGIS Repository Boundary

The PyQGIS desktop plugin code (`stratum_ro/`, `stratum_ro_dockwidget.py`, `metadata.txt`) is currently housed inside the root of `QGIS-AI`.
- **Architectural Assessment:** Keeping the desktop plugin in the same repository as the domain logic and core algorithms during development accelerates end-to-end iteration (Closed-Loop Development).
- **Packaging Boundary:** The QGIS plugin manifest (`metadata.txt`) specifies `name=StratumRO`. Release builds package the `stratum_ro` directory into a `.zip` artifact via standard PyQGIS packaging tools without needing a separate Git repository.

---

## 14. AI / MLOps Boundary

The AI components:
- Local ONNX DirectML engine (`onnx_engine.py`)
- Multi-provider AI router (`stratum_ro/ai/router.py`)
- Task graph and capability resolver (`stratum_ro/ai/task_graph.py`, `capability_resolver.py`)
- Verification harnesses (`vlm_verifier.py`)

These reside in `stratum_ro/ai/` and `tools/`. They do not require a separate repository. They represent the AI Control Plane of the StratumRO platform.

---

## 15. Monorepo vs Multi-Repo Analysis

| Dimension | Monorepo Strategy (Current `QGIS-AI`) | Multi-Repo Strategy (Split Core / Plugin / AI) |
| :--- | :--- | :--- |
| **Reproducibility** | **Superior:** Single commit captures exact Core math, AI prompts, and QGIS layer styling. | Fragile: Version skew between core algorithms and QGIS UI. |
| **CI / Testing** | **Fast:** All 245 tests run in 35s in a unified virtual environment (`venv`). | Complex: Multi-repo submodules, pip release lags, CI matrix friction. |
| **Cadastral Auditability** | **High:** ANCPI compliance auditors can inspect algorithms, tests, and CAD exports in one place. | Low: Fragmented evidence across multiple repositories. |
| **Team Velocity** | High for pair-programming and assisted AI workflows. | Overhead of package publishing and dependency management. |

**Recommendation:** Maintain StratumRO as a **focused, modular monorepo** with strict internal package boundaries (`stratum_ro/core/`, `stratum_ro/domain/`, `stratum_ro/contracts/`).

---

## 16. Consolidation Decision

**Decision:** **NO GIT CONSOLIDATION REQUIRED.**
- Why? There is nothing to consolidate. All internal branches (`mlops_qgis_pipeline_integration`, `lowly-vanilla`, `smart-particle`) are already ancestors of `main`.
- `geode-barber` is already pointing to `main`.
- External repositories (`pug-geodesy-gis-toolkit`, etc.) are independent tools and must **NOT** be merged into StratumRO.

---

## 17. Keep-Separate Decision

The following repositories must remain separate:
1. **`pug-geodesy-gis-toolkit`**: Focuses on PUG / RLU (MDLPA 904/2023) urban planning, which operates on different legal timelines and schemas than ANCPI 600/2023 pre-cadastre.
2. **`OmniScan3D`**: Terrestrial laser scanner hardware integration.
3. **`nova-tech-models`** & **`website`**: Commercial web presentation projects.

---

## 18. Risks

1. **Worktree Confusion:** Secondary agent worktrees (`.kilo/worktrees/*`, `.gemini/antigravity/worktrees/*`) may confuse human developers viewing IDE Source Control into thinking divergent repos exist.
   - *Mitigation:* Document worktrees in this dossier; prune stale worktrees when agent sessions conclude.
2. **Untracked Scratch in Worktrees:** `lowly-vanilla` contains uncommitted scratch experiments.
   - *Mitigation:* Leave untouched in read-only mode during Phase 3.5; prune worktree via `git worktree remove` when ready.
3. **Large Binary Creep:** Adding additional GeoTIFFs or GPKGs directly to Git without LFS could cause repository bloat.
   - *Mitigation:* Enforce `.gitignore` on all new `.tif`, `.las`, `.laz`, `.pt` files.

---

## 19. Recommended Git Topology

The canonical Git topology for StratumRO is:

```text
https://github.com/lefterpatrickandrei-sketch/StratumRO-QGIS.git
                           │
                           └── main (c976864) [CANONICAL HEAD]
                                 ├── (Ancestor: lowly-vanilla / smart-particle @ 0c840d3)
                                 ├── (Ancestor: origin/add/test-llm-orchestrator @ 5f4c4ce)
                                 └── (Ancestor: mlops_qgis_pipeline_integration @ c193e6a)
```

**Worktrees Lifecycle Guidance:**
- `QGIS-AI` (Root workspace): The primary development working tree.
- `.kilo/worktrees/*`: Ephemeral review checkouts managed by Kilo.
- `.gemini/antigravity/worktrees/*`: Ephemeral task checkouts managed by Antigravity.
- When an agent task finishes, the worktree can be cleanly pruned with `git worktree prune`.

---

## 20. Preconditions for Any Future Consolidation

If in the future any external project (e.g. specific PUG utility functions) is considered for integration:
1. **Strict Legal & Scientific Isolation:** ANCPI cadastral accuracy standards (±10cm) must not be diluted by urban planning approximations.
2. **Independent Dependency Check:** Any imported code must pass the pure-Python test without adding heavy external dependencies.
3. **Formal RFC / Issue:** A dedicated Phase RFC must define the exact boundary before any `git subtree` or submodule operation.

---

# 21. FINAL GATE VERDICT

```text
======================================================================
PHASE 3.5 STATUS:
PASS

CANONICAL STRATUMRO REPO:
https://github.com/lefterpatrickandrei-sketch/StratumRO-QGIS.git (C:\Users\lefpa\Downloads\QGIS-AI)

SOURCE CONTROL ENTRIES:
- QGIS-AI (Root worktree on main @ c976864)
- geode-barber (Secondary worktree on main @ c976864)
- mlops_qgis_pipeline_integration (Secondary worktree on ancestor @ c193e6a)
- lowly-vanilla (Secondary worktree on ancestor @ 0c840d3)

GEODE-BARBER:
SAME PROJECT (Kilo secondary Git worktree, bitwise identical to main)

MLOPS_QGIS_PIPELINE:
SAME PROJECT (Antigravity secondary Git worktree, ancestor of main by 49 commits)

RECOMMENDED GIT TOPOLOGY:
Single modular monorepo (StratumRO-QGIS: main) with internal package boundaries

CONSOLIDATION REQUIRED:
NO (All branches are already ancestors of main; zero code merge needed)

PHASE 4 READY:
YES
======================================================================
```
