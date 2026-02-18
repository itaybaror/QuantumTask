# worker/main.py
import os
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, HTTPException, Request
from qiskit.qasm3 import loads as qasm3_loads
from qiskit_aer import AerSimulator

from shared import db

# Path to shared SQLite database (mounted volume in Docker)
DB_PATH = os.getenv("DB_PATH", "./data/tasks.db")

app = FastAPI(title="Quantum Task Worker")

# Global thread pool used for background execution
_executor: ThreadPoolExecutor | None = None


def _execute_circuit(qasm_string: str):
    # Parse QASM3 string into a QuantumCircuit
    qc = qasm3_loads(qasm_string)

    # Run circuit on local simulator (blocking / CPU work)
    simulator = AerSimulator()
    result = simulator.run(qc, shots=1024).result()

    # Return measurement counts as plain dict
    return dict(result.get_counts(qc))


def _run_task(task_id: str):
    # This runs inside a background thread
    conn = db.connect(DB_PATH)
    try:
        task = db.get_task(conn, task_id)
        if task is None:
            return

        # Avoid re-running tasks
        if task["status"] in ("pending", "completed", "failed"):
            return

        # Mark task as pending
        db.set_status(conn, task_id, "pending")

        # Execute circuit (blocking work)
        result = _execute_circuit(task["payload"])

        # Store successful result
        db.set_result(conn, task_id, result)

    except Exception as e:
        # Store failure in DB if execution crashes
        db.set_error(conn, task_id, str(e))
    finally:
        conn.close()


@app.on_event("startup")
def _startup():
    # Initialize DB and thread pool once on worker startup
    global _executor
    conn = db.connect(DB_PATH)
    db.init_db(conn)
    conn.close()

    # Limit parallel executions
    _executor = ThreadPoolExecutor(max_workers=2)


@app.post("/execute")
async def execute(request: Request):
    # Async HTTP handler (non-blocking I/O only)
    body = await request.json()
    task_id = body.get("task_id")

    if not isinstance(task_id, str) or not task_id.strip():
        raise HTTPException(status_code=400, detail="invalid task_id")

    conn = db.connect(DB_PATH)
    try:
        if db.get_task(conn, task_id) is None:
            raise HTTPException(status_code=404, detail="task not found")

        # Submit execution to background thread
        # Do not block HTTP response
        _executor.submit(_run_task, task_id)

        return {"accepted": True}
    finally:
        conn.close()