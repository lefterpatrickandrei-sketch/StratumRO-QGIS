# Git Repository Relationship Matrix — StratumRO Forensic Audit

This matrix provides the verified forensic relationship between all Git repositories, worktrees, and branches identified across the workspace and local system during Phase 3.5.

---

## 1. Worktrees & Internal Branches (StratumRO Local Ecosystem)

| Entity | Type | Filesystem Path | Remote Origin | Branch / Ref | Same Project? | Same Git History? | Keep / Action | Confidence |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **QGIS-AI (Canonical)** | Main Worktree (Root) | `C:/Users/lefpa/Downloads/QGIS-AI` | `https://github.com/lefterpatrickandrei-sketch/StratumRO-QGIS.git` | `main` (`c976864`) | **YES** (Canonical) | **YES** (Source of Truth) | **KEEP (CANONICAL)** | 100% |
| **geode-barber** | Secondary Git Worktree | `C:/Users/lefpa/Downloads/QGIS-AI/.kilo/worktrees/geode-barber` | `https://github.com/lefterpatrickandrei-sketch/StratumRO-QGIS.git` | Detached HEAD (`c976864`) | **YES** (Same repo) | **YES** (Bitwise identical to `main`) | **KEEP / PRUNE LATER** (Read-only agent worktree) | 100% |
| **lowly-vanilla** | Secondary Git Worktree | `C:/Users/lefpa/Downloads/QGIS-AI/.kilo/worktrees/lowly-vanilla` | `https://github.com/lefterpatrickandrei-sketch/StratumRO-QGIS.git` | `lowly-vanilla` (`0c840d3`) | **YES** (Same repo) | **YES** (Ancestor of `main`, 15 commits behind) | **KEEP / CLEAN LATER** (Historical agent scratch) | 100% |
| **mlops_qgis_pipeline_integration** | Secondary Git Worktree | `C:/Users/lefpa/.gemini/antigravity/worktrees/QGIS-AI/mlops_qgis_pipeline_integration` | `https://github.com/lefterpatrickandrei-sketch/StratumRO-QGIS.git` | `mlops_qgis_pipeline_integration` (`c193e6a`) | **YES** (Same repo) | **YES** (Ancestor of `main`, 49 commits behind) | **KEEP / PRUNE LATER** (Fully merged/superseded) | 100% |
| **smart-particle** | Local Branch | N/A (local ref) | `origin` | `smart-particle` (`0c840d3`) | **YES** (Same repo) | **YES** (Ancestor of `main`) | **KEEP** (Ancestor ref) | 100% |
| **add/test-llm-orchestrator** | Remote Tracking Branch | N/A (remote ref) | `origin` | `remotes/origin/add/test-llm-orchestrator` (`5f4c4ce`) | **YES** (Same repo) | **YES** (Ancestor of `main`, 47 commits behind) | **KEEP** (Remote ref) | 100% |

---

## 2. External Repositories (Discovered in `C:\Users\lefpa\Downloads\`)

| Entity | Type | Filesystem Path | Remote Origin | Branch | Same Project? | Same Git History? | Keep / Action | Confidence |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **pug-geodesy-gis-toolkit** | Standalone Git Repository | `C:/Users/lefpa/Downloads/pug-geodesy-gis-toolkit` | `https://github.com/lefterpatrickandrei-sketch/pug-geodesy-gis-toolkit.git` | `main` (`2d23593`) | **RELATED (SUPPORT)** (PUG/MDLPA 904/2023 domain tool) | **NO** (0 common commits) | **KEEP SEPARATE** (Independent tool/lifecycle) | 100% |
| **OmniScan3D** | Standalone Git Repository | `C:/Users/lefpa/Downloads/OmniScan3D` | `https://github.com/lefterpatrickandrei-sketch/OmniScan3D.git` | `main` (`c26e2bd`) | **UNRELATED** (Field 3D scanner hardware toolkit) | **NO** (0 common commits) | **KEEP SEPARATE** (Independent project) | 100% |
| **nova-tech-models** | Standalone Git Repository | `C:/Users/lefpa/Downloads/nova-tech-models` | `https://github.com/lefterpatrickandrei-sketch/nova-tech-models.git` | `main` (`b47442a`) | **UNRELATED** (Web 3D product showcase) | **NO** (0 common commits) | **KEEP SEPARATE** (Independent project) | 100% |
| **website** | Standalone Git Repository | `C:/Users/lefpa/Downloads/website` | `https://github.com/lefterpatrickandrei-sketch/ugr-sector1-website.git` | `main` (`4e5b475`) | **UNRELATED** (Sector 1 municipal web portal) | **NO** (0 common commits) | **KEEP SEPARATE** (Independent project) | 100% |

---

## 3. Summary of Findings

1. **`geode-barber`** is **NOT** a separate repository. It is a secondary Git worktree created by Kilo (`.kilo/worktrees/geode-barber`) attached to the canonical StratumRO repository, currently sitting at detached HEAD `c976864` (identical to `main`).
2. **`mlops_qgis_pipeline_integration`** is **NOT** a separate repository. It is a Git worktree created by Antigravity under `.gemini/antigravity/worktrees/` checked out to branch `mlops_qgis_pipeline_integration` (`c193e6a`), which is a direct ancestor of `main` (49 commits behind `main`).
3. **No External Repo Merging Required:** No external repository needs to be merged into StratumRO. All StratumRO work is already inside `https://github.com/lefterpatrickandrei-sketch/StratumRO-QGIS.git`.
