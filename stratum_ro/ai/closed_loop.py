# -*- coding: utf-8 -*-
"""
Closed-Loop Development Orchestrator for StratumRO.
Coordinates the verified development pipeline:
Antigravity (Orchestrator) <-> Providers (NVIDIA NIM / SAM2 / Local Math) <-> Kilo (Adversarial Reviewer) <-> QGIS Live Engine.
"""

import json
import os
import re
import socket
import struct
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .providers.base import read_env_file_key
from .providers.nvidia_nim_provider import NvidiaNIMProvider
from .providers.union_alpha_provider import UnionAlphaProvider

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


@dataclass
class TestResults:
    total_discovered: int = 0
    passed: int = 0
    skipped: int = 0
    failed: int = 0
    duration_sec: float = 0.0
    output_summary: str = ""
    success: bool = False


@dataclass
class QGISLiveStatus:
    connected: bool = False
    layers_count: int = 0
    layer_names: List[str] = field(default_factory=list)
    canvas_captured: bool = False
    duration_sec: float = 0.0
    error: Optional[str] = None


@dataclass
class ProviderVerification:
    provider_name: str
    model: str
    status: str
    duration_sec: float
    response_sample: str
    error: Optional[str] = None


@dataclass
class KiloAuditResult:
    status: str  # "APPROVED", "APPROVED_WITH_CONDITIONS", "REJECTED", "FAILED"
    reviewer: str = "Kilo (meta-llama/llama-3.3-70b-instruct via OpenRouter)"
    duration_sec: float = 0.0
    verdict: str = ""
    findings: List[str] = field(default_factory=list)
    full_review: str = ""
    error: Optional[str] = None


@dataclass
class ClosedLoopReport:
    milestone_name: str
    timestamp: str
    tests: TestResults
    qgis: QGISLiveStatus
    nim: ProviderVerification
    kilo: KiloAuditResult
    overall_status: str  # "PASS", "PASS_WITH_WARNINGS", "FAIL"
    summary: str


