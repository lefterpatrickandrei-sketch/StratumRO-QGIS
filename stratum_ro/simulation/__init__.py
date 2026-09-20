# -*- coding: utf-8 -*-
"""
Simulation and Perturbation Module for StratumRO.
Provides controlled geometric perturbations, sensor noise simulation,
and failure-case generation for robustness testing.
"""

from .perturbation import PerturbationConfig, PerturbationEngine

__all__ = ["PerturbationConfig", "PerturbationEngine"]
