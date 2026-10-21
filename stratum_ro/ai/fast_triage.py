# -*- coding: utf-8 -*-
"""
stratum_ro/ai/fast_triage.py - System 1 Fast Triage Engine (<35ms CPU / Edge)

Performs deterministic, ultra-fast pre-screening of building candidates using
geometric compactness, altimetric LiDAR nDSM profiles, and orthophoto contrast.
Clearly valid buildings are APPROVED instantly; obvious noise/pavements are REJECTED;
complex, ambiguous, or calcan boundary cases are flagged UNCERTAIN for VLM escalation.
"""

from dataclasses import dataclass, field
import time
from typing import Any, Dict, List, Optional
import numpy as np
from shapely.geometry import Polygon, shape


@dataclass
class FastTriageVerdict:
    status: str  # "APPROVED", "REJECTED", "UNCERTAIN"
    confidence: float
    reason: str
    escalate_to_vlm: bool
    latency_ms: float
    metrics: Dict[str, Any] = field(default_factory=dict)


class FastTriageEngine:
    """
    System 1 triage classifier running entirely on local CPU with sub-35ms latency.
    """

    def __init__(
        self,
        min_annex_area: float = 8.0,
        min_main_area: float = 45.0,
        min_building_height_m: float = 2.2,
        min_solidity_approval: float = 0.80,
        max_aspect_ratio: float = 7.0,
    ):
        self.min_annex_area = min_annex_area
        self.min_main_area = min_main_area
        self.min_building_height_m = min_building_height_m
        self.min_solidity_approval = min_solidity_approval
        self.max_aspect_ratio = max_aspect_ratio

    def evaluate_candidate(
        self,
        geometry: Any,
        attributes: Optional[Dict[str, Any]] = None,
        image_chip: Optional[np.ndarray] = None,
    ) -> FastTriageVerdict:
        """
        Evaluates a single building candidate geometry and associated attributes.
        """
        t0 = time.perf_counter()
        attrs = attributes or {}

        # 1. Convert geometry
        if isinstance(geometry, dict):
            geom = shape(geometry)
        else:
            geom = geometry

        if geom is None or geom.is_empty:
            latency = (time.perf_counter() - t0) * 1000.0
            return FastTriageVerdict(
                status="REJECTED",
                confidence=1.0,
                reason="Empty or null geometry",
                escalate_to_vlm=False,
                latency_ms=latency,
            )

        area = float(geom.area)

        # Calculate bounding box & aspect ratio
        minx, miny, maxx, maxy = geom.bounds
        width = max(maxx - minx, 1e-6)
        height = max(maxy - miny, 1e-6)
        aspect_ratio = max(width / height, height / width)

        # Convex hull solidity
        hull_area = geom.convex_hull.area
        solidity = float(area / max(hull_area, 1e-6))

        # Height properties from attributes (nDSM LiDAR)
        h_mean = float(attrs.get("h_mean", attrs.get("height_mean", 0.0)))
        h_max = float(attrs.get("h_max", attrs.get("height_max", 0.0)))
        has_calcan = bool(attrs.get("has_calcan", False))
        mean_contrast = float(attrs.get("mean_contrast", 0.5))

        metrics = {
            "area_m2": round(area, 2),
            "solidity": round(solidity, 3),
            "aspect_ratio": round(aspect_ratio, 2),
            "h_mean": round(h_mean, 2),
            "h_max": round(h_max, 2),
            "has_calcan": has_calcan,
            "mean_contrast": round(mean_contrast, 3),
        }

        # --- RULE 1: HARD REJECTIONS (Noise, Pavements, Slivers) ---
        if area < self.min_annex_area:
            latency = (time.perf_counter() - t0) * 1000.0
            return FastTriageVerdict(
                status="REJECTED",
                confidence=0.95,
                reason=f"Area ({area:.1f} m2) below legal ANCPI annex minimum ({self.min_annex_area} m2)",
                escalate_to_vlm=False,
                latency_ms=latency,
                metrics=metrics,
            )

        if aspect_ratio > self.max_aspect_ratio:
            latency = (time.perf_counter() - t0) * 1000.0
            return FastTriageVerdict(
                status="REJECTED",
                confidence=0.92,
                reason=f"Extreme aspect ratio ({aspect_ratio:.1f}) indicates road/curb artifact",
                escalate_to_vlm=False,
                latency_ms=latency,
                metrics=metrics,
            )

        if h_max > 0.0 and h_max < 1.6 and h_mean < 1.4:
            # Verified ground pavement / patio / shadow
            latency = (time.perf_counter() - t0) * 1000.0
            return FastTriageVerdict(
                status="REJECTED",
                confidence=0.91,
                reason=f"Altimetric height (max {h_max:.1f}m, mean {h_mean:.1f}m) confirms ground-level feature",
                escalate_to_vlm=False,
                latency_ms=latency,
                metrics=metrics,
            )

        # --- RULE 2: AMBIGUITY -> UNCERTAIN (Escalate to VLM) ---
        # Calcan party walls need visual context verification
        if has_calcan:
            latency = (time.perf_counter() - t0) * 1000.0
            return FastTriageVerdict(
                status="UNCERTAIN",
                confidence=0.60,
                reason="Party wall (calcan) contact detected; requires visual audit",
                escalate_to_vlm=True,
                latency_ms=latency,
                metrics=metrics,
            )

        # Low solidity with large area indicates complex courtyards or split wings
        if solidity < 0.65 and area > 60.0:
            latency = (time.perf_counter() - t0) * 1000.0
            return FastTriageVerdict(
                status="UNCERTAIN",
                confidence=0.55,
                reason=f"Low compactness/solidity ({solidity:.2f}) suggests courtyard or multi-wing ambiguity",
                escalate_to_vlm=True,
                latency_ms=latency,
                metrics=metrics,
            )

        # Borderline altimetric profile
        if 0.0 < h_max < self.min_building_height_m:
            latency = (time.perf_counter() - t0) * 1000.0
            return FastTriageVerdict(
                status="UNCERTAIN",
                confidence=0.50,
                reason=f"Borderline height ({h_max:.1f}m); requires semantic confirmation",
                escalate_to_vlm=True,
                latency_ms=latency,
                metrics=metrics,
            )

        # --- RULE 3: CLEAR APPROVALS ---
        if area >= self.min_main_area and (h_mean >= 2.5 or h_max >= 3.0) and solidity >= self.min_solidity_approval:
            latency = (time.perf_counter() - t0) * 1000.0
            return FastTriageVerdict(
                status="APPROVED",
                confidence=0.94,
                reason="Detached main building with solid roof envelope and confirmed LiDAR height",
                escalate_to_vlm=False,
                latency_ms=latency,
                metrics=metrics,
            )

        if area >= self.min_annex_area and solidity >= 0.85 and (h_mean >= 2.2 or h_max >= 2.5):
            latency = (time.perf_counter() - t0) * 1000.0
            return FastTriageVerdict(
                status="APPROVED",
                confidence=0.89,
                reason="Regular compact outbuilding/annex with confirmed elevation",
                escalate_to_vlm=False,
                latency_ms=latency,
                metrics=metrics,
            )

        # Fallback for remaining cases
        latency = (time.perf_counter() - t0) * 1000.0
        return FastTriageVerdict(
            status="UNCERTAIN",
            confidence=0.50,
            reason="Heuristic thresholds inconclusive; escalating to VLM Describe-First audit",
            escalate_to_vlm=True,
            latency_ms=latency,
            metrics=metrics,
        )

    def evaluate_batch(
        self,
        features: List[Dict[str, Any]],
    ) -> List[FastTriageVerdict]:
        """
        Evaluates a batch of features sequentially, returning verdicts and summary.
        """
        return [
            self.evaluate_candidate(
                geometry=f.get("geometry"),
                attributes=f.get("properties", f),
            )
            for f in features
        ]