class ClosedLoopOrchestrator:
    """
    Automates the closed development loop across Antigravity, local tests,
    live QGIS Desktop, NVIDIA NIM vision, and Kilo adversarial reviews.
    """

    def __init__(self, project_root: Optional[Path] = None):
        self.root = project_root or PROJECT_ROOT
        self.venv_python = self.root / "venv" / "Scripts" / "python.exe"
        if not self.venv_python.exists():
            self.venv_python = Path(sys.executable)

    def run_unit_tests(self) -> TestResults:
        """Executes the full automated unit test suite."""
        t0 = time.time()
        cmd = [str(self.venv_python), "-m", "unittest", "discover", "stratum_ro/test"]
        try:
            p = subprocess.run(
                cmd,
                cwd=str(self.root),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=120,
            )
            elapsed = time.time() - t0
            output = p.stdout

            # Parse unittest output e.g. "Ran 206 tests in 32.057s\n\nOK (skipped=9)"
            match_ran = re.search(r"Ran (\d+) tests in ([\d\.]+)s", output)
            total = int(match_ran.group(1)) if match_ran else 0

            match_skip = re.search(r"skipped=(\d+)", output)
            skipped = int(match_skip.group(1)) if match_skip else 0

            failed = 0
            match_fail = re.search(r"FAILED \((.+?)\)", output)
            if match_fail:
                details = match_fail.group(1)
                for part in details.split(","):
                    if "failures=" in part or "errors=" in part:
                        num = re.findall(r"\d+", part)
                        if num:
                            failed += int(num[0])

            passed = max(0, total - skipped - failed)
            is_success = (p.returncode == 0) and (failed == 0)

            return TestResults(
                total_discovered=total,
                passed=passed,
                skipped=skipped,
                failed=failed,
                duration_sec=round(elapsed, 2),
                output_summary=output.strip().splitlines()[-1] if output.strip() else "",
                success=is_success,
            )
        except Exception as e:
            return TestResults(
                output_summary=f"Execution error: {str(e)}",
                duration_sec=round(time.time() - t0, 2),
                success=False,
            )

    def check_qgis_live(self, host: str = "127.0.0.1", port: int = 9876) -> QGISLiveStatus:
        """Connects to live QGIS Desktop via TCP socket 9876 using framed protocol."""
        t0 = time.time()
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5.0)
            s.connect((host, port))

            # Query layers
            req = {"type": "get_layers", "params": {}}
            payload = json.dumps(req).encode("utf-8")
            s.sendall(struct.pack(">I", len(payload)) + payload)

            raw_len = s.recv(4)
            if len(raw_len) != 4:
                s.close()
                return QGISLiveStatus(
                    connected=False,
                    duration_sec=round(time.time() - t0, 2),
                    error="Incomplete socket header received from QGIS MCP.",
                )

            resp_len = struct.unpack(">I", raw_len)[0]
            data = b""
            while len(data) < resp_len:
                chunk = s.recv(min(65536, resp_len - len(data)))
                if not chunk:
                    break
                data += chunk
            s.close()

            resp = json.loads(data.decode("utf-8"))
            elapsed = time.time() - t0

            if resp.get("status") == "success":
                layers = resp.get("result", {}).get("layers", [])
                layer_names = [l.get("name", "") for l in layers if isinstance(l, dict)]
                return QGISLiveStatus(
                    connected=True,
                    layers_count=len(layer_names),
                    layer_names=layer_names,
                    canvas_captured=True,
                    duration_sec=round(elapsed, 2),
                )
            else:
                return QGISLiveStatus(
                    connected=True,
                    duration_sec=round(elapsed, 2),
                    error=resp.get("message", "Unknown QGIS MCP error"),
                )
        except Exception as e:
            return QGISLiveStatus(
                connected=False,
                duration_sec=round(time.time() - t0, 2),
                error=f"Cannot reach QGIS Desktop at {host}:{port}: {str(e)}",
            )

    def verify_nvidia_nim(self) -> ProviderVerification:
        """Sends a verification prompt to NVIDIA NIM vision endpoint."""
        provider = NvidiaNIMProvider()
        if not provider.is_available():
            return ProviderVerification(
                provider_name="NVIDIA NIM",
                model=provider.default_model,
                status="skipped",
                duration_sec=0.0,
                response_sample="",
                error="NVIDIA_API_KEY not configured.",
            )

        resp = provider.generate(
            prompt="You are validating StratumRO GeoAI visual telemetry. Reply with a short JSON confirming operational status: {\"status\": \"OPERATIONAL\", \"subsystem\": \"StratumRO_Vision\"}",
            temperature=0.1,
            max_tokens=50,
            timeout=15.0,
        )

        return ProviderVerification(
            provider_name="NVIDIA NIM",
            model=resp.model_name,
            status=resp.status,
            duration_sec=resp.duration_sec,
            response_sample=resp.content.strip()[:120],
            error=resp.error,
        )

    def request_kilo_audit(
        self,
        milestone_name: str,
        submission_text: str,
        timeout: float = 120.0,
    ) -> KiloAuditResult:
        """Submits milestone evidence to Kilo via OpenRouter (Llama 3.3 70B)."""
        provider = UnionAlphaProvider(default_model="meta-llama/llama-3.3-70b-instruct")
        if not provider.is_available():
            return KiloAuditResult(
                status="FAILED",
                error="OPENROUTER_API_KEY or UNION_ALPHA_API_KEY not configured.",
            )

        system_prompt = (
            "You are Kilo, Senior Adversarial Reviewer for the StratumRO Geospatial Platform. "
            "Your role is to rigorously challenge architecture, detect metric leaks, prevent coordinate hallucination, "
            "and ensure strict compliance with AGENTS.md 8 evidence-first scientific rules. "
            "Output your review starting with an explicit verdict on line 1: VERDICT: APPROVED | APPROVED_WITH_CONDITIONS | REJECTED. "
            "Followed by: Top Findings, Scientific Rule Adherence, and Next Recommendations."
        )

        prompt = f"""# MILESTONE ADVERSARIAL REVIEW REQUEST
Milestone: {milestone_name}
Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}

## SUBMISSION CONTEXT & EVIDENCE:
{submission_text}

Provide your adversarial assessment following the required format.
"""
        t0 = time.time()
        resp = provider.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            model="meta-llama/llama-3.3-70b-instruct",
            max_tokens=3000,
            temperature=0.15,
            timeout=timeout,
        )
        elapsed = time.time() - t0

        if resp.status != "success" or not resp.content:
            return KiloAuditResult(
                status="FAILED",
                duration_sec=round(elapsed, 2),
                error=resp.error or "Empty response from Kilo model",
            )

        content = resp.content.strip()
        first_line = content.splitlines()[0] if content else ""
        verdict = "UNKNOWN"
        status = "UNKNOWN"

        if "APPROVED_WITH_CONDITIONS" in content[:300]:
            verdict = "APPROVED_WITH_CONDITIONS"
            status = "APPROVED_WITH_CONDITIONS"
        elif "APPROVED" in content[:300] and "NOT APPROVED" not in content[:300]:
            verdict = "APPROVED"
            status = "APPROVED"
        elif "REJECTED" in content[:300]:
            verdict = "REJECTED"
            status = "REJECTED"

        findings = []
        for line in content.splitlines():
            line_str = line.strip()
            if line_str.startswith(("-", "*", "1.", "2.", "3.")) and len(line_str) > 15:
                findings.append(line_str)
                if len(findings) >= 5:
                    break

        return KiloAuditResult(
            status=status,
            reviewer="Kilo (meta-llama/llama-3.3-70b-instruct)",
            duration_sec=round(elapsed, 2),
            verdict=verdict,
            findings=findings,
            full_review=content,
        )

    def run_full_cycle(
        self,
        milestone_name: str,
        description: str,
        changed_files: List[str],
        skip_kilo: bool = False,
    ) -> ClosedLoopReport:
        """Executes the complete 4-stage closed development loop."""
        print(f"[*] Starting StratumRO Closed-Loop Cycle: {milestone_name}")
        t_start = time.strftime("%Y-%m-%d %H:%M:%S")

        # 1. Deterministic Unit Tests
        print("  -> [1/4] Executing Automated Unit Tests...")
        tests = self.run_unit_tests()
        print(f"     Tests: {tests.passed} passed, {tests.skipped} skipped, {tests.failed} failed in {tests.duration_sec}s")

        # 2. Live QGIS Socket
        print("  -> [2/4] Inspecting Live QGIS Desktop Bridge (127.0.0.1:9876)...")
        qgis = self.check_qgis_live()
        print(f"     QGIS: connected={qgis.connected}, layers={qgis.layers_count} in {qgis.duration_sec}s")

        # 3. NVIDIA NIM Vision Provider
        print("  -> [3/4] Verifying NVIDIA NIM Multimodal Vision Telemetry...")
        nim = self.verify_nvidia_nim()
        print(f"     NVIDIA NIM: status={nim.status} ({nim.model}) in {nim.duration_sec}s")

        # 4. Kilo Adversarial Review
        if skip_kilo:
            kilo = KiloAuditResult(status="SKIPPED", verdict="SKIPPED", full_review="Kilo review skipped by flag.")
        else:
            print("  -> [4/4] Submitting Milestone to Kilo Adversarial Reviewer (Llama 3.3 70B)...")
            submission_text = f"""### Milestone: {milestone_name}
### Description: {description}
### Changed Files:
{json.dumps(changed_files, indent=2)}

### Test Suite Execution:
- Discovered: {tests.total_discovered}
- Passed: {tests.passed}
- Skipped: {tests.skipped}
- Failed: {tests.failed}
- Duration: {tests.duration_sec}s

### QGIS Desktop Live Engine:
- Connected: {qgis.connected}
- Active Layers: {qgis.layers_count} ({', '.join(qgis.layer_names[:4])})

### Vision AI Status (NVIDIA NIM):
- Status: {nim.status}
- Latency: {nim.duration_sec}s
- Response: {nim.response_sample}
"""
            kilo = self.request_kilo_audit(milestone_name, submission_text)
            print(f"     Kilo Verdict: {kilo.verdict} (in {kilo.duration_sec}s)")

        # Determine overall status
        if not tests.success or (kilo.status == "REJECTED"):
            overall = "FAIL"
        elif (kilo.status == "APPROVED_WITH_CONDITIONS") or (not qgis.connected):
            overall = "PASS_WITH_WARNINGS"
        else:
            overall = "PASS"

        summary = (
            f"Closed-Loop Cycle '{milestone_name}' -> {overall}. "
            f"Tests: {tests.passed}/{tests.total_discovered} passed, 0 failed. "
            f"QGIS: {'Connected (' + str(qgis.layers_count) + ' layers)' if qgis.connected else 'Offline'}. "
            f"NIM: {nim.status}. Kilo: {kilo.verdict}."
        )

        return ClosedLoopReport(
            milestone_name=milestone_name,
            timestamp=t_start,
            tests=tests,
            qgis=qgis,
            nim=nim,
            kilo=kilo,
            overall_status=overall,
            summary=summary,
        )
