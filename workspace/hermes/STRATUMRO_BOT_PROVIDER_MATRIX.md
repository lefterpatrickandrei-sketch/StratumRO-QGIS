# STRATUMRO BOT PROVIDER MATRIX

**Date:** 2026-09-21  
**Model Audit Reference:** `workspace/hermes/STRATUMRO_DEFAULT_MODEL_DECISION.md`

## Bot-Provider-Model Assignment

| Bot | Capability | Provider | Model | Status | Evidence |
|-----|------------|----------|-------|--------|----------|
| **Architect** | architecture, dependency analysis, domain boundaries, planning, migration plans, risk analysis | **NVIDIA NIM** (primary) | `meta/llama-3.2-11b-vision-instruct` | LIVE VERIFIED | Returns STRATUMRO_MODEL_TEST_OK in 2.7s; supports VISION, REASONING, PLANNING |
| | | Local (fallback) | `deterministic-planner-v1` | LIVE VERIFIED | Always available, 0ms, structured deterministic plans |
| **Coder** | Python implementation, refactoring, bug fixes, tests, Git diff | **NVIDIA NIM** (primary) | `meta/llama-3.2-11b-vision-instruct` | LIVE VERIFIED | Same as Architect; tool-use capable via Hermes |
| | | Local (fallback) | `deterministic-planner-v1` | LIVE VERIFIED | Always available for planning tasks |
| **Geospatial** | GIS, geodesy, geometry, CRS, topology, LiDAR, raster, measurements | **NVIDIA NIM** (primary) | `meta/llama-3.2-11b-vision-instruct` | LIVE VERIFIED | Vision capability for orthophoto/map analysis; reasoning for geospatial logic |
| | | Local (fallback) | `deterministic-planner-v1` | LIVE VERIFIED | Deterministic Stereo 70 (EPSG:3844) plans |
| **QGIS** | QGIS, PyQGIS, Processing, plugin, QGIS runtime, MCP QGIS | **NVIDIA NIM** (primary) | `meta/llama-3.2-11b-vision-instruct` | LIVE VERIFIED | Vision for QGIS canvas screenshots; planning for QGIS workflows |
| | | Local (fallback) | `deterministic-planner-v1` | LIVE VERIFIED | QGIS project structure awareness |
| **Reviewer** | adversarial review, regression review, scientific safety, security, diff inspection, unsupported claims | **NVIDIA NIM** (primary) | `meta/llama-3.2-11b-vision-instruct` | LIVE VERIFIED | Independent model instance for review; vision for diff/screenshots |
| | | Local (fallback) | `deterministic-planner-v1` | LIVE VERIFIED | Always available for structural review |
| **Researcher** | official documentation, current technical research, library verification, QGIS docs, AI provider docs, regulatory-source verification, open-source research | **NVIDIA NIM** (primary) | `meta/llama-3.2-11b-vision-instruct` | LIVE VERIFIED | Long-context capability for research; vision for docs/screenshots |
| | | Local (fallback) | `deterministic-planner-v1` | LIVE VERIFIED | Structured research plans |

## Hermes Agent Reasoning Model (Separate)

| Component | Provider | Model | Purpose |
|-----------|----------|-------|---------|
| **Hermes Global Default** | OpenAI Codex (ChatGPT/Codex Subscription) | `gpt-5.6-terra` | Agent reasoning, chat, tool use, compression, approval routing, MCP routing |

## Provider Status Summary

| Provider | StratumRO AI Registry Status | Hermes Global Status | Notes |
|----------|------------------------------|----------------------|-------|
| **NVIDIA NIM** | ✅ LIVE VERIFIED (1/4 models) | Available via provider #13 | Only `meta/llama-3.2-11b-vision-instruct` works; others return 404 |
| **Local (Mock)** | ✅ LIVE VERIFIED | N/A | Guaranteed fallback, deterministic |
| **OpenAI** | ❌ CONFIGURED ONLY (credits exhausted) | ✅ ACTIVE (Codex subscription) | StratumRO registry: no credits; Hermes: uses Codex OAuth |
| **Anthropic** | ❌ CONFIGURED ONLY (credits exhausted) | Available via provider #7 | StratumRO registry: no credits |
| **OpenRouter** | ✅ CONFIGURED (keys in .env) | Available via provider #3 | Not live probed |
| **Union Alpha** | ✅ CONFIGURED (keys in .env) | N/A | Not live probed |
| **Google/Gemini** | ✅ CONFIGURED (keys in .env) | Available via provider #16/17 | Not live probed |
| **SambaNova** | ✅ CONFIGURED (keys in .env) | Available via provider #5 | Not live probed |
| **Cerebras** | ✅ CONFIGURED (keys in .env) | N/A | Not live probed |
| **Ollama** | ❌ EXCLUDED BY POLICY | Available via provider #6 | Daemon offline; project policy: EXCLUDED |

## Bot Model Assignment Rationale

Per protocol Section 50: *"Nu presupune că fiecare trebuie să aibă alt provider. Folosește diferențierea numai dacă există motiv și dovezi."*

**Decision:** All six StratumRO bots use the **same provider/model pair** (NVIDIA NIM / `meta/llama-3.2-11b-vision-instruct` as primary, Local as fallback) because:
1. Only ONE cloud provider is currently LIVE VERIFIED
2. The working model supports all required capabilities: VISION, REASONING, PLANNING
3. No evidence justifies different providers per bot
4. Resource constraint: 3 warm backends maximum initially

**Differentiation** happens at the **skill/MCP/prompt level**, not model level:
- Each bot gets distinct skills, MCP servers, and system prompts
- The SAME underlying model reasons differently based on context

## Warm Backend Allocation (3 Maximum)

| Backend | Assignment | Models |
|---------|------------|--------|
| Backend 1 | Architect + Geospatial (paired for architecture audits) | NVIDIA NIM |
| Backend 2 | Coder + Reviewer (paired for coding + review) | NVIDIA NIM |
| Backend 3 | QGIS + Researcher (paired for QGIS verification + research) | NVIDIA NIM |
| Overflow | Any additional bot | Local (fallback) |

## Future Differentiation Triggers

| Condition | Action |
|-----------|--------|
| OpenRouter credits restored + live probe passes | Assign Researcher → OpenRouter (long-context models) |
| Anthropic credits restored + live probe passes | Assign Reviewer → Anthropic (independent model family) |
| OpenAI Codex credits restored | Assign Coder → OpenAI (coding-optimized) |
| NVIDIA NIM 90B or Nemotron 70B becomes available | Upgrade primary model for all bots |

---

**Note:** This matrix reflects CURRENT live evidence. Update after each provider probe or credit restoration.