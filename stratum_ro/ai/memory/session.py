# -*- coding: utf-8 -*-
"""
Session Memory & Reproducibility Audit Engine for StratumRO AI (MD 4 Conformance).
Provides local-first SQLite structured persistence for task execution logs,
artifact references, scoped user approvals, validation summaries, and crash recovery,
strictly conforming to AGENTS.md evidence rules and privacy constraints.
"""

import json
import os
import re
import sqlite3
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Regex patterns for sensitive credentials (MD 4 Section 3.2, 36)
SECRET_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9_-]{20,}", re.IGNORECASE),
    re.compile(r"nvapi-[a-zA-Z0-9_-]{20,}", re.IGNORECASE),
    re.compile(r"Bearer\s+[a-zA-Z0-9_\-\.]{20,}", re.IGNORECASE),
    re.compile(r"(api[_-]?key|password|secret|token)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-]{8,})['\"]?", re.IGNORECASE),
]


def sanitize_secrets(value: Any) -> Any:
    """
    Recursively redacts sensitive API keys, tokens, and credentials from
    strings, dicts, and lists before writing to persistent memory.
    """
    if isinstance(value, str):
        masked = value
        for pat in SECRET_PATTERNS:
            masked = pat.sub("[REDACTED_SECRET]", masked)
        return masked
    elif isinstance(value, dict):
        cleaned = {}
        for k, v in value.items():
            k_lower = str(k).lower()
            if any(s in k_lower for s in ["key", "token", "password", "secret", "auth", "credential"]):
                cleaned[k] = "[REDACTED_SECRET]"
            else:
                cleaned[k] = sanitize_secrets(v)
        return cleaned
    elif isinstance(value, list):
        return [sanitize_secrets(item) for item in value]
    return value


