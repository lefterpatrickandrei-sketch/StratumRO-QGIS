# MODEL_PROVIDER_MAP.md — Capability-Based AI Provider Architecture

> **Architecture:** Decoupled Model Abstraction Layer  
> **Rule:** StratumRO survives provider outages, API deprecations, and network cuts  
> **Key Principle:** Deterministic GIS math stays in Python/C++; LLMs do planning, synthesis & diagnosis

---

## 1. Provider Independence & Fallback Tiers

StratumRO is designed so that no single external AI provider is mandatory. If OpenAI is unreachable, Claude or Gemini takes over. If cloud services or the internet are cut, local Ollama and local PyTorch/ONNX models handle execution.

```mermaid
graph TD
    TASK[Task from User / Antigravity] --> ROUTER{Capability Router}

    ROUTER -->|Deterministic GIS / Cadastre| DET[Local PyQGIS / GDAL / Shapely]
    ROUTER -->|Building Segmentation| SAM[Local Meta SAM 2 / ONNX]

    ROUTER -->|Planning & Reasoning| CLOUD_REASON{Cloud Available?}
    CLOUD_REASON -->|Yes| OPENAI[OpenAI: GPT-4o / o3-mini]
    CLOUD_REASON -->|Fail / Alt| CLAUDE[Anthropic: Claude 3.5 Sonnet]
    CLOUD_REASON -->|Fail / Alt| GEMINI[Google: Gemini 1.5 / 2.5 Pro]
    CLOUD_REASON -->|No / Offline| OLLAMA[Local Ollama: Llama 3.2 / Qwen 2.5]

    ROUTER -->|Vision / Multimodal QA| CLOUD_VISION{Cloud Vision Available?}
    CLOUD_VISION -->|Yes| NIM[NVIDIA NIM: Llama 3.2 11B/90B Vision]
    CLOUD_VISION -->|No / Offline| LOCAL_VIS[Local SAM 2 + nDSM Analysis]
```

---

## 2. Model & Provider Catalog

| Provider | Integration Type | Models Supported | Current Status | Required Credentials / URL | Primary Purpose |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Union Alpha** | Remote REST API (OpenRouter) | `stealth/union-alpha` (262k context) | **CONFIGURED & OPERATIONAL** | `UNION_ALPHA_API_KEY` (Present in `.env`)<br>URL: `https://openrouter.ai/api/v1` | 256k large-context repository analysis, multi-file architectural reasoning, complex cadastral debugging |
| **NVIDIA NIM** | Remote REST API (OpenAI client) | `meta/llama-3.2-11b-vision-instruct`<br>`meta/llama-3.2-90b-vision-instruct`<br>`meta/llama-3.3-70b-instruct` | **CONFIGURED** | `NVIDIA_API_KEY` (Present in `.env`)<br>URL: `https://integrate.api.nvidia.com/v1` | Fast multimodal vision analysis, cloud GPU acceleration |
| **OpenAI** | Remote REST API (`openai` SDK) | `gpt-4o`<br>`gpt-4o-mini`<br>`o3-mini` | **AVAILABLE IN VENV** (Key required) | `OPENAI_API_KEY` (Developer API key, not ChatGPT Plus) | Multi-step task planning, root-cause diagnosis of failed segmentations |
| **Anthropic** | Remote REST API (`httpx` / `anthropic`) | `claude-3-5-sonnet`<br>`claude-3-7-sonnet` | **OPTIONAL** | `ANTHROPIC_API_KEY` | Architectural reviews, code audits, adversarial validation |
| **Google Gemini** | Antigravity Control Plane / REST | `gemini-1.5-pro`<br>`gemini-2.5-pro` | **NATIVE IN AGY** | Built into Antigravity IDE (or optional `GEMINI_API_KEY` for scripts) | Control plane orchestration, large-context workspace planning |
| **Ollama** | Local REST HTTP | `llama3.2:3b`<br>`qwen2.5-coder:7b`<br>`mistral:7b` | **LOCAL ENGINE** | `http://localhost:11434` (No API key, zero cost) | 100% offline fallback, private cadastral data processing |
| **Local SAM 2** | Local PyTorch Engine (`torch`) | `sam2_hiera_tiny.pt`<br>`sam2_hiera_large.pt` | **READY ON DISK** | GPU CUDA / DirectML / CPU (Weights in `models/sam2/`) | High-resolution building boundary segmentation |
| **ONNX Runtime** | DirectML / CPU (`onnxruntime`) | SAM 2 ONNX exported models | **READY (SKELETON)** | DirectX 12 GPU on Windows (Zero CUDA dependency) | Lightweight cross-vendor local inference |

---

## 3. Capability-Based Task Routing Matrix

The orchestrator selects tools and providers based on task characteristics, security requirements, and available hardware:

| Task Type | First Choice Provider | Second Choice Fallback | Offline / Air-Gapped Fallback | LLM Ingestion Permitted? |
| :--- | :--- | :--- | :--- | :--- |
| **Polygon Area / Perimeter** | Deterministic (Shapely / PyQGIS) | *None needed* | Deterministic | **NO (Strictly Forbidden)** |
| **CRS Reprojection (Stereo 70)** | GDAL / OGR / QgsCoordinateTransform | *None needed* | Deterministic | **NO (Strictly Forbidden)** |
| **Topology Validation** | Shapely `is_valid` + `explain_validity` | *None needed* | Deterministic | **NO (Strictly Forbidden)** |
| **nDSM Elevation Profile** | `LidarProcessor` (`laspy` + `scipy`) | *None needed* | Deterministic | **NO (Strictly Forbidden)** |
| **Building Optical Segmentation** | Local SAM 2 (PyTorch GPU) | Local ONNX DirectML | Local SAM 2 CPU | Mask weights only |
| **AOI Work Plan Decomposition** | Union Alpha / OpenAI `gpt-4o` | Claude 3.5 Sonnet / Gemini | Ollama `llama3.2` | High-level metadata only |
| **Complex Multi-File Debugging & Failure Diagnosis** | Union Alpha (`stealth/union-alpha`) | OpenAI `gpt-4o` / Claude | Local / Deterministic | Diagnostic logs only |
| **Segmentation Anomaly Diagnosis** | NVIDIA NIM Vision / Union Alpha | OpenAI `gpt-4o` / Claude | Ollama + nDSM Stats | Thumbnail chip + Stats |
| **TopoLT CAD / PAD Generation** | Deterministic `CadastralDxfExporter` | *None needed* | Deterministic | **NO (Strictly Forbidden)** |

---

## 4. Cost, Privacy & Latency Guardrails

1. **Deterministic-First:** If an operation can be solved by linear algebra, spatial indexing (R-Tree), or exact geodetic transformation (EPSG:3844), **zero tokens are consumed**.
2. **Data Minimization:** Cadastral personal identifiers or legal property numbers are never transmitted to external cloud APIs. Only anonymous geometric bounding boxes and normalized raster chips are sent when vision models are explicitly queried.
3. **Graceful Degradation:** When an API key is missing or quota is exhausted, the system logs a `PROVIDER_UNAVAILABLE` event and automatically executes via local mock or Ollama without throwing fatal errors.
