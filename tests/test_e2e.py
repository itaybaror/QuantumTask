import time
import uuid

import httpx

API_URL = "http://localhost:8000"


# Test that sending invalid JSON returns 400
def test_post_invalid_json():
    r = httpx.post(
        f"{API_URL}/tasks",
        content="not-json",
        headers={"Content-Type": "application/json"},
    )
    assert r.status_code == 400
    assert r.json()["detail"] == "invalid json"


# Test that missing "circuit" field returns 400
def test_post_missing_circuit():
    r = httpx.post(f"{API_URL}/tasks", json={})
    assert r.status_code == 400
    assert "circuit" in r.json()["detail"]


# Test that empty circuit string returns 400
def test_post_empty_circuit():
    r = httpx.post(f"{API_URL}/tasks", json={"circuit": "   "})
    assert r.status_code == 400


# Test that requesting a non-existent task returns 404
def test_get_nonexistent_task():
    fake_id = str(uuid.uuid4())
    r = httpx.get(f"{API_URL}/tasks/{fake_id}")
    assert r.status_code == 404
    assert r.json()["detail"] == "task not found"


# Test that invalid QASM results in task status "failed"
def test_invalid_qasm_results_in_failed_status():
    r = httpx.post(f"{API_URL}/tasks", json={"circuit": "INVALID QASM"})
    assert r.status_code == 200

    task_id = r.json()["task_id"]

    deadline = time.time() + 10
    while True:
        g = httpx.get(f"{API_URL}/tasks/{task_id}")
        data = g.json()

        if data["status"] == "failed":
            assert "error" in data
            break

        if time.time() > deadline:
            raise AssertionError("Task did not fail within timeout")

        time.sleep(0.2)


# Test full successful execution of a valid Bell state circuit
def test_successful_bell_circuit():
    qasm = """OPENQASM 3.0;
include "stdgates.inc";
bit[2] c;
qubit[2] q;
h q[0];
cx q[0], q[1];
c[0] = measure q[0];
c[1] = measure q[1];
"""

    r = httpx.post(f"{API_URL}/tasks", json={"circuit": qasm})
    assert r.status_code == 200

    task_id = r.json()["task_id"]

    deadline = time.time() + 10
    while True:
        g = httpx.get(f"{API_URL}/tasks/{task_id}")
        data = g.json()

        if data["status"] == "completed":
            result = data["result"]
            assert isinstance(result, dict)
            assert sum(result.values()) > 0
            break

        if data["status"] == "failed":
            raise AssertionError(f"Unexpected failure: {data.get('error')}")

        if time.time() > deadline:
            raise AssertionError("Task did not complete within timeout")

        time.sleep(0.2)