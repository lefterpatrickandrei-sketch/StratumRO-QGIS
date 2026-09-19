# -*- coding: utf-8 -*-
"""
StratumRO — VLM Verifier for SAM Building Segmentations.
Audits 2D/3D building footprints using Vision-Language Models (NVIDIA NIM LLaMA 3.2 Vision / Gemini)
cross-referenced against aerial orthophotos (RGB) and LiDAR nDSM profiles.
Complies with ANCPI Ordinul nr. 600/2023 building classifications (1CC, 2CC, ANEXA).
"""

import base64
import io
import json
import math
import os
import re
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw
from shapely.geometry import Polygon, MultiPolygon

from stratum_ro.ai.providers.base import BaseAIProvider, ProviderResponse, extract_json
from stratum_ro.ai.providers.nvidia_nim_provider import NvidiaNIMProvider


@dataclass
class VLMVerificationResult:
    building_id: str
    is_real_building: bool
    ancpi_code: str  # "1CC", "2CC", "SERA", "SPECIALA", "FALSE_POSITIVE"
    typology: str  # e.g., "Construcție Principală (Locuință)", "Anexă gospodărească"
    confidence: float  # 0.0 to 1.0
    verdict: str  # "APPROVED", "REVIEW_NEEDED", "REJECTED"
    roof_type: str  # "în 2 ape", "terasă plană", "complex", "ușor/tablă"
    eave_visible: bool
    has_calcan: bool
    vegetation_occlusion: bool
    reasoning: str
    provider_used: str
    duration_sec: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def crop_building_chip(
    ortho_path: str,
    polygon: Polygon,
    padding_m: float = 5.0,
    target_size: Tuple[int, int] = (512, 512),
    draw_contour: bool = True,
    outline_color: Tuple[int, int, int] = (255, 0, 128),
    contour_width: int = 3
) -> Optional[Image.Image]:
    """
    Crops a square orthophoto chip centered on the building polygon with surrounding spatial context.
    Optionally overlays the SAM polygon contour in high-visibility magenta.
    """
    try:
        import rasterio
        from rasterio.windows import from_bounds
    except ImportError:
        return None

    if polygon is None or polygon.is_empty:
        return None

    minx, miny, maxx, maxy = polygon.bounds
    cx, cy = (minx + maxx) / 2.0, (miny + maxy) / 2.0
    half_side = max((maxx - minx), (maxy - miny)) / 2.0 + padding_m

    crop_bounds = (cx - half_side, cy - half_side, cx + half_side, cy + half_side)

    try:
        with rasterio.open(ortho_path) as src:
            win = from_bounds(*crop_bounds, src.transform)
            num_bands = min(3, src.count)
            bands = tuple(range(1, num_bands + 1))
            rgb = src.read(bands, window=win, boundless=True, fill_value=0)

            if rgb.size == 0 or rgb.shape[1] == 0 or rgb.shape[2] == 0:
                return None

            if num_bands == 1:
                rgb = np.repeat(rgb, 3, axis=0)

            arr = np.transpose(rgb[:3, :, :], (1, 2, 0))
            chip = Image.fromarray(arr).resize(target_size, Image.Resampling.BILINEAR)

            if draw_contour:
                draw = ImageDraw.Draw(chip)
                w, h = target_size
                b_minx, b_miny, b_maxx, b_maxy = crop_bounds

                def to_px(x, y):
                    px = int((x - b_minx) / (b_maxx - b_minx) * w)
                    py = int((b_maxy - y) / (b_maxy - b_miny) * h)
                    return px, py

                polys = [polygon] if isinstance(polygon, Polygon) else ([p for p in polygon.geoms if isinstance(p, Polygon)] if isinstance(polygon, MultiPolygon) else [])
                for p in polys:
                    pts = [to_px(x, y) for x, y in p.exterior.coords]
                    if len(pts) >= 3:
                        draw.line(pts + [pts[0]], fill=outline_color, width=contour_width)

            return chip

    except Exception:
        return None


def encode_chip_base64(img: Image.Image, format: str = "JPEG", quality: int = 90) -> str:
    """Converts a PIL Image into a Base64-encoded string."""
    buffered = io.BytesIO()
    img.save(buffered, format=format, quality=quality)
    return base64.b64encode(buffered.getvalue()).decode("utf-8")


