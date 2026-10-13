# StratumRO: researched ML training options

Date: 2026-10-13. Status: RESEARCH AND PROPOSED EXPERIMENTS, not a trained model.
No packages installed, checkpoints downloaded, training started or QGIS outputs changed.

## Recommendation

After repairing input preparation and establishing a reproducible full-pipeline
baseline, compare a small local roof segmentation model against the existing
SAM2 workflow. Keep SAM2 as an optional refinement branch; do not assume two
models outperform one. NVIDIA TAO offers useful workflow patterns, but its current
documented deployment prerequisites exceed this machine. Do not replace the
working environment merely to adopt a toolkit.

Hardware measured locally with nvidia-smi: NVIDIA GeForce RTX 4050 Laptop GPU,
6141 MiB VRAM. Candidate small-model training feasibility is an inference requiring
a measured forward/backward memory trial, not a demonstrated training result.

## Primary-source findings

1. NVIDIA TAO SegFormer accepts paired images/masks and supports training,
evaluation, inference and export. It is a customization toolkit, not a pretrained
Romanian cadastral extractor. [Current SegFormer docs](https://docs.nvidia.com/tao/tao-toolkit/latest/text/cv_finetuning/pytorch/segformer.html).

2. Current TAO getting-started documentation specifies Linux/local or remote Docker
and 16 GB minimum VRAM, with 24 GB+ recommended for foundation-model fine-tuning.
Older TAO guides have different requirements; do not conflate versions or promise
current TAO will train locally on 6 GB. [Requirements](https://docs.nvidia.com/tao/tao-toolkit/latest/text/getting_started.html).

3. Microsoft AI for Good/World Bank studied scene-specific U-Net training. Their
2010 training set has 527 polygons: 437 building, 59 background, 31 road. They
report approximately 0.87 recall on held-out buildings. Sparse unknown pixels are
ignored during training. This is local-scene evidence, not precise cadastral
boundaries or Romanian geographic transfer. [Paper](https://arxiv.org/html/2206.05377v1).

4. Microsoft GlobalMLBuildingFootprints documents segmentation followed by
polygonization. Published polygons are predictions, not automatically trustworthy
labels for our imagery. [Official repository](https://github.com/microsoft/GlobalMLBuildingFootprints).

5. Meta releases SAM2 image/video fine-tuning code. Its supplied MOSE training
example assumes A100 80 GB GPUs; this is an example, not proof all partial
fine-tuning requires 80 GB. Reduced/frozen-encoder training would need a separate
implementation and resource benchmark here. [Training README](https://github.com/facebookresearch/sam2/blob/main/training/README.md).

6. TorchGeo provides geospatial datasets/samplers and training integrations;
consider it only if it removes actual dataset handling work. Rasterio plus a
small PyTorch dataset may suffice. [Official project](https://github.com/torchgeo/torchgeo).

7. A practitioner repository implements U-Net/SAM training and polygon export;
it is a code example, not independently verified benchmark evidence and not SAM2.
[Example](https://github.com/matteochestnut/Building-Footprint-Extraction).

## Proposed training data contract (not yet implemented)

Target the visible roof outline first. Ground footprint is a different annotation
task; an assumed inset does not supply measured ground truth. Define treatment of
attached wings, independent neighbors, canopies and greenhouses before labeling.

Maintain instance IDs even if the first model predicts a binary roof probability
map: binary semantic segmentation alone does not guarantee separate touching
buildings. Preserve interiors/courtyards and explicit unknown/occluded areas.
Do not label all unannotated pixels background in partially labeled images.

Build samples from georeferenced RGB and corrected polygons on the same pixel
grid. Record AOI, acquisition date, source, GSD, CRS, annotation version and spatial
split. Include verified negatives: pavement, parking, bare ground, trees, shadows
and other confusing surfaces, not only successful red roofs.

Use SAM2 predictions to accelerate drafting labels, then correct them on native
imagery before promotion into training data. Keep prediction provenance separate
from annotation provenance. T12 pavement and partial T17 are failures to correct,
not labels to learn. The 29 mixed GMW contours are not a clean building-only set.

Reserve one geographically separate AOI for final evaluation. Use disjoint blocks
and a suitable gap for training/validation within development AOIs. Split BEFORE
patch sampling or augmentation; overlapping views of a building stay in one split.
Never tune using final-test feedback and continue calling it an untouched test.

## Proposed controlled experiment

A. Repaired current production workflow, fixed configuration and all failures kept.
B. Small U-Net with lightweight encoder; alternatively SegFormer-B0 as a second
candidate, not an immediate dependency. Start with 256px patches, batch 1 and mixed
precision where supported. Benchmark peak VRAM and step time before a longer run.
Retain native GSD; choose larger context only after memory/cut-edge checks.
C. Best candidate's roof proposals/points followed by existing SAM2 refinement.

Optional later ablation: RGB vs RGB plus co-registered nDSM. Missing LiDAR is an
explicit input condition; evaluate an RGB path rather than silently filling
missing height data with meaningful-looking zeros. Do not import autonomous-driving
BEVFusion as if it directly solved airborne cadastral roof extraction.

Use learning-curve checkpoints, e.g. 100/200/400/800 unique building annotations
when available, with the same validation geography. These are experiment budgets,
not sufficient-data guarantees. Record separately the count of buildings, labeled
negative regions, image patches and unique geographic coverage. More crops from
the same roof do not equal more independent buildings.

Measure per-AOI object precision/recall, merge/split errors, missed small roofs,
mask IoU and boundary error in meters with suitable references. Count human
corrections/time as a product outcome. Sparse building-only references cannot
establish false-positive rates over an entire scene; densely annotate audit blocks.
Compare multiple seeds where feasible. Select checkpoints on validation performance,
not training loss. Record actual hardware, time, peak VRAM, dataset/checkpoint
hashes and configurations; do not promise runtime or accuracy before measurement.

Promote a model only if it improves the agreed baseline without unacceptable
merge/omission regressions. Keep rollback and the existing model available. ONNX
export/integration is a separate parity test, not proof of correct geometry.

## What Antigravity should do next

Repair Lot3 according to executable evaluation gates first. Then inventory clean
annotations and prepare a proposal for the dataset builder and spatial splits.
Implement training in an isolated environment after verifying package/checkpoint
compatibility and licenses. Do not install TAO, rent compute or train during a
research task. The next decision should be based on sample inventory and a small
memory benchmark, not assumed nationwide generalization from 12 square kilometers.
