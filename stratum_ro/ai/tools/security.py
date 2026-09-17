# -*- coding: utf-8 -*-
"""
Security Sandbox & Permission Enforcement for StratumRO MCP Tools (MD 3).
Restricts filesystem operations to authorized repository subdirectories
and implements the ALLOW / SAFE_WRITE / ASK / DENY permission hierarchy.
"""

import sys
import re
import tempfile
from enum import Enum
from pathlib import Path
from typing import List, Optional, Tuple

# Base repository root directory
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SYSTEM_TEMP = Path(tempfile.gettempdir()).resolve()

# Allowed sandboxed directory roots
ALLOWED_ROOTS = [
    REPO_ROOT / "workspace",
    REPO_ROOT / "data",
    REPO_ROOT / "reports",
    REPO_ROOT / "tests",
    SYSTEM_TEMP,
]


class PermissionClass(str, Enum):
    ALLOW = "ALLOW"            # Read-only inspection / queries
    SAFE_WRITE = "SAFE_WRITE"  # Non-authoritative / preview writes
    ASK = "ASK"                # Official cadastral commit or CAD export
    DENY = "DENY"              # Arbitrary shell/python code execution


# Tool permission assignments
TOOL_PERMISSIONS = {
    # Project & Context
    "project.get_context": PermissionClass.ALLOW,
    "project.get_aoi": PermissionClass.ALLOW,
    "layers.list": PermissionClass.ALLOW,
    "layers.inspect": PermissionClass.ALLOW,
    "context.get": PermissionClass.ALLOW,
    "context.get_aoi": PermissionClass.ALLOW,
    "context.get_layers": PermissionClass.ALLOW,
    "context.get_inputs": PermissionClass.ALLOW,

    # Session Memory Queries (Read-only)
    "memory.get_recent_runs": PermissionClass.ALLOW,
    "memory.get_task_history": PermissionClass.ALLOW,
    "memory.search": PermissionClass.ALLOW,

    # Raster & LiDAR
    "raster.inspect": PermissionClass.ALLOW,
    "raster.extract_chip": PermissionClass.SAFE_WRITE,
    "lidar.inspect": PermissionClass.ALLOW,
    "lidar.generate_ndsm": PermissionClass.SAFE_WRITE,

    # Segmentation
    "segmentation.run_sam2": PermissionClass.SAFE_WRITE,
    "segmentation.inspect_mask": PermissionClass.ALLOW,

    # Vector
    "vector.regularize": PermissionClass.SAFE_WRITE,
    "vector.apply_eave_offset": PermissionClass.SAFE_WRITE,
    "vector.planar_partition": PermissionClass.SAFE_WRITE,

    # Validation & Evaluation
    "geometry.validate_topology": PermissionClass.ALLOW,
    "cadastral.validate_ancpi": PermissionClass.ALLOW,
    "evaluation.compare_ground_truth": PermissionClass.ALLOW,

    # Results & Previews
    "results.create_preview": PermissionClass.SAFE_WRITE,
    "results.commit_to_project": PermissionClass.ASK,

    # Authoritative Exports
    "export.export_gpkg": PermissionClass.SAFE_WRITE,
    "export.export_topolt_dxf": PermissionClass.ASK,
    "export.export_cp": PermissionClass.ASK,
    "export.export_cityjson": PermissionClass.SAFE_WRITE,
}


def resolve_sandboxed_path(
    user_path: str = "",
    must_exist: bool = False,
    allow_creation: bool = True
) -> Path:
    """
    Resolves and validates that a given path stays within authorized project boundaries.
    Prevents path traversal attacks (e.g. '../../etc/passwd' or 'C:\\Windows').
    Raises PermissionError or ValueError if the path escapes the sandbox.
    """
    if user_path is None:
        raise ValueError("Path cannot be None.")

    path_str = str(user_path).strip()
    if not path_str or path_str == ".":
        resolved = REPO_ROOT
    else:
        # Block Windows-style drive paths on POSIX systems where Path.is_absolute() evaluates to False
        if re.match(r"^[a-zA-Z]:", path_str) and sys.platform != "win32":
            raise PermissionError(f"Access denied: Windows-style path '{user_path}' escapes the authorized project workspace sandbox.")
        p = Path(path_str)
        if p.is_absolute():
            resolved = p.resolve()
        else:
            resolved = (REPO_ROOT / p).resolve()

    # Check against allowed roots or repo root
    is_allowed = False
    if resolved == REPO_ROOT or resolved.is_relative_to(REPO_ROOT) or resolved.is_relative_to(SYSTEM_TEMP):
        # Additional check: block sensitive system files within repo (.git/config, .env)
        if ".env" in resolved.name.lower() or ".git" in resolved.parts:
            raise PermissionError(f"Access to sensitive file '{resolved.name}' is strictly denied.")
        is_allowed = True

    if not is_allowed:
        raise PermissionError(
            f"Access denied: path '{user_path}' escapes the authorized project workspace sandbox."
        )

    if must_exist and not resolved.exists():
        raise FileNotFoundError(f"Requested file does not exist: {resolved}")

    if allow_creation and not resolved.parent.exists():
        resolved.parent.mkdir(parents=True, exist_ok=True)

    return resolved


def check_permission(
    tool_name: str,
    approved: bool = False,
    approval_reason: str = ""
) -> Tuple[bool, str]:
    """
    Verifies execution permission for a given MCP tool.
    Returns (is_permitted, status_message).
    """
    perm = TOOL_PERMISSIONS.get(tool_name, PermissionClass.DENY)

    if perm == PermissionClass.DENY:
        return False, f"Permission DENIED: Tool '{tool_name}' is not authorized."

    if perm in {PermissionClass.ALLOW, PermissionClass.SAFE_WRITE}:
        return True, f"Permission granted ({perm.value})."

    if perm == PermissionClass.ASK:
        if approved:
            reason_log = f" [Reason: {approval_reason}]" if approval_reason else ""
            return True, f"Permission granted with user approval{reason_log}."
        return False, (
            f"Permission ASK: Tool '{tool_name}' requires explicit human-in-the-loop approval. "
            f"Action paused in waiting_for_approval state."
        )

    return False, "Unknown permission class."
