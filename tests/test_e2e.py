import time

import httpx
from qiskit import QuantumCircuit
from qiskit.qasm3 import dumps as qasm3_dumps


API_URL = "http://localhost:8000"
TIMEOUT_S = 20.0
POLL_S = 0.25


def _bell_qasm3() -> str:
    qc = QuantumCircuit(2, 2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure([0, 1], [0, 1])
    return qasm3_dumps(qc)


def test_submit_and_get_result():
    payload = _bell_qasm3()

    with httpx.Client(timeout=10.0) as client:
        r = client.post(f"{API_URL}/tasks", json={"circuit": payload})
        assert r.status_code == 200
        task_id = r.json()["task_id"]
        assert isinstance(task_id, str) and task_id

        deadline = time.time() + TIMEOUT_S
        while True:
            g = client.get(f"{API_URL}/tasks/{task_id}")
            assert g.status_code == 200
            data = g.json()

            if data["status"] == "completed":
                result = data["result"]
                assert isinstance(result, dict)
                assert "00" in result or "11" in result
                assert sum(result.values()) > 0
                break

            if data["status"] == "failed":
                raise AssertionError(f"task failed: {data.get('error')}")

            if time.time() > deadline:
                raise AssertionError("timed out waiting for task completion")

            time.sleep(POLL_S)