class SessionMemory:
    """
    Stateful memory recording workflow execution, artifacts, and user approvals
    backed by local SQLite database with thread-safe WAL mode and crash recovery.
    """

    def __init__(
        self,
        session_id: Optional[str] = None,
        db_path: Optional[str] = None,
        auto_recover: bool = True
    ):
        self.session_id = session_id or f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.start_time = time.time()
        self._lock = threading.RLock()

        # In-memory mirrors for backward compatibility
        self.task_history: List[Dict[str, Any]] = []
        self.approvals: List[Dict[str, Any]] = []
        self.artifacts: List[str] = []

        # Configure SQLite database path
        if db_path is None:
            ws_dir = Path("workspace")
            ws_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = str((ws_dir / "memory.db").resolve())
        else:
            self.db_path = db_path

        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

        if auto_recover:
            self.recover_interrupted_sessions()

        self._register_session_start()

    def _get_connection(self) -> sqlite3.Connection:
        """Returns or creates a thread-safe SQLite connection with WAL mode."""
        if self._conn is None:
            conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=10.0)
            conn.row_factory = sqlite3.Row
            # Enable WAL mode for high concurrency
            try:
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.execute("PRAGMA busy_timeout=5000;")
                conn.execute("PRAGMA synchronous=NORMAL;")
            except Exception:
                pass
            self._conn = conn
        return self._conn

    def _init_db(self):
        """Initializes SQLite schema for sessions, tasks, approvals, artifacts, and memory entries."""
        with self._lock:
            conn = self._get_connection()
            with conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS sessions (
                        session_id TEXT PRIMARY KEY,
                        start_time REAL,
                        end_time REAL,
                        status TEXT,
                        metadata TEXT
                    );
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS tasks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        task_id TEXT,
                        session_id TEXT,
                        graph_id TEXT,
                        task_type TEXT,
                        tool TEXT,
                        provider TEXT,
                        status TEXT,
                        start_time REAL,
                        end_time REAL,
                        duration_sec REAL,
                        confidence REAL,
                        evidence_level TEXT,
                        source TEXT,
                        outputs_summary TEXT,
                        error TEXT,
                        artifact_reference TEXT,
                        timestamp TEXT
                    );
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS approvals (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        task_id TEXT,
                        session_id TEXT,
                        decision TEXT,
                        scope TEXT,
                        reason TEXT,
                        timestamp TEXT
                    );
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS artifacts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT,
                        task_id TEXT,
                        file_path TEXT,
                        artifact_type TEXT,
                        file_size_kb REAL,
                        timestamp TEXT
                    );
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS memory_entries (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT,
                        task_id TEXT,
                        category TEXT,
                        key TEXT,
                        value TEXT,
                        source TEXT,
                        confidence REAL,
                        artifact_reference TEXT,
                        evidence_level TEXT,
                        timestamp TEXT
                    );
                """)
                # Indexes for fast querying
                conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_session ON tasks(session_id);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_task ON tasks(task_id);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_approvals_task ON approvals(task_id);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_cat ON memory_entries(category);")

    def _register_session_start(self):
        """Records initial session lifecycle start."""
        with self._lock:
            conn = self._get_connection()
            with conn:
                conn.execute(
                    "INSERT OR IGNORE INTO sessions (session_id, start_time, status, metadata) VALUES (?, ?, ?, ?)",
                    (self.session_id, self.start_time, "RUNNING", json.dumps({"source": "stratum_ro_agent"}))
                )

    def recover_interrupted_sessions(self) -> int:
        """
        Crash Recovery (MD 4 Section 32):
        Detects stale tasks/sessions left in 'RUNNING' status from prior abnormal process exits
        and marks them as 'INTERRUPTED'.
        """
        with self._lock:
            conn = self._get_connection()
            with conn:
                cur = conn.execute(
                    "UPDATE tasks SET status='INTERRUPTED' WHERE status='RUNNING' AND session_id != ?",
                    (self.session_id,)
                )
                interrupted_tasks = cur.rowcount
                conn.execute(
                    "UPDATE sessions SET status='INTERRUPTED', end_time=? WHERE status='RUNNING' AND session_id != ?",
                    (time.time(), self.session_id)
                )
            return interrupted_tasks

    def record_task(
        self,
        task_id: str,
        tool: str,
        status: str,
        duration_sec: float = 0.0,
        outputs: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        confidence: Optional[float] = None,
        graph_id: Optional[str] = None,
        task_type: Optional[str] = None,
        provider: Optional[str] = None,
        evidence_level: str = "OBSERVED",
        source: str = "tool_result",
        artifact_reference: Optional[str] = None
    ):
        """
        Records a task execution event into SQLite and in-memory history.
        Masks any sensitive secrets in outputs or errors before storage.
        """
        now_iso = datetime.now().isoformat()
        clean_error = sanitize_secrets(error) if error else None
        clean_outputs = sanitize_secrets(outputs) if outputs else {}
        outputs_summary = {k: type(v).__name__ for k, v in clean_outputs.items()}

        record = {
            "task_id": task_id,
            "tool": tool,
            "status": status,
            "duration_sec": round(duration_sec, 3),
            "timestamp": now_iso,
            "confidence": confidence,
            "evidence_level": evidence_level,
            "source": source,
            "outputs_summary": outputs_summary,
            "error": clean_error,
            "artifact_reference": artifact_reference
        }

        with self._lock:
            self.task_history.append(record)
            conn = self._get_connection()
            with conn:
                conn.execute("""
                    INSERT INTO tasks (
                        task_id, session_id, graph_id, task_type, tool, provider,
                        status, start_time, end_time, duration_sec, confidence,
                        evidence_level, source, outputs_summary, error, artifact_reference, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    task_id, self.session_id, graph_id, task_type or tool, tool, provider or "deterministic",
                    status, self.start_time, time.time(), round(duration_sec, 3), confidence,
                    evidence_level, source, json.dumps(outputs_summary), clean_error, artifact_reference, now_iso
                ))

    def record_approval(
        self,
        task_id: str,
        approved: bool = True,
        comment: str = "",
        scope: str = "general",
        decision: Optional[str] = None
    ):
        """
        Records human approval decision with explicit scope (MD 4 Section 23).
        Scope restricts approval to a specific operation (e.g. export_topolt_dxf).
        """
        now_iso = datetime.now().isoformat()
        dec_str = decision or ("approved" if approved else "rejected")
        clean_comment = sanitize_secrets(comment)

        with self._lock:
            self.approvals.append({
                "task_id": task_id,
                "approved": approved,
                "decision": dec_str,
                "scope": scope,
                "comment": clean_comment,
                "timestamp": now_iso
            })

            conn = self._get_connection()
            with conn:
                conn.execute("""
                    INSERT INTO approvals (task_id, session_id, decision, scope, reason, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (task_id, self.session_id, dec_str, scope, clean_comment, now_iso))

    def record_artifact(
        self,
        file_path: str,
        task_id: Optional[str] = None,
        artifact_type: Optional[str] = None
    ):
        """Tracks an output artifact reference in memory and SQLite."""
        now_iso = datetime.now().isoformat()
        file_size_kb = 0.0
        try:
            p = Path(file_path)
            if p.is_file():
                file_size_kb = round(p.stat().st_size / 1024.0, 1)
        except Exception:
            pass

        with self._lock:
            if file_path not in self.artifacts:
                self.artifacts.append(file_path)

            conn = self._get_connection()
            with conn:
                conn.execute("""
                    INSERT INTO artifacts (session_id, task_id, file_path, artifact_type, file_size_kb, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (self.session_id, task_id, file_path, artifact_type or Path(file_path).suffix, file_size_kb, now_iso))

    def record_memory_entry(
        self,
        category: str,
        key: str,
        value: Any,
        source: str = "deterministic_validation",
        confidence: Optional[float] = None,
        artifact_reference: Optional[str] = None,
        evidence_level: str = "OBSERVED",
        task_id: Optional[str] = None
    ):
        """Records an audited persistent memory record conforming to Sections 20-22."""
        now_iso = datetime.now().isoformat()
        clean_val = sanitize_secrets(value)
        val_str = json.dumps(clean_val) if isinstance(clean_val, (dict, list)) else str(clean_val)

        with self._lock:
            conn = self._get_connection()
            with conn:
                conn.execute("""
                    INSERT INTO memory_entries (
                        session_id, task_id, category, key, value, source,
                        confidence, artifact_reference, evidence_level, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    self.session_id, task_id, category, key, val_str, source,
                    confidence, artifact_reference, evidence_level, now_iso
                ))

    # =========================================================================
    # Query APIs (MD 4 Section 25)
    # =========================================================================

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves session metadata and task count by session_id."""
        with self._lock:
            conn = self._get_connection()
            cur = conn.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
            row = cur.fetchone()
            if not row:
                return None
            return dict(row)

    def get_task_history(self, task_id: str) -> List[Dict[str, Any]]:
        """Retrieves task runs and retries for a given task_id."""
        with self._lock:
            conn = self._get_connection()
            cur = conn.execute("SELECT * FROM tasks WHERE task_id = ? ORDER BY id ASC", (task_id,))
            return [dict(r) for r in cur.fetchall()]

    def get_recent_runs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Returns recent completed/failed tasks across sessions."""
        with self._lock:
            conn = self._get_connection()
            cur = conn.execute("""
                SELECT task_id, session_id, tool, status, duration_sec, evidence_level, timestamp, artifact_reference
                FROM tasks ORDER BY id DESC LIMIT ?
            """, (limit,))
            return [dict(r) for r in cur.fetchall()]

    def get_artifact_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieves registered output artifacts and sizes."""
        with self._lock:
            conn = self._get_connection()
            cur = conn.execute("SELECT * FROM artifacts ORDER BY id DESC LIMIT ?", (limit,))
            return [dict(r) for r in cur.fetchall()]

    def get_validation_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieves validation metrics stored in memory entries."""
        with self._lock:
            conn = self._get_connection()
            cur = conn.execute("""
                SELECT * FROM memory_entries
                WHERE category IN ('validation', 'evaluation')
                ORDER BY id DESC LIMIT ?
            """, (limit,))
            return [dict(r) for r in cur.fetchall()]

    def get_approval(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves approval decision and scope for a specific task."""
        with self._lock:
            conn = self._get_connection()
            cur = conn.execute("SELECT * FROM approvals WHERE task_id = ? ORDER BY id DESC LIMIT 1", (task_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def search_memory(self, query: str, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Performs structured search across tasks, approvals, and memory entries
        without requiring vector database dependencies (Section 40).
        """
        pattern = f"%{query}%"
        results = []
        with self._lock:
            conn = self._get_connection()
            # 1. Search tasks
            cur = conn.execute("""
                SELECT 'task' AS kind, task_id, tool AS name, status AS result, timestamp
                FROM tasks WHERE tool LIKE ? OR task_id LIKE ? OR error LIKE ?
                ORDER BY id DESC LIMIT 10
            """, (pattern, pattern, pattern))
            results.extend([dict(r) for r in cur.fetchall()])

            # 2. Search memory entries
            if category:
                cur2 = conn.execute("""
                    SELECT 'memory' AS kind, key AS name, value AS result, category, timestamp
                    FROM memory_entries WHERE category = ? AND (key LIKE ? OR value LIKE ?)
                    ORDER BY id DESC LIMIT 10
                """, (category, pattern, pattern))
            else:
                cur2 = conn.execute("""
                    SELECT 'memory' AS kind, key AS name, value AS result, category, timestamp
                    FROM memory_entries WHERE key LIKE ? OR value LIKE ?
                    ORDER BY id DESC LIMIT 10
                """, (pattern, pattern))
            results.extend([dict(r) for r in cur2.fetchall()])

        return results

    # =========================================================================
    # Retention & Audit Export (MD 4 Section 30)
    # =========================================================================

    def cleanup_old_records(self, retention_days: int = 30, keep_sessions: int = 50) -> Dict[str, int]:
        """
        Bounded cleanup policy removing historical records older than retention_days,
        while always preserving the most recent keep_sessions.
        """
        cutoff_date = (datetime.now() - timedelta(days=retention_days)).isoformat()
        with self._lock:
            conn = self._get_connection()
            with conn:
                # Identify sessions to keep
                cur = conn.execute(
                    "SELECT session_id FROM sessions ORDER BY start_time DESC LIMIT ?",
                    (keep_sessions,)
                )
                keep_ids = [r["session_id"] for r in cur.fetchall()]
                placeholders = ",".join(["?"] * len(keep_ids)) if keep_ids else "''"

                query_del = f"""
                    DELETE FROM tasks
                    WHERE timestamp < ? AND session_id NOT IN ({placeholders})
                """
                params = [cutoff_date] + keep_ids
                c1 = conn.execute(query_del, params)
                del_tasks = c1.rowcount

                query_del_mem = f"""
                    DELETE FROM memory_entries
                    WHERE timestamp < ? AND session_id NOT IN ({placeholders})
                """
                c2 = conn.execute(query_del_mem, params)
                del_mem = c2.rowcount

            return {"deleted_tasks": del_tasks, "deleted_memory_entries": del_mem}

    def to_dict(self) -> Dict[str, Any]:
        """Returns JSON-serializable dictionary summary for audit trail."""
        return {
            "session_id": self.session_id,
            "duration_total_sec": round(time.time() - self.start_time, 2),
            "tasks_count": len(self.task_history),
            "approvals_count": len(self.approvals),
            "artifacts_count": len(self.artifacts),
            "tasks": self.task_history,
            "approvals": self.approvals,
            "artifacts": self.artifacts
        }

    def save_audit_log(self, output_dir: str = "workspace/output") -> str:
        """Saves session audit trail to disk as structured JSON."""
        os.makedirs(output_dir, exist_ok=True)
        log_path = os.path.join(output_dir, f"session_audit_{self.session_id}.json")
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)
        return log_path

    def close(self):
        """Closes the underlying SQLite connection cleanly."""
        with self._lock:
            if self._conn is not None:
                try:
                    self._conn.close()
                except Exception:
                    pass
                self._conn = None

