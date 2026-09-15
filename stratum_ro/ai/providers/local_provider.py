# -*- coding: utf-8 -*-
"""
Local Deterministic & Mock Provider for StratumRO.
Guarantees 100% availability for offline, air-gapped, or test execution,
providing deterministic responses and structured fallback plans.
"""

import json
import time
from typing import Any, Dict, List, Optional
from .base import BaseAIProvider, ProviderCapability, ProviderResponse


class LocalProvider(BaseAIProvider):
    """
    Guaranteed local provider with deterministic mock templates.
    """

    def __init__(self, name: str = "local_mock"):
        super().__init__(name=name)

    def is_available(self) -> bool:
        return True

    def capabilities(self) -> List[ProviderCapability]:
        return [
            ProviderCapability.LOCAL_INFERENCE,
            ProviderCapability.PLANNING,
            ProviderCapability.REASONING,
        ]

    def list_models(self) -> List[str]:
        return ["deterministic-planner-v1", "offline-mock-engine"]

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
        timeout: float = 1.0,
        **kwargs
    ) -> ProviderResponse:
        t0 = time.time()
        chosen_model = model or "deterministic-planner-v1"

        ctx = context or {}
        siruta = ctx.get("siruta_code", 26573)
        proj_name = ctx.get("project_name", "StratumRO_Local")
        crs = ctx.get("crs", "EPSG:3844")

        # Standard deterministic plan in Stereo 70
        plan_dict = {
            "project_name": proj_name,
            "crs": crs,
            "pipeline_mode": "hybrid",
            "administrative": {
                "siruta_code": siruta,
                "name": ctx.get("locality_name", "Localitate_Implicit"),
                "county": ctx.get("county", "Romania")
            },
            "steps": [
                {"id": 1, "tool": "lidar.detect_candidates", "status": "planned"},
                {"id": 2, "tool": "segmentation.sam2", "status": "planned"},
                {"id": 3, "tool": "vectorizer.regularize", "status": "planned"},
                {"id": 4, "tool": "cadastral.validate", "status": "planned"}
            ],
            "fallback_engaged": True,
            "source": "local_deterministic_engine"
        }

        content_str = json.dumps(plan_dict, indent=2)
        elapsed = time.time() - t0

        return ProviderResponse(
            content=content_str,
            model_name=chosen_model,
            provider_name=self.name,
            status="fallback",
            duration_sec=round(elapsed, 4),
            parsed_json=plan_dict,
            usage={"tokens": 0, "cost": 0.0}
        )
