import time
import httpx

API_URL = "http://localhost:8000"


# Test that POST /tasks returns immediately and does not block on execution
def test_post_returns_immediately():
    qasm = "INVALID QASM"

    start = time.time()
    r = httpx.post(f"{API_URL}/tasks", json={"circuit": qasm})
    duration = time.time() - start

    assert r.status_code == 200

    # Should return quickly (execution happens in background)
    assert duration < 1.0


# Test that task status changes asynchronously over time
def test_status_changes_over_time():
    qasm = "INVALID QASM"

    r = httpx.post(f"{API_URL}/tasks", json={"circuit": qasm})
    task_id = r.json()["task_id"]

    first = httpx.get(f"{API_URL}/tasks/{task_id}").json()
    assert first["status"] == "pending"

    deadline = time.time() + 10
    while True:
        current = httpx.get(f"{API_URL}/tasks/{task_id}").json()

        if current["status"] in ("completed", "failed"):
            break

        if time.time() > deadline:
            raise AssertionError("Task did not finish within timeout")

        time.sleep(0.2)

    assert current["status"] in ("completed", "failed")


# Test that multiple tasks can execute concurrently (thread pool behavior)
def test_multiple_tasks_run_in_parallel():
    qasm = """OPENQASM 3.0;
include "stdgates.inc";
bit[2] c;
qubit[2] q;
h q[0];
cx q[0], q[1];
c[0] = measure q[0];
c[1] = measure q[1];
"""

    task_ids = []

    for _ in range(10):
        r = httpx.post(f"{API_URL}/tasks", json={"circuit": qasm})
        assert r.status_code == 200
        task_ids.append(r.json()["task_id"])

    completed = set()
    deadline = time.time() + 15

    while time.time() < deadline:
        for tid in task_ids:
            if tid in completed:
                continue

            status = httpx.get(f"{API_URL}/tasks/{tid}").json()["status"]
            if status == "completed":
                completed.add(tid)

        if len(completed) == len(task_ids):
            break

        time.sleep(0.2)

    assert len(completed) == len(task_ids)