# Vision Domain Pack

**Domain:** Computer Vision & Optical Building Footprint Delineation  
**Frameworks:** Meta Segment Anything Model 2 (SAM2 Hiera), ONNX Runtime DirectML  
**Maturity:** `MATURE`

## Capabilities
- `optical_candidate_generation`: Centroid and bounding box proposal from orthophoto chips.
- `sam2_onnx_segmentation`: DirectML/CPU accelerated ViT image encoder and mask decoder inference.
- `mask_fusion`: Consensus voting and confidence weighting across multiple overlapping chips.
- `vegetation_filtering`: Optical-spectral and height-based masking to eliminate false canopy detections.
