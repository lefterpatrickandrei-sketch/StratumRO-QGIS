<!-- Metadata: Provider=nvidia_nim, Model=meta/llama-3.2-11b-vision-instruct, Duration=68.82s -->

**Computer Vision and Remote Sensing Evaluation**
=====================================================

**Verified Facts**
-----------------

1. The Phase 3 empirical performance is based on the Meta SAM 2 Hiera Tiny model checkpoint (`models/sam2/sam2_hiera_tiny.pt`) used in `sam2_engine.py`.
2. The `candidate_generator.py` module applies nDSM height thresholding and morphological closing (5x5) to generate candidate regions.
3. The `vegetation_filter.py` module uses the ExG (Excess Green) index to filter out non-vegetation regions.
4. The `mask_fusion.py` module fuses the SAM2 mask with the nDSM height consensus to generate a final mask.
5. The `prompt_generator.py` module generates box, box+center, and multi-point prompts for the SAM2 model.

**Vision Architecture Assessment**
---------------------------------

The current vision pipeline architecture is a combination of AI inference, deterministic image filtering, and morphological processing. However, there is a clear separation between these components, which can be improved for robust multi-sensor extraction.

* AI inference is performed using the SAM2 model in `sam2_engine.py`.
* Deterministic image filtering is performed using the `candidate_generator.py` and `vegetation_filter.py` modules.
* Morphological processing is performed using the `mask_fusion.py` module.

To improve the architecture, we can separate the AI inference pipeline from the deterministic image filtering and morphological processing pipelines. This will allow for more flexibility and robustness in the vision pipeline.

**Detailed Analysis of Cluj Empirical Results**
---------------------------------------------

The Phase 3 empirical results show a significant drop in false positives (FP) from 90 to 22, but the recall remains stuck at 6.15%. This can be attributed to the following reasons:

* The box-only prompt strategy used in `prompt_generator.py` may not be effective for all types of buildings.
* The lack of fine-tuned domain segmentation weights for Romanian historical campus structures may lead to poor performance.
* The resolution mismatch between the orthophoto (5cm) and LiDAR (1m) data may lead to poor performance.

**Critical Vision Risks**
-------------------------

1. Over-reliance on zero-shot SAM2 without fine-tuning may lead to poor performance.
2. The box-only prompt brittleness may lead to poor performance for certain types of buildings.
3. The resolution mismatch between orthophoto and LiDAR data may lead to poor performance.

**Missing Components**
----------------------

1. Multi-point prompting is not used in the current pipeline, which may lead to poor performance.
2. Shadow invariant indices are not used in the current pipeline, which may lead to poor performance.
3. Edge-guided refinement is not used in the current pipeline, which may lead to poor performance.
4. Adaptive nDSM thresholding is not used in the current pipeline, which may lead to poor performance.

**Architectural Contradictions**
------------------------------

Treating SAM2 as an LLM provider instead of a deterministic CV inference pipeline may lead to poor performance.

**Migration Risks**
------------------

Refactoring CV modules into a Remote Sensing / CV Domain Pack may lead to:

* Loss of flexibility in the vision pipeline.
* Increased complexity in the architecture.

**Scientific Risks**
------------------

1. Mask binarization threshold sensitivity may lead to poor performance.
2. Non-deterministic contour tracing may lead to poor performance.

**Concrete Recommendations**
---------------------------

1. Upgrade the vision pipeline architecture to separate AI inference from deterministic image filtering and morphological processing.
2. Use multi-point prompting and shadow invariant indices to improve performance.
3. Use edge-guided refinement and adaptive nDSM thresholding to improve performance.
4. Fine-tune domain segmentation weights for Romanian historical campus structures.
5. Use multi-scale feature fusion to improve performance.

**Code References**

* `models/sam2/sam2_hiera_tiny.pt`: Meta SAM 2 Hiera Tiny model checkpoint.
* `candidate_generator.py`: nDSM height thresholding and morphological closing (5x5) module.
* `vegetation_filter.py`: ExG (Excess Green) index module.
* `mask_fusion.py`: SAM2 mask and nDSM height consensus fusion module.
* `prompt_generator.py`: Box, box+center, and multi-point prompt generator module.
* `sam2_engine.py`: SAM2 model inference module.
* `stratum_ro/ai/providers/`: BaseAIProvider, NvidiaNIMProvider, UnionAlphaProvider, OpenAIProvider, OllamaProvider, LocalProvider.
* `stratum_ro/ai/`: router.py (AIRouter), task_graph.py (TaskGraph), task_executor.py (TaskExecutor), risk_engine.py (RiskEngine), provenance.py (ProvenanceChain), context_engine.py (ContextEngine), registry.py (CapabilityRegistry, ProviderRegistry).