# api/main.py
import os
import sqlite3
import uuid

import httpx
from fastapi import FastAPI, HTTPException, Request

from shared import db

DB_PATH = os.getenv("DB_PATH", "./data/tasks.db")
WORKER_URL = os.getenv("WORKER_URL", "http://localhost:8001")

app = FastAPI(title="Quantum Task API")

_conn: sqlite3.Connection | None = None


@app.on_event("startup")
def _startup() -> None:
    global _conn
    _conn = db.connect(DB_PATH)
    db.init_db(_conn)


@app.post("/tasks")
async def create_task(request: Request) -> dict:
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="invalid json")

    circuit = body.get("circuit") if isinstance(body, dict) else None
    if not isinstance(circuit, str) or not circuit.strip():
        raise HTTPException(status_code=400, detail="circuit must be a non-empty string")

    task_id = str(uuid.uuid4())
    db.create_task(_conn, task_id, circuit)

    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            await client.post(f"{WORKER_URL}/execute", json={"task_id": task_id})
    except Exception:
        pass

    return {"task_id": task_id, "status": "submitted"}


@app.get("/tasks/{task_id}")
def get_task(task_id: str) -> dict:
    t = db.get_task(_conn, task_id)
    if t is None:
        raise HTTPException(status_code=404, detail="task not found")

    status = t["status"]
    if status in ("submitted", "running"):
        return {"task_id": task_id, "status": "pending"}

    if status == "completed":
        return {"task_id": task_id, "status": "completed", "result": t["result"]}

    if status == "failed":
        return {"task_id": task_id, "status": "failed", "error": t["error"]}

    return {"task_id": task_id, "status": status}