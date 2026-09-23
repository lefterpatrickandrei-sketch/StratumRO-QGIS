# -*- coding: utf-8 -*-
"""
StratumRO — Core Geodesy: Coordinate Transformations (Phase 3)
Implementation of the ITransformer contract.
Pure-Python, deterministic PROJ/pyproj transformations. Zero LLM authority.
"""

from typing import List, Tuple, Optional
import pyproj

from stratum_ro.contracts.geodesy import ITransformer


class CoreTransformer(ITransformer):
    """
    Standard deterministic coordinate transformer wrapping pyproj.Transformer.
    Strictly enforces always_xy=True to eliminate Cartesian axis flipping.
    """

    def __init__(self, source_crs: str, target_crs: str):
        self._source_crs = str(source_crs).strip()
        self._target_crs = str(target_crs).strip()
        # Initialize pyproj transformer with always_xy=True
        self._transformer = pyproj.Transformer.from_crs(
            self._source_crs,
            self._target_crs,
            always_xy=True
        )

    @property
    def source_crs(self) -> str:
        return self._source_crs

    @property
    def target_crs(self) -> str:
        return self._target_crs

    def transform_point(self, x: float, y: float, z: float = 0.0) -> Tuple[float, float, float]:
        """Transforms a 2D or 3D point from source_crs to target_crs."""
        if z != 0.0:
            tx, ty, tz = self._transformer.transform(x, y, z)
            return (float(tx), float(ty), float(tz))
        else:
            tx, ty = self._transformer.transform(x, y)
            return (float(tx), float(ty), 0.0)

    def transform_coordinates(self, coordinates: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """Transforms a sequence of 2D coordinates."""
        if not coordinates:
            return []
        xs = [c[0] for c in coordinates]
        ys = [c[1] for c in coordinates]
        txs, tys = self._transformer.transform(xs, ys)
        return [(float(x), float(y)) for x, y in zip(txs, tys)]