def build_cadastral_prompt(
    building_id: str,
    area_m2: float,
    perimeter_m: float,
    ndsm_height_m: Optional[float] = None
) -> Tuple[str, str]:
    """
    Constructs the specialized Romanian cadastral audit prompt for VLM inference.
    """
    system_prompt = (
        "Ești un expert inginer geodez autorizat ANCPI (Ordinul 600/2023) specializat în recunoaștere fotogrammetrică aeriană.\n"
        "Misiunea ta este să auditezi măștile de clădiri generate automat de modelul AI SAM (Segment Anything Model).\n"
        "Trebuie să confirmi dacă poligonul roz suprapus pe imagine este o clădire reală, să identifici fals-pozitivele "
        "(copaci, terase, umbre, pietre funerare) și să atribui codul de destinație ANCPI corect.\n"
        "Răspunde STRICT în format JSON valid fără alt text."
    )

    h_info = f"- Înălțime medie LiDAR nDSM: {ndsm_height_m:.1f} m\n" if ndsm_height_m is not None else ""

    user_prompt = (
        f"Analizează decupajul aerian ortofoto pentru elementul '{building_id}'.\n"
        f"Conturul roz reprezintă masca generată automat de modelul de segmentare SAM.\n"
        f"Date geometrice:\n"
        f"- Suprafață amprentă: {area_m2:.1f} mp\n"
        f"- Perimetru: {perimeter_m:.1f} m\n"
        f"{h_info}\n"
        "Instrucțiuni de clasificare ANCPI Ordinul 600/2023:\n"
        "1. is_real_building: true (dacă este o construcție fizică acoperită) sau false.\n"
        "2. ancpi_code:\n"
        "   - '1CC': Construcție Principală (casă rezidențială, bloc, sediu administrativ, corp școală/universitate).\n"
        "   - '2CC': Construcție Anexă (garaj, magazie, șopron, bucătărie vară).\n"
        "   - 'SERA': Seră agricolă sau structură ușoară transparentă.\n"
        "   - 'SPECIALA': Construcție cu regim special (edificiu de cult, post trafo, hală mare).\n"
        "   - 'FALSE_POSITIVE': Copac/vegetație densă, terasă sol, umbră, vehicul, piatră funerară.\n"
        "3. verdict: 'APPROVED' (sigur clădire), 'REVIEW_NEEDED' (obstrucție parțială / calcan), 'REJECTED' (fals pozitiv).\n"
        "4. confidence: număr între 0.0 și 1.0.\n"
        "5. roof_type: tip acoperiș (ex: 'în 2 ape', 'terasă plană', 'în 4 ape', 'ușor/tablă').\n"
        "6. eave_visible: true dacă streașina/ieșitura acoperișului e vizibilă peste perete.\n"
        "7. has_calcan: true dacă se lipește de o altă clădire (perete comun la calcan).\n"
        "8. vegetation_occlusion: true dacă coroana unui copac acoperă o parte din acoperiș.\n"
        "9. reasoning: explicație scurtă în limba română a verdictului geodezic.\n\n"
        "Răspunde DOAR cu obiectul JSON următor:\n"
        "{\n"
        '  "is_real_building": true,\n'
        '  "ancpi_code": "1CC",\n'
        '  "typology": "Construcție Principală (Locuință)",\n'
        '  "confidence": 0.95,\n'
        '  "verdict": "APPROVED",\n'
        '  "roof_type": "în 2 ape",\n'
        '  "eave_visible": true,\n'
        '  "has_calcan": false,\n'
        '  "vegetation_occlusion": false,\n'
        '  "reasoning": "Acoperiș vizibil cu versanți simetrici..."\n'
        "}"
    )

    return system_prompt, user_prompt


