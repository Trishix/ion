from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from ion.contracts import EngineEvent, TaskResult, TaskSpec


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class RunStore:
    """Local, inspectable record of foreground task runs.

    This is a history store, not an automatic resume mechanism. Repository edits
    are never replayed from it.
    """

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if path.is_symlink():
            raise ValueError("run database path cannot be a symlink")
        self.connection = sqlite3.connect(path)
        os.chmod(path, 0o600)
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA foreign_keys=ON")
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS runs (
                task_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                status TEXT NOT NULL,
                task_json TEXT NOT NULL,
                result_json TEXT
            );
            CREATE TABLE IF NOT EXISTS events (
                task_id TEXT NOT NULL REFERENCES runs(task_id),
                sequence INTEGER NOT NULL,
                event_json TEXT NOT NULL,
                PRIMARY KEY(task_id, sequence)
            );
            """
        )
        self.connection.commit()

    def begin(self, task: TaskSpec) -> None:
        timestamp = now()
        with self.connection:
            self.connection.execute(
                "INSERT INTO runs(task_id, created_at, updated_at, status, task_json) VALUES (?, ?, ?, ?, ?)",
                (task.task_id, timestamp, timestamp, "running", task.model_dump_json()),
            )

    def append(self, task_id: str, event: EngineEvent) -> None:
        with self.connection:
            self.connection.execute(
                "INSERT INTO events(task_id, sequence, event_json) "
                "VALUES (?, (SELECT COALESCE(MAX(sequence), 0) + 1 FROM events WHERE task_id = ?), ?)",
                (task_id, task_id, event.model_dump_json()),
            )
            self.connection.execute("UPDATE runs SET updated_at = ? WHERE task_id = ?", (now(), task_id))

    def finish(self, result: TaskResult) -> None:
        with self.connection:
            self.connection.execute(
                "UPDATE runs SET status = ?, result_json = ?, updated_at = ? WHERE task_id = ?",
                (result.outcome.value, result.model_dump_json(), now(), result.task_id),
            )

    def interrupt(self, task_id: str) -> None:
        with self.connection:
            self.connection.execute(
                "UPDATE runs SET status = 'interrupted', updated_at = ? WHERE task_id = ? AND status = 'running'",
                (now(), task_id),
            )

    def recent(self, limit: int = 10) -> list[dict]:
        rows = self.connection.execute(
            "SELECT task_id, created_at, status, task_json, result_json FROM runs ORDER BY created_at DESC LIMIT ?",
            (max(1, min(limit, 100)),),
        ).fetchall()
        return [
            {"task_id": task_id, "created_at": created_at, "status": status,
             "task": json.loads(task_json), "result": json.loads(result_json) if result_json else None}
            for task_id, created_at, status, task_json, result_json in rows
        ]

    def inspect(self, task_id: str) -> dict | None:
        row = self.connection.execute(
            "SELECT created_at, updated_at, status, task_json, result_json FROM runs WHERE task_id = ?",
            (task_id,),
        ).fetchone()
        if row is None:
            return None
        created_at, updated_at, status, task_json, result_json = row
        events = [json.loads(item[0]) for item in self.connection.execute(
            "SELECT event_json FROM events WHERE task_id = ? ORDER BY sequence", (task_id,)
        )]
        return {
            "task_id": task_id, "created_at": created_at, "updated_at": updated_at,
            "status": status, "task": json.loads(task_json),
            "result": json.loads(result_json) if result_json else None,
            "events": events,
        }

    def close(self) -> None:
        self.connection.close()
