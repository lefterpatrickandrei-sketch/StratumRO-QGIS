# StratumRO — Consulting & Audit Context for Claude Desktop

## 1. Operating Role of Claude Desktop
* **External Reviewer via MCP:** Claude Desktop operates as an independent, external reviewer and architectural consultant communicating via the local Model Context Protocol (MCP) over `stdio`.
* **Not Internal Core Runtime:** Claude Desktop is **NOT** a built-in execution provider or internal pipeline component of StratumRO. Antigravity is the primary development and execution engine, Kilo is the adversarial reviewer, and GitHub (`origin/main`) is the authoritative source of truth.

## 2. Available Verified Model Providers in StratumRO
* **OpenRouter / Kilo**: `OPENROUTER_API_KEY` in `.env`
  - Primary Verified Model: `meta-llama/llama-3.3-70b-instruct` (latency: 722 ms)
  - Fast / Linting Model: `meta-llama/llama-3.1-8b-instruct` (latency: 540 ms)
* **NVIDIA NIM**: `NVIDIA_API_KEY` in `.env`
  - Primary Verified Vision Model: `meta/llama-3.2-11b-vision-instruct` (latency: 652 ms)
* **Local Deterministic Fallback**: `LocalProvider` / `deterministic-planner-v1` (latency: 0.0 ms)
* **OpenAI Direct**: `NOT_CONFIGURED` (no direct API key)
* **Ollama**: `UNAVAILABLE` (local daemon offline)

## 3. Capability-Based Execution Rules
1. **Spatial Math & Cadastral Operations:** Strictly local deterministic Python (`shapely`, `geopandas`, `ezdxf`, `numpy`). NEVER use LLMs to calculate Stereo 70 coordinates, areas, or PAD tables.
2. **Optical Building Segmentation:** Meta SAM 2 Hiera (PyTorch GPU or ONNX DirectML) cross-referenced with LiDAR nDSM.
3. **Multimodal VLM Inspection:** NVIDIA NIM Vision via `stratum_ro/ai/vlm_verifier.py`.
4. **Code & Architecture Reviews:** OpenRouter (`llama-3.3-70b-instruct`) or external MCP reviews via Claude Desktop.

## 4. Testing Standard
Always verify using the local virtual environment:
```bash
venv\Scripts\python -m unittest discover stratum_ro/test
```
Report the exact verified test count (193 unit tests: 184 passed, 9 skipped, 0 failed).

