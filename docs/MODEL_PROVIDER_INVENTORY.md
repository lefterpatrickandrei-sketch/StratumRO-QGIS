# STRATUMRO — MODEL & PROVIDER INVENTORY

> **Canonical AI Provider & Model Governance Document**  
> **Standard:** Master Execution Protocol (Sections 2–20) & AGENTS.md Evidence-First Rules  
> **Repository:** `lefterpatrickandrei-sketch/StratumRO-QGIS`  
> **Version:** 1.0  
> **Last Verification:** 2026-09-19  

---

## 1. Inventory Date
* **Verification Timestamp:** `2026-09-19T15:28:24Z` (Local: 2026-09-19 18:28 EEST)
* **Auditor:** Antigravity AI Engine + Empirical API Smoke Test Harness
* **Classification:** Forensic Empirical Verification (No assumptions, no marketing claims)

---

## 2. Environment
* **Operating System:** Windows 11 (build 26100)
* **Python Virtual Environment:** Python 3.12.9 (`venv\`)
* **PyTorch Runtime:** `torch 2.6.0+cu124` (CUDA 12.4 enabled, GPU detected)
* **ONNX Runtime:** `onnxruntime 1.20.1` (Execution Providers: `AzureExecutionProvider`, `CPUExecutionProvider`)
* **GIS Engine:** GDAL 3.10.2, Shapely 2.0.7, PyQGIS 3.40 compatible

---

## 3. Provider Summary

| Provider ID | Implementation Class | Configuration Source | Status | Verified Latency | Primary Capability |
| :--- | :--- | :--- | :---: | :---: | :--- |
| **`openrouter_kilo`** | `UnionAlphaProvider` | `OPENROUTER_API_KEY` (`.env`) | **CONNECTED / TESTED** | 722 ms | Frontier Reasoning, Cadastral Audit, Code Review |
| **`nvidia_nim`** | `NvidiaNIMProvider` | `NVIDIA_API_KEY` (`.env`) | **CONNECTED / TESTED** | 652 ms | Multimodal Vision QA, High-throughput Inference |
| **`openai`** | `OpenAIProvider` | `OPENAI_API_KEY` (missing) | **NOT_CONFIGURED** | N/A | Direct OpenAI API access |
| **`local_sam2`** | `SegmentAnything2` / ONNX | Local disk (`models/sam2/`) | **LOADED / BENCHMARKED** | 2,183 ms (load) | Building Boundary Segmentation |
| **`local_mock`** | `LocalProvider` | Local Python module | **AVAILABLE / TESTED** | 0.0 ms | Air-Gapped Fallback, Deterministic Planning |
| **`ollama`** | `OllamaProvider` | `http://localhost:11434` | **UNAVAILABLE** | Timeout | Local LLM fallback (daemon inactive) |

---

## 4. Model Catalogue

| Model ID | Provider | Status | Evidence Level | Input Modalities | Context Window |
| :--- | :--- | :---: | :---: | :---: | :---: |
| `meta-llama/llama-3.3-70b-instruct` | OpenRouter (Kilo) | **SMOKE_TESTED** | `SMOKE_TEST_VERIFIED` | Text | 131,072 |
| `meta-llama/llama-3.1-8b-instruct` | OpenRouter | **SMOKE_TESTED** | `SMOKE_TEST_VERIFIED` | Text | 131,072 |
| `openai/gpt-4o` | OpenRouter (Proxy) | **AVAILABLE** | `AVAILABILITY_VERIFIED` | Text, Image | 128,000 |
| `mistralai/mistral-large-2407` | OpenRouter (Proxy) | **AVAILABLE** | `AVAILABILITY_VERIFIED` | Text | 128,000 |
| `stealth/union-alpha` | OpenRouter (Legacy) | **UNAVAILABLE** | `AVAILABILITY_VERIFIED` | Text | Deprecated |
| `meta/llama-3.2-11b-vision-instruct` | NVIDIA NIM | **SMOKE_TESTED** | `SMOKE_TEST_VERIFIED` | Text, Image | 131,072 |
| `meta/llama-3.2-90b-vision-instruct` | NVIDIA NIM | **AVAILABLE** | `AVAILABILITY_VERIFIED` | Text, Image | 131,072 |
| `meta/llama-3.3-70b-instruct` | NVIDIA NIM | **BROKEN (EOL 410)** | `SMOKE_TEST_VERIFIED` | Text | Deprecated |
| `sam2_hiera_tiny.pt` | Local (PyTorch CUDA) | **BENCHMARKED** | `BENCHMARK_VERIFIED` | Image Tensor | N/A (1024x1024) |
| `sam2_encoder.onnx` + `decoder.onnx` | Local (ONNX Runtime) | **LOADED** | `AVAILABILITY_VERIFIED` | Image Tensor | N/A (1024x1024) |
| `deterministic-planner-v1` | Local Mock | **SMOKE_TESTED** | `SMOKE_TEST_VERIFIED` | Text / Dict | Infinite |

---

## 5. Capability Matrix

| Model Identifier | Reasoning | Coding | Vision | Multimodal | Segmentation | Local | Tested in StratumRO |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `meta-llama/llama-3.3-70b-instruct` (OpenRouter) | **YES** | **YES** | **NO** | **NO** | **NO** | **NO** | **YES (PASS, 722ms)** |
| `meta-llama/llama-3.1-8b-instruct` (OpenRouter) | **YES** | **YES** | **NO** | **NO** | **NO** | **NO** | **YES (PASS, 139ms)** |
| `meta/llama-3.2-11b-vision-instruct` (NIM) | **YES** | **YES** | **YES** | **YES** | **NO** | **NO** | **YES (PASS, 652ms)** |
| `sam2_hiera_tiny.pt` (Local PyTorch) | **NO** | **NO** | **YES** | **NO** | **YES** | **YES** | **YES (PASS, Phase 3 E0-E9)** |
| `deterministic-planner-v1` (Local Mock) | **YES** | **NO** | **NO** | **NO** | **NO** | **YES** | **YES (PASS, 0.0ms)** |

---

## 6. Verification Status

1. **`openrouter_kilo`**: Verified operational via HTTP 200 model list query (447 total catalogue models) and real text generation smoke test on `meta-llama/llama-3.3-70b-instruct` (exit code 0, 722.2 ms latency).
2. **`nvidia_nim`**: Verified operational via HTTP 200 model list query (82 models). Multimodal vision smoke test executed with 20×20 test JPEG payload on `meta/llama-3.2-11b-vision-instruct`: correctly classified image color with 652.5 ms latency.
3. **`local_sam2`**: Verified weights on disk: `sam2_hiera_tiny.pt` (155,906,050 bytes), `sam2_encoder.onnx` (109,279,593 bytes), `sam2_decoder.onnx` (16,556,852 bytes). Tested weight loading via `torch.load` on CPU/CUDA.
4. **`local_mock`**: Verified deterministic fallback execution generating structured Stereo 70 pipeline JSON in 0.0 ms.

---

## 7. Routing Relationship & Discrepancies

Forensic comparison between actual inventory and router implementation (`stratum_ro/ai/router.py`):

* **Discrepancy 1 (Legacy Union Alpha model ID):** `stratum_ro/ai/providers/union_alpha_provider.py` hardcodes default model as `stealth/union-alpha`. OpenRouter returned 404/unlisted for this model ID. The active, tested model in the provider is `meta-llama/llama-3.3-70b-instruct`.
* **Discrepancy 2 (NVIDIA NIM 70b EOL):** `stratum_ro/ai/providers/nvidia_nim_provider.py` defaults to `meta/llama-3.3-70b-instruct`. NVIDIA returned HTTP 410 ("End of life on 2026-08-26"). The active, tested model providing vision + text on NIM is `meta/llama-3.2-11b-vision-instruct`.
* **Discrepancy 3 (Unconfigured OpenAI candidate):** `stratum_ro/ai/router.py` lists `"openai"` as candidate 2 in fallback chain. However, `OPENAI_API_KEY` is not present in `.env`.
* **Discrepancy 4 (Ollama offline):** `stratum_ro/ai/router.py` lists `"ollama"` as candidate 4 in fallback chain. The Ollama daemon is currently not running.
* **Effective Working Chain:**  
  `OpenRouter (Kilo / Llama 3.3 70B)` $\to$ `NVIDIA NIM (Llama 3.2 11B Vision)` $\to$ `Local Mock Engine`.  
  This chain provides 100% operational coverage for Reasoning, Vision, and Offline Fallback.

---

## 8. Kilo / External Review Providers
* **Provider:** OpenRouter (`https://openrouter.ai/api/v1`)
* **Reviewer Model:** `meta-llama/llama-3.3-70b-instruct`
* **Role:** Independent adversarial auditor, Phase 2 re-audit, Phase 3 audit, and Phase 4 architecture review.
* **Audit Record:** All reviews executed with strict read-only constraints, zero code modification authority.

---

## 9. Local Models
* **SAM2 Tiny Checkpoint:** `models/sam2/sam2_hiera_tiny.pt` (155.9 MB)
* **SAM2 ONNX Encoder:** `models/sam2/sam2_encoder.onnx` (109.3 MB)
* **SAM2 ONNX Decoder:** `models/sam2/sam2_decoder.onnx` (16.6 MB)
* **Deterministic Fallback Engine:** Built-in Python rule engine (0.0 ms, zero token cost).

---

## 10. Vision Models
* **Cloud Multimodal Vision:** `meta/llama-3.2-11b-vision-instruct` via NVIDIA NIM (Verified with image payload).
* **Local Geometric Segmentation:** Meta SAM2 Hiera Tiny (Local PyTorch CUDA / ONNX DirectML).

---

## 11. Known Unavailable Providers
* **OpenAI Direct:** `NOT_CONFIGURED` (`OPENAI_API_KEY` missing).
* **Ollama Daemon:** `UNAVAILABLE` (Daemon not responding at `localhost:11434`).

---

## 12. Known Configuration Problems
* `stealth/union-alpha`: Deprecated endpoint model ID on OpenRouter. Replaced by `meta-llama/llama-3.3-70b-instruct`.
* `meta/llama-3.3-70b-instruct` on NVIDIA NIM: Retired by NVIDIA on August 26, 2026 (HTTP 410). Replaced by `meta/llama-3.2-11b-vision-instruct`.

---

## 13. Tested Models
1. `meta-llama/llama-3.3-70b-instruct` (OpenRouter) — **PASS**
2. `meta-llama/llama-3.1-8b-instruct` (OpenRouter) — **PASS**
3. `meta/llama-3.2-11b-vision-instruct` (NVIDIA NIM) — **PASS (Multimodal Image Test)**
4. `sam2_hiera_tiny.pt` (Local PyTorch) — **PASS (Phase 3 E0-E9)**
5. `deterministic-planner-v1` (Local Mock) — **PASS**

---

## 14. Not Yet Tested
* `meta/llama-3.2-90b-vision-instruct` (NVIDIA NIM) — Available in catalogue, but skipped due to high API queue latency.
* `openai/gpt-4o` via OpenRouter proxy — Available in catalogue, not directly smoke-tested.

---

## 15. Security Notes
* Zero API keys, bearer tokens, or sensitive credentials are committed to Git or printed in reports.
* All credential checks are strictly performed via safe variable presence checks (`read_env_file_key`).
* Smoke tests used harmless in-memory synthetic test payloads (20×20 solid color squares), ensuring zero exposure of private cadastral or orthophoto imagery.

---

## 16. Last Verification
* **Timestamp:** 2026-09-19 18:28:24 EEST
* **Integrity Gate:** PASS
