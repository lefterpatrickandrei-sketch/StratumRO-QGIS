# Provider Ownership Matrix — StratumRO Phase 4.2

**Authoritative Evidence-Based Ownership Classification of All AI Providers and Engines**  
*Status as of 2026-09-20 — Evaluated from Repository Call Graph & AST Inspection*

---

## 1. Provider Ownership Matrix

| Provider / Engine | File Location | Dev SDK | Product Runtime | Classification | Call Graph Evidence |
| :--- | :--- | :---: | :---: | :--- | :--- |
| **AnthropicProvider** | `stratum_ro/ai/providers/anthropic_provider.py` | **YES** | NO | **DEV SDK ONLY** | Imported by `scripts/validate_project.py` and `stratum_ro/test/test_ai_providers.py`. Zero imports in geomatics/cadastral runtime. |
| **OpenAIProvider** | `stratum_ro/ai/providers/openai_provider.py` | **YES** | NO | **DEV SDK ONLY** | Imported by `stratum_ro/ai/registry.py`, `scripts/validate_project.py`, and scratch review tools. Zero imports in cadastral runtime. |
| **UnionAlphaProvider** | `stratum_ro/ai/providers/union_alpha_provider.py` | **YES** | NO | **DEV SDK ONLY** | Consumed by `stratum_ro/ai/closed_loop.py` for Kilo adversarial code review and external audit tools. No role in spatial math. |
| **NvidiaNIMProvider** | `stratum_ro/ai/providers/nvidia_nim_provider.py` | **YES** | **YES** | **BOTH (Dual-Use)** | Consumed by `vlm_verifier.py` (optional runtime visual anomaly detection) and by Dev SDK review scripts (`test_nvidia_live.py`). |
| **LocalProvider** | `stratum_ro/ai/providers/local_provider.py` | NO | **YES** | **PRODUCT RUNTIME** | Air-gapped deterministic mock baseline providing 0.0ms local responses for offline runtime testing (`test_ai_router.py`, `test_task_spec.py`). |
| **OllamaProvider** | `stratum_ro/ai/providers/ollama_provider.py` | NO | NO | **EXCLUDED (§13, §80)** | Permanently excluded from target architecture. Daemon offline, models uninstalled, rejected as fallback. |
| **SAM 2 Engine (ONNX DirectML)** | `stratum_ro/sam2_engine.py`, `stratum_ro/onnx_engine.py` | NO | **YES** | **PRODUCT RUNTIME CV ENGINE** | Core computer vision engine generating building masks. Consumed by `stratum_ro_dockwidget.py`, `segmentation_tools.py`, `run_hybrid_full_aoi.py`. |

---

## 2. Model Registry Distinction (§23)

### Development Model Registry (Dev SDK)
- **Scope:** LLM coding, architectural reasoning, long-context repository search, and adversarial review.
- **Configured Models:**
  - `claude-3-5-sonnet-latest`, `claude-3-7-sonnet` (Anthropic)
  - `gpt-4o`, `o3-mini` (OpenAI)
  - `stealth/union-alpha` (OpenRouter)
  - `meta-llama/llama-3.3-70b-instruct` (SambaNova / Cerebras)
  - `gemini-3.8-flash`, `gemini-3.6-flash` (Google AI Studio)
  - `meta/llama-3.2-11b-vision-instruct` (NVIDIA NIM)
- **Host Location:** Dev SDK environment configurations (`.env`), not hardcoded in product core.

### Product Runtime Model Registry (StratumRO Product)
- **Scope:** Computer vision segmentation, feature extraction, and altimetric cross-validation.
- **Active Runtime Models:**
  - `sam2_hiera_small.onnx` / `sam2_hiera_base_plus.onnx` (DirectML accelerated ONNX image encoder and mask decoder).
  - Deterministic local mock engine (`LocalProvider`).
- **Host Location:** `stratum_ro/ai/registry.py` (capability router for spatial task specs).