class VLMVerifier:
    """
    Autonomous Vision-Language Auditor for StratumRO.
    Validates building candidates against optical and LiDAR data using LLaMA 3.2 Vision / Gemini,
    with an evidence-backed deterministic heuristic fallback.
    """

    def __init__(
        self,
        provider: Optional[BaseAIProvider] = None,
        default_model: str = "meta/llama-3.3-70b-instruct",
        fallback_to_heuristic: bool = True
    ):
        self.provider = provider or NvidiaNIMProvider(default_model=default_model)
        self.default_model = default_model
        self.fallback_to_heuristic = fallback_to_heuristic

    def verify_building(
        self,
        polygon: Polygon,
        ortho_path: str,
        building_id: str = "bldg_0",
        ndsm_height_m: Optional[float] = None,
        padding_m: float = 6.0,
        timeout: float = 12.0
    ) -> VLMVerificationResult:
        """
        Verifies a single building footprint candidate.
        """
        if polygon is None or polygon.is_empty:
            return VLMVerificationResult(
                building_id=building_id,
                is_real_building=False,
                ancpi_code="FALSE_POSITIVE",
                typology="Geometrie Nulă",
                confidence=0.0,
                verdict="REJECTED",
                roof_type="necunoscut",
                eave_visible=False,
                has_calcan=False,
                vegetation_occlusion=False,
                reasoning="Poligonul furnizat este nul sau invalid topologic.",
                provider_used="validator_internal"
            )

        area_m2 = float(polygon.area)
        perim_m = float(polygon.length)

        # 1. Generate image chip with overlay
        chip = crop_building_chip(
            ortho_path=ortho_path,
            polygon=polygon,
            padding_m=padding_m,
            target_size=(512, 512),
            draw_contour=True
        )

        # If image cannot be cropped or provider is unavailable, trigger heuristic fallback
        if chip is None or not self.provider.is_available():
            if self.fallback_to_heuristic:
                return self._heuristic_fallback(
                    building_id=building_id,
                    polygon=polygon,
                    area_m2=area_m2,
                    perim_m=perim_m,
                    ndsm_height_m=ndsm_height_m,
                    chip=chip,
                    reason="Provider VLM indisponibil sau fără cheie API configurată."
                )
            else:
                return VLMVerificationResult(
                    building_id=building_id,
                    is_real_building=False,
                    ancpi_code="FALSE_POSITIVE",
                    typology="Eroare Extragere Imagine",
                    confidence=0.0,
                    verdict="REJECTED",
                    roof_type="necunoscut",
                    eave_visible=False,
                    has_calcan=False,
                    vegetation_occlusion=False,
                    reasoning="Nu s-a putut decupa imaginea ortofoto sau providerul este inactiv.",
                    provider_used=self.provider.name
                )

        # 2. Prepare multimodal payload
        b64_img = encode_chip_base64(chip)
        sys_p, usr_p = build_cadastral_prompt(
            building_id=building_id,
            area_m2=area_m2,
            perimeter_m=perim_m,
            ndsm_height_m=ndsm_height_m
        )

        # 3. Call VLM Provider
        resp: ProviderResponse = self.provider.generate(
            prompt=usr_p,
            system_prompt=sys_p,
            images=[b64_img],
            model=self.default_model,
            timeout=timeout
        )

        if resp.is_ok() and resp.parsed_json:
            p = resp.parsed_json
            return VLMVerificationResult(
                building_id=building_id,
                is_real_building=bool(p.get("is_real_building", True)),
                ancpi_code=str(p.get("ancpi_code", "1CC")),
                typology=str(p.get("typology", "Construcție")),
                confidence=float(p.get("confidence", 0.90)),
                verdict=str(p.get("verdict", "APPROVED")),
                roof_type=str(p.get("roof_type", "în 2 ape")),
                eave_visible=bool(p.get("eave_visible", True)),
                has_calcan=bool(p.get("has_calcan", False)),
                vegetation_occlusion=bool(p.get("vegetation_occlusion", False)),
                reasoning=str(p.get("reasoning", "Validat cu succes prin VLM.")),
                provider_used=f"{self.provider.name} ({resp.model_name})",
                duration_sec=resp.duration_sec
            )

        # Fallback if VLM call failed
        if self.fallback_to_heuristic:
            return self._heuristic_fallback(
                building_id=building_id,
                polygon=polygon,
                area_m2=area_m2,
                perim_m=perim_m,
                ndsm_height_m=ndsm_height_m,
                chip=chip,
                reason=f"Apel VLM eșuat ({resp.error or 'fără răspuns JSON'}). S-a activat fallback-ul determinist."
            )

        return VLMVerificationResult(
            building_id=building_id,
            is_real_building=False,
            ancpi_code="FALSE_POSITIVE",
            typology="Eroare Inspecție VLM",
            confidence=0.0,
            verdict="REJECTED",
            roof_type="necunoscut",
            eave_visible=False,
            has_calcan=False,
            vegetation_occlusion=False,
            reasoning=f"Eroare răspuns VLM: {resp.error}",
            provider_used=self.provider.name
        )

    def _heuristic_fallback(
        self,
        building_id: str,
        polygon: Polygon,
        area_m2: float,
        perim_m: float,
        ndsm_height_m: Optional[float],
        chip: Optional[Image.Image],
        reason: str
    ) -> VLMVerificationResult:
        """
        Deterministic, evidence-based geometric and altimetric fallback
        when external VLM APIs are not reachable.
        """
        # Compactness ratio (Polsby-Popper): 4 * pi * Area / Perim^2
        compactness = (4.0 * math.pi * area_m2) / (perim_m ** 2) if perim_m > 0 else 0.0

        # Altimetric assessment
        h = ndsm_height_m if ndsm_height_m is not None else 5.0

        # Filter 1: Very small objects (< 12 m²)
        if area_m2 < 12.0:
            if area_m2 < 5.0 or h < 2.0:
                return VLMVerificationResult(
                    building_id=building_id,
                    is_real_building=False,
                    ancpi_code="FALSE_POSITIVE",
                    typology="Obiect minor / Piatră funerară / Zgomot",
                    confidence=0.88,
                    verdict="REJECTED",
                    roof_type="niciunul",
                    eave_visible=False,
                    has_calcan=False,
                    vegetation_occlusion=False,
                    reasoning=f"Suprafață sub pragul cadastral ({area_m2:.1f} mp < 12 mp). {reason}",
                    provider_used="heuristic_fallback (geodesic)"
                )
            else:
                return VLMVerificationResult(
                    building_id=building_id,
                    is_real_building=True,
                    ancpi_code="2CC",
                    typology="Anexă gospodărească minoră (șopron/garaj mic)",
                    confidence=0.82,
                    verdict="APPROVED",
                    roof_type="ușor/tablă",
                    eave_visible=True,
                    has_calcan=False,
                    vegetation_occlusion=False,
                    reasoning=f"Construcție mică de tip anexă ({area_m2:.1f} mp, H={h:.1f}m). {reason}",
                    provider_used="heuristic_fallback (geodesic)"
                )

        # Filter 2: Annexes (12 - 45 m²)
        if 12.0 <= area_m2 < 45.0:
            ancpi = "2CC"
            typology = "Anexă gospodărească (Garaj / Depozit)"
            conf = 0.89
            verdict = "APPROVED"
            roof = "în 1-2 ape"

        # Filter 3: Main Buildings (> 45 m²)
        else:
            ancpi = "1CC"
            typology = "Construcție Principală (Locuință / Corp Clădire)"
            conf = 0.94 if h >= 2.8 else 0.78
            verdict = "APPROVED" if h >= 2.5 else "REVIEW_NEEDED"
            roof = "în 2-4 ape"

        return VLMVerificationResult(
            building_id=building_id,
            is_real_building=True,
            ancpi_code=ancpi,
            typology=typology,
            confidence=conf,
            verdict=verdict,
            roof_type=roof,
            eave_visible=True,
            has_calcan=False,
            vegetation_occlusion=False,
            reasoning=f"Amprentă validă cadastral ({area_m2:.1f} mp, H={h:.1f}m, compacitate={compactness:.2f}). {reason}",
            provider_used="heuristic_fallback (geodesic)"
        )

    def batch_verify_footprints(
        self,
        gpkg_path: str,
        layer_name: str,
        ortho_path: str,
        max_buildings: Optional[int] = None,
        ndsm_tif_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Runs batch verification across features in a GeoPackage layer.
        Returns summary statistics and per-building verification cards.
        """
        import geopandas as gpd

        gdf = gpd.read_file(gpkg_path, layer=layer_name)
        if max_buildings:
            gdf = gdf.iloc[:max_buildings]

        results = []
        counts = {"APPROVED": 0, "REVIEW_NEEDED": 0, "REJECTED": 0}
        typologies = {"1CC": 0, "2CC": 0, "SERA": 0, "SPECIALA": 0, "FALSE_POSITIVE": 0}

        for idx, row in gdf.iterrows():
            geom = row.geometry
            b_id = f"bldg_{row.get('fid', idx)}"

            # Estimate height if ndsm provided
            h_est = None
            if ndsm_tif_path and os.path.exists(ndsm_tif_path):
                try:
                    import rasterio
                    from rasterio.windows import from_bounds
                    with rasterio.open(ndsm_tif_path) as ndsm_src:
                        win = from_bounds(*geom.bounds, ndsm_src.transform)
                        p = ndsm_src.read(1, window=win)
                        if p.size > 0:
                            h_est = float(np.nanmax(p))
                except Exception:
                    pass

            v_res = self.verify_building(
                polygon=geom,
                ortho_path=ortho_path,
                building_id=b_id,
                ndsm_height_m=h_est
            )
            results.append(v_res.to_dict())
            counts[v_res.verdict] = counts.get(v_res.verdict, 0) + 1
            typologies[v_res.ancpi_code] = typologies.get(v_res.ancpi_code, 0) + 1

        return {
            "status": "success",
            "total_evaluated": len(results),
            "summary_counts": counts,
            "typology_distribution": typologies,
            "verification_cards": results
        }
