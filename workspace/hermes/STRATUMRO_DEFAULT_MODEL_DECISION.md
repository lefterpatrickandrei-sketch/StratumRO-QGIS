# STRATUMRO DEFAULT MODEL DECISION

**Date:** 2026-09-21

## Providers Tested

| Provider | Authentication | Configured | Catalog Available | Live Verified | Status |
|----------|---------------|------------|-------------------|---------------|--------|
| **OpenAI** | API Key (sk-...) | ✅ Yes (.env) | gpt-4o, gpt-4o-mini, o3-mini | ❌ Failed (429 - credits exhausted) | CONFIGURED |
| **Anthropic** | API Key (sk-ant-...) | ✅ Yes (.env) | claude-3-5-sonnet-latest, claude-3-5-haiku-latest, claude-3-7-sonnet-latest | ❌ Failed (400 - credits exhausted) | CONFIGURED |
| **NVIDIA NIM** | API Key (nvapi-...) | ✅ Yes (.env) | meta/llama-3.2-11b-vision-instruct, meta/llama-3.2-90b-vision-instruct, nvidia/llama-3.1-nemotron-70b-instruct, microsoft/phi-3-vision-128k-instruct | ✅ **meta/llama-3.2-11b-vision-instruct** LIVE VERIFIED | **LIVE VERIFIED** |
| **OpenRouter** | API Key | ✅ Yes (.env) | Not tested via StratumRO providers | UNKNOWN | CONFIGURED |
| **Local (Mock)** | None required | ✅ Built-in | deterministic-planner-v1, offline-mock-engine | ✅ Always available | LIVE VERIFIED |
| **Ollama** | Local daemon | ❌ Daemon offline | N/A | ❌ Unavailable | UNAVAILABLE |
| **Google/Gemini** | API Key | ✅ Yes (.env) | Not tested | UNKNOWN | CONFIGURED |
| **SambaNova** | API Key | ✅ Yes (.env) | Not tested | UNKNOWN | CONFIGURED |
| **Cerebras** | API Key | ✅ Yes (.env) | Not tested | UNKNOWN | CONFIGURED |
| **Union Alpha** | API Key | ✅ Yes (.env) | stealth/union-alpha | UNKNOWN | CONFIGURED |

## Models Tested (Live Probes)

| Provider | Model | Success | Latency | Error |
|----------|-------|---------|---------|-------|
| NVIDIA NIM | meta/llama-3.2-11b-vision-instruct | ✅ YES | **2.712s** | None |
| NVIDIA NIM | nvidia/llama-3.1-nemotron-70b-instruct | ❌ NO | 2.138s | HTTP 404 - Function not found for account |
| NVIDIA NIM | microsoft/phi-3-vision-128k-instruct | ❌ NO | 2.071s | HTTP 404 - Function not found for account |
| NVIDIA NIM | meta/llama-3.2-90b-vision-instruct | ❌ TIMEOUT | >90s | Timeout |
| Anthropic | claude-3-5-sonnet-latest | ❌ NO | 1.958s | Credit balance too low |
| OpenAI | gpt-4o | ❌ NO | 5.698s | Credit balance exhausted |
| Local | deterministic-planner-v1 | ✅ YES | **0.000s** | None (fallback mode) |

## Recommended Default

**DEFAULT PROVIDER:** NVIDIA NIM  
**DEFAULT MODEL:** meta/llama-3.2-11b-vision-instruct  

**LIVE TEST:** ✅ PASSED — Returned exactly "STRATUMRO_MODEL_TEST_OK" in 2.712s

**Reason:**
- Only provider with **LIVE VERIFIED** status among cloud providers
- Working API key configured and functional
- Supports VISION, REASONING, PLANNING capabilities needed for StratumRO
- Low latency (~2.7s) suitable for development workflow
- OpenAI-compatible endpoint via NVIDIA's integrate.api.nvidia.com

**Strengths:**
- Vision capability for multimodal verification (orthophotos, QGIS screenshots)
- Reasoning/planning capability for architecture and code tasks
- Always available (no local daemon dependency)
- Deterministic fallback via LocalProvider when needed

**Weaknesses:**
- Only 11B vision model currently accessible (90B and Nemotron 70B return 404)
- Single provider dependency — if NVIDIA NIM has issues, must fallback
- No direct access to larger reasoning models (Claude Sonnet, GPT-4o) due to credit limits

## Fallback

**FALLBACK PROVIDER:** Local (deterministic mock)  
**FALLBACK MODEL:** deterministic-planner-v1  

**FALLBACK EVIDENCE:** ✅ LIVE VERIFIED — Always available, 0ms latency, returns structured deterministic plans with EPSG:3844 CRS, proper administrative context, and pipeline steps.

**Note:** Per protocol, fallback must be LIVE VERIFIED. LocalProvider is the only universally available fallback. For cloud fallback, none currently meet the LIVE VERIFIED criteria (OpenRouter, Union Alpha, Google, SambaNova, Cerebras not yet probed live).

---

## Hermes Global Model Configuration (Separate from StratumRO Providers)

**Current Hermes Default:** `gpt-5.6-terra` via `openai-codex` (ChatGPT/Codex Subscription)  
**Hermes Config:** `~/AppData/Local/hermes/config.yaml` — model.default = gpt-5.6-terra, provider = openai-codex

This is the **Hermes agent reasoning model** (for chat, tool use, compression, approval routing) — distinct from StratumRO's AI provider registry used by the product runtime. The StratumRO default model decision above applies to **StratumRO AI Provider Registry** (`stratum_ro.ai.providers`), not to Hermes global config.