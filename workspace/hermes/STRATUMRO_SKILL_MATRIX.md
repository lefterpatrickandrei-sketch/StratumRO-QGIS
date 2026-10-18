# STRATUMRO SKILL MATRIX

**Date:** 2026-09-21

## Project-Local Skills (StratumRO-specific)

| Skill | Source | Installed | Enabled | Bot | Purpose |
|-------|--------|-----------|---------|-----|---------|
| gsd-cadastre | `.agents/skills/gsd-cadastre/SKILL.md` | ✅ | ✅ | Architect, Geospatial, Coder | Spec-driven cadastral workflow (Discuss→Research→Plan→Execute→Test→QGIS Verify→Kilo Audit) |
| qgis-live | `.agents/skills/qgis-live/SKILL.md` | ✅ | ✅ | QGIS, Geospatial | QGIS Desktop 3.40 live interaction, spectator mode, visual canvas inspection, MCP communication |
| huashu-design | `.agents/skills/huashu-design/SKILL.md` | ✅ | ⚠️ Large (54KB) | Architect, Reviewer | Design system / architecture documentation (review content before enabling) |

## Hermes Official Skills (Relevant to StratumRO)

| Skill | Source | Installed | Enabled | Bot | Purpose |
|-------|--------|-----------|---------|-----|---------|
| github | `official/software-development/github` | ✅ | ✅ | Architect, Coder, Researcher | GitHub via gh CLI: PRs, issues, reviews, repos, auth |
| git | `official/software-development/git` | ❌ | ❌ | Coder, Architect | Git operations via terminal (built-in) |
| python | `official/software-development/python` | ❌ | ❌ | Coder, Geospatial | Python development, debugging, review |
| test-driven-development | `official/software-development/test-driven-development` | ❌ | ❌ | Coder, Reviewer | TDD: enforce RED-GREEN-REFACTOR |
| systematic-debugging | `official/software-development/systematic-debugging` | ❌ | ❌ | Coder, Reviewer | 4-phase root cause debugging |
| requesting-code-review | `official/software-development/requesting-code-review` | ❌ | ❌ | Reviewer | Pre-commit review: security scan, quality gates |
| codebase-inspection | `official/software-development/codebase-inspection` | ✅ | ✅ | Architect, Researcher | Inspect codebases w/ pygount: LOC, languages, ratios |
| external-project-onboarding | `official/software-development/external-project-onboarding` | ✅ | ✅ | Architect | Use when onboarding external codebases |
| inspecting-hermes-desktop-dom | `official/software-development/inspecting-hermes-desktop-dom` | ❌ | ❌ | QGIS | Read live Hermes desktop DOM/CSS over CDP |
| node-inspect-debugger | `official/software-development/node-inspect-debugger` | ❌ | ❌ | - | Debug Node.js via --inspect + CDP |

## Hermes Official Skills (MCP, Research, Web)

| Skill | Source | Installed | Enabled | Bot | Purpose |
|-------|--------|-----------|---------|-----|---------|
| grounded-citations | `official/research/grounded-citations` | ❌ | ❌ | Researcher | Ground answers in cited, verifiable sources |
| arxiv | `official/research/arxiv` | ❌ | ❌ | Researcher | Search arXiv papers by keyword, author, category |
| competitor-news-monitor | `official/research/competitor-news-monitor` | ❌ | ❌ | Researcher | Watch named companies for material news |
| blocked-page-recovery | `official/web/blocked-page-recovery` | ❌ | ❌ | Researcher | Use when fetch fails: 403/429, paywall, WAF |
| web_search | built-in | N/A | ✅ | Researcher | Search the web for information |

## Community Skills (Clawhub/Skills.sh - Not Installed)

| Skill | Source | Category | Potential Bot | Notes |
|-------|--------|----------|---------------|-------|
| qgis-agent | clawhub/community | QGIS | QGIS | Drives native QGIS 1000+ Processing algorithms |
| qgis | clawhub/community | QGIS | QGIS | Run QGIS geospatial processing with qgis_process |
| gis | clawhub/community | GIS | Geospatial | GIS concepts, spatial data formats, projections |
| geospatial-osint | clawhub/community | Geospatial | Geospatial | Geospatial intelligence gathering |
| geospatial-analysis | clawhub/community | Geospatial | Geospatial | Analyze geospatial data using geopandas |
| mapbox-geospatial-operations | clawhub/community | Geospatial | Geospatial | Mapbox geospatial operations |
| geomaster | github/community | Geospatial | Geospatial | Comprehensive geospatial science skill |
| geopandas | github/community | Geospatial | Geospatial | Python library for geospatial vector data |
| geoscience-data | github/community | Geospatial | Geospatial | Reads/transforms gridded geospatial data |
| code-review | clawhub/community | Code Review | Reviewer | Production-ready code review at either scope |
| github | clawhub/community | GitHub | Architect, Coder | GitHub API integration with managed OAuth |
| git | clawhub/community | Git | Coder | Commits, branches, merges, rebases |
| python | clawhub/community | Python | Coder, Geospatial | Writes, debugs, reviews Python code |

## Recommended Skill Installations for StratumRO Bots

### Priority 1 (Install Immediately)
- `official/software-development/github` — Already loaded via Hermes
- `official/software-development/codebase-inspection` — Already loaded
- `official/software-development/external-project-onboarding` — Already loaded
- `official/research/arxiv` — For research on geospatial methods
- `official/research/grounded-citations` — For evidence-first research

### Priority 2 (Install for Specialist Bots)
- `clawhub/qgis` or `clawhub/qgis-agent` — For QGIS bot (evaluate first)
- `clawhub/gis` — For Geospatial bot (GIS concepts, projections)
- `clawhub/code-review` — For Reviewer bot (production-ready review)

### Priority 3 (Evaluate Before Install)
- `github/geomaster` — Comprehensive geospatial science (large, review first)
- `github/geopandas` — Vector data operations
- `official/software-development/requesting-code-review` — Pre-commit review

## Installation Commands

```bash
# Priority 1
hermes skills install official/research/arxiv
hermes skills install official/research/grounded-citations
hermes skills install official/software-development/requesting-code-review

# Priority 2 (evaluate first)
hermes skills inspect clawhub/qgis
hermes skills inspect clawhub/qgis-agent
hermes skills inspect clawhub/gis
hermes skills inspect clawhub/code-review

# Project-local skills are already available in .agents/skills/
```

## Skill Categories Summary

| Category | Project-Local | Hermes Official | Community (Not Installed) |
|----------|---------------|-----------------|---------------------------|
| Git | - | github | git, github |
| GitHub | - | github | github |
| Repository | - | codebase-inspection, external-project-onboarding | repository-discovery, repository-health |
| Python | - | python (built-in terminal) | python |
| Testing | - | test-driven-development, systematic-debugging | testing, testing-handbook |
| QGIS | qgis-live | - | qgis-agent, qgis |
| GIS/Geospatial | gsd-cadastre | - | gis, geospatial-osint, geospatial-analysis, geomaster |
| Geodesy | gsd-cadastre | - | cgcs2000 |
| Cadastre | gsd-cadastre | - | - |
| LiDAR | gsd-cadastre | - | - |
| Raster | gsd-cadastre | - | geoscience-data |
| Computer Vision | gsd-cadastre (SAM2/ONNX) | - | - |
| Research | - | arxiv, grounded-citations, competitor-news-monitor | paper-lookup, bioinformatics |
| Documentation | huashu-design | - | document-multiple-repository |
| Code Review | - | requesting-code-review | code-review, cot-code-review |
| Security | - | - | oss-forensics, security-threat-model |
| Windows/PowerShell | - | terminal (built-in) | - |