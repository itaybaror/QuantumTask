# shared/db.py
import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Optional


def now_ts() -> int:
    return int(time.time())


def connect(db_path: str) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            status TEXT NOT NULL,
            payload TEXT NOT NULL,
            result_json TEXT,
            error TEXT,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL
        )
        """
    )
    conn.commit()


def create_task(conn: sqlite3.Connection, task_id: str, payload: str) -> None:
    ts = now_ts()
    conn.execute(
        """
        INSERT INTO tasks (id, status, payload, result_json, error, created_at, updated_at)
        VALUES (?, 'submitted', ?, NULL, NULL, ?, ?)
        """,
        (task_id, payload, ts, ts),
    )
    conn.commit()


def get_task(conn: sqlite3.Connection, task_id: str) -> Optional[dict[str, Any]]:
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if row is None:
        return None

    result = None
    if row["result_json"] is not None:
        try:
            result = json.loads(row["result_json"])
        except json.JSONDecodeError:
            result = None

    return {
        "id": row["id"],
        "status": row["status"],
        "payload": row["payload"],
        "result": result,
        "error": row["error"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }