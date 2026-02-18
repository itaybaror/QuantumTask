# worker/main.py
import os
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, HTTPException, Request
from qiskit.qasm3 import loads as qasm3_loads
from qiskit_aer import AerSimulator

from shared import db

DB_PATH = os.getenv("DB_PATH", "./data/tasks.db")

app = FastAPI(title="Quantum Task Worker")
_executor: ThreadPoolExecutor | None = None


def _execute_circuit(qasm_string: str) -> dict[str, int]:
    # Serialize a QuantumCircuit to a string format that can be sent over the network
    qc = qasm3_loads(qasm_string)
    simulator = AerSimulator()
    result = simulator.run(qc, shots=1024).result()
    return dict(result.get_counts(qc))


def _run_task(task_id: str) -> None:
    conn = db.connect(DB_PATH)
    try:
        task = db.get_task(conn, task_id)
        if task is None:
            return

        if task["status"] in ("running", "completed", "failed"):
            return

        db.set_status(conn, task_id, "running")
        result = _execute_circuit(task["payload"])
        db.set_result(conn, task_id, result)
    except Exception as e:
        db.set_error(conn, task_id, str(e))
    finally:
        conn.close()


@app.on_event("startup")
def _startup() -> None:
    global _executor
    conn = db.connect(DB_PATH)
    db.init_db(conn)
    conn.close()
    _executor = ThreadPoolExecutor(max_workers=2)


@app.post("/execute")
async def execute(request: Request) -> dict:
    body = await request.json()
    task_id = body.get("task_id")

    if not isinstance(task_id, str) or not task_id.strip():
        raise HTTPException(status_code=400, detail="invalid task_id")

    conn = db.connect(DB_PATH)
    try:
        if db.get_task(conn, task_id) is None:
            raise HTTPException(status_code=404, detail="task not found")

        _executor.submit(_run_task, task_id)
        return {"accepted": True}
    finally:
        conn.close()