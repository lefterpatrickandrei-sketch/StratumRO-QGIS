# -*- coding: utf-8 -*-
"""
StratumRO API Subsystem.
Provides a REST and SSE FastAPI backend for the StratumRO Geospatial Platform,
bridging the Web Cockpit, QGIS Desktop, deterministic math engine, and AI providers.
"""

from .app import app

__all__ = ["app"]
