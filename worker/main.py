# worker/main.py
import os
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, HTTPException, Request

from shared import db

DB_PATH = os.getenv("DB_PATH", "./data/tasks.db")

app = FastAPI(title="Quantum Task Worker")

_executor: ThreadPoolExecutor | None = None


def _execute_circuit(payload: str) -> dict:
    # Use the helper provided in the assignment (adjust module name if needed).
    from execute_circuit import execute_circuit  # type: ignore
    return execute_circuit(payload)


def _run_task(task_id: str) -> None:
    conn = db.connect(DB_PATH)
    try:
        t = db.get_task(conn, task_id)
        if t is None:
            return

        if t["status"] in ("running", "completed", "failed"):
            return

        db.set_status(conn, task_id, "running")
        result = _execute_circuit(t["payload"])
        db.set_result(conn, task_id, result)
    except Exception as e:
        try:
            db.set_error(conn, task_id, str(e))
        except Exception:
            pass
    finally:
        conn.close()


@app.on_event("startup")
def _startup() -> None:
    global _executor
    # Ensure schema exists (both services can do this; it's idempotent).
    conn = db.connect(DB_PATH)
    db.init_db(conn)
    conn.close()

    _executor = ThreadPoolExecutor(max_workers=2)


@app.on_event("shutdown")
def _shutdown() -> None:
    if _executor is not None:
        _executor.shutdown(wait=False)


@app.post("/execute")
async def execute(request: Request) -> dict:
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="invalid json")

    task_id = body.get("task_id") if isinstance(body, dict) else None
    if not isinstance(task_id, str) or not task_id.strip():
        raise HTTPException(status_code=400, detail="task_id must be a non-empty string")

    conn = db.connect(DB_PATH)
    try:
        t = db.get_task(conn, task_id)
        if t is None:
            raise HTTPException(status_code=404, detail="task not found")

        # If already done/in-progress, ack immediately (idempotent).
        if t["status"] in ("running", "completed", "failed"):
            return {"accepted": True, "status": t["status"]}

        # Submit background execution and return immediately.
        assert _executor is not None
        _executor.submit(_run_task, task_id)
        return {"accepted": True}
    finally:
        conn.close()