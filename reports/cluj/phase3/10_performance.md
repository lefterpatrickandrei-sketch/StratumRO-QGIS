# 10. Hardware Performance & GPU Latency Profile

**Document ID:** `REPORT-CLUJ-P3-10-PERFORMANCE`  
**Execution Date:** 2026-09-19  
**Platform:** StratumRO-QGIS — Cluj Phase 3  
**Author:** Antigravity Engineering Coordinator  
**Standard Compliance:** Evidence-First Scientific Rule (MEASURED)

---

## 1. Hardware & Runtime Specifications

| Component | Specification | Operational Status |
|:---|:---|:---|
| **Host System** | Windows 11 Enterprise (Build 10.0.26100) | Native Local Host |
| **GPU Hardware** | NVIDIA GeForce RTX 4050 Laptop GPU | Dedicated Device 0 |
| **Dedicated VRAM** | 6,141 MB GDDR6 | Peak Allocation: ~1,240 MB |
| **CUDA Capability** | sm_89 (Ada Lovelace) | PyTorch `cu124` Driver |
| **PyTorch Version**| 2.6.0+cu124 | Native CUDA acceleration |
| **Vision Model** | Meta SAM 2 Hiera Tiny (`sam2_hiera_tiny.pt`) | 148.7 MB model weights |
| **Python Environment**| Python 3.10.10 (`venv\Scripts\python.exe`) | Local Project Virtualenv |

---

## 2. End-to-End Latency Breakdown by Experiment

All latencies measured from disk load to final GeoJSON serialization:

| Experiment ID | Focus | Candidates / Items | Image Encode Latency | Prompt Inference Latency | Post-Processing & Reg | Total Runtime | Throughput (cands/sec) |
|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **E0** | Baseline | 94 | 0.61 s | 12.54 s | 0.00 s | **13.15 s** | 7.15 |
| **E1** | Candidate Gen | 75 | 0.39 s | 7.42 s | 0.32 s | **8.13 s** | 9.22 |
| **E2** | Veg Filtering | 31 | 0.39 s | 3.18 s | 0.31 s | **3.88 s** | 7.99 |
| **E3** | Box Prompting | 31 | 0.35 s | 3.82 s | 0.32 s | **4.49 s** | 6.90 |
| **E4** | Multi-Point | 31 | 0.35 s | 3.31 s | 0.31 s | **3.97 s** | 7.81 |
| **E5** | Multi-Scale | 31 | 0.34 s | 3.44 s | 0.32 s | **4.10 s** | 7.56 |
| **E6** | Mask Fusion | 26 | 0.43 s | 3.29 s | 0.42 s | **4.14 s** | 6.28 |
| **E7** | Vectorization | 26 | 0.37 s | 2.89 s | 0.41 s | **3.67 s** | 7.08 |
| **E8** | Orientation CAD| 26 | 0.37 s | 2.92 s | 0.84 s | **4.13 s** | 6.30 |
| **E9** | **Integrated** | **26** | **0.36 s** | **2.68 s** | **0.61 s** | **3.65 s** | **7.12** |

---

## 3. Engineering Performance Observations

1. **Massive Efficiency Gain from Vegetation Suppression:**
   - Pruning 44 non-building candidates in deterministic preprocessing reduced neural prompt decoding from $12.54\,\text{s}$ down to $2.68\,\text{s}$.
   - Total pipeline execution accelerated by **$3.6\times$** (from $13.15\,\text{s}$ down to $3.65\,\text{s}$).
2. **Backbone Feature Caching:**
   - Encoding the entire $2,500 \times 2,000$ image once takes only **$0.36\,\text{s}$**.
   - Subsequent prompt queries decode at $\approx 100\,\text{ms}$ per candidate on GPU.
3. **Memory Safety:**
   - Peak VRAM consumption never exceeded $1.4\,\text{GB}$ during full execution, comfortably operating within the $6.1\,\text{GB}$ dedicated VRAM limit with zero out-of-memory risks.
