from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


FINAL_STATUSES = {"accepted", "review_required", "failed"}


@dataclass(frozen=True)
class Job:
    id: str
    input_path: str
    output_dir: str
    config_path: str
    status: str
    error: str | None
    attempts: int
    created_at: str
    updated_at: str


class JobStore:
    def __init__(self, database: str | Path) -> None:
        self.path = Path(database)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    input_path TEXT NOT NULL,
                    output_dir TEXT NOT NULL,
                    config_path TEXT NOT NULL,
                    status TEXT NOT NULL,
                    error TEXT,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            connection.execute("""
                CREATE TABLE IF NOT EXISTS job_events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)

    def create(self, input_path: str, output_dir: str, config_path: str) -> Job:
        now = datetime.now(timezone.utc).isoformat()
        job_id = uuid.uuid4().hex
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO jobs VALUES (?, ?, ?, ?, 'queued', NULL, 0, ?, ?)",
                (job_id, input_path, output_dir, config_path, now, now),
            )
            self._event(connection, job_id, "queued", {})
        return self.get(job_id)

    @staticmethod
    def _event(connection: sqlite3.Connection, job_id: str, status: str, payload: dict) -> None:
        connection.execute(
            "INSERT INTO job_events(job_id, status, payload, created_at) VALUES (?, ?, ?, ?)",
            (job_id, status, json.dumps(payload), datetime.now(timezone.utc).isoformat()),
        )

    def get(self, job_id: str) -> Job:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if row is None:
            raise KeyError(job_id)
        return Job(**dict(row))

    def update(self, job_id: str, status: str, *, error: str | None = None, payload: dict | None = None) -> Job:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            connection.execute(
                "UPDATE jobs SET status = ?, error = ?, updated_at = ? WHERE id = ?",
                (status, error, now, job_id),
            )
            self._event(connection, job_id, status, payload or {})
        return self.get(job_id)

    def claim_next(self) -> Job | None:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT id FROM jobs WHERE status = 'queued' ORDER BY created_at LIMIT 1"
            ).fetchone()
            if row is None:
                return None
            now = datetime.now(timezone.utc).isoformat()
            connection.execute(
                "UPDATE jobs SET status = 'preflight', attempts = attempts + 1, updated_at = ? WHERE id = ?",
                (now, row["id"]),
            )
            self._event(connection, row["id"], "preflight", {"claimed": True})
            job_id = row["id"]
        return self.get(job_id)

    def retry(self, job_id: str, retry_limit: int) -> Job:
        job = self.get(job_id)
        if job.status != "failed":
            raise ValueError("only failed jobs can be retried")
        if job.attempts > retry_limit:
            raise ValueError("retry limit reached")
        return self.update(job_id, "queued", error=None, payload={"retry": True})

    def events(self, job_id: str) -> list[dict[str, object]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT sequence, status, payload, created_at FROM job_events WHERE job_id = ? ORDER BY sequence",
                (job_id,),
            ).fetchall()
        return [
            {**dict(row), "payload": json.loads(row["payload"])} for row in rows
        ]

    def status_counts(self) -> dict[str, int]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT status, COUNT(*) AS count FROM jobs GROUP BY status"
            ).fetchall()
        return {str(row["status"]): int(row["count"]) for row in rows}
