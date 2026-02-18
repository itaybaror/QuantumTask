# QuantumTask ⚛️

A minimal distributed quantum circuit execution service built with FastAPI, Docker, and Qiskit, demonstrating asynchronous request handling and background task execution via threading.

## Table of Contents

- [About the Project](#about-the-project)
- [Getting Started](#getting-started)
- [Architecture](#architecture)
- [Design Decisions](#design-decisions)
- [Deliverables](#deliverables)
- [Resources & References](#resources--references)

## About the Project

QuantumTask is a distributed quantum circuit execution system.

It allows clients to:

- Submit serialized OpenQASM 3 quantum circuits
- Receive a task ID immediately
- Poll for execution status
- Retrieve measurement results once execution completes

The system demonstrates:

- Asynchronous HTTP handling
- Background CPU-bound execution using threads
- Clean separation between API and Worker services
- Deterministic task lifecycle management via SQLite
- Container-based service communication

The API does not execute circuits.  
The Worker performs execution in background threads.

This guarantees:

- The API remains responsive
- Circuit execution does not block requests
- Multiple circuits can execute concurrently

⚠️ Disclaimer  
This project uses Qiskit’s local Aer simulator only.  
No real quantum hardware is involved.


## Getting Started

### 1. Prerequisites

- Docker
- Docker Compose

### 2. Run the System

Build and start services:

```bash
docker compose up --build
```

The API will be available at:

```
http://localhost:8000
```

Swagger docs:

```
http://localhost:8000/docs
```

### 3. Running Tests

With Docker running:

```bash
pytest -q
```

## Architecture

The system consists of two services:

- API (FastAPI)
- Worker (FastAPI + ThreadPoolExecutor)

Both share a mounted SQLite database.

Project structure:

```
.
├── api/
│   └── main.py
├── worker/
│   └── main.py
├── shared/
│   └── db.py
├── tests/
│   ├── test_errors.py
│   └── test_async_behavior.py
├── docker-compose.yml
└── README.md
```

### High-Level Flow

1. Client submits circuit to API (`POST /tasks`)
2. API:
   - Validates input
   - Inserts task with status = "submitted"
   - Asynchronously notifies Worker
   - Returns task_id immediately
3. Worker:
   - Receives `/execute`
   - Submits task to ThreadPoolExecutor
   - Returns acknowledgment immediately
4. Background thread:
   - Marks task as "running"
   - Executes QASM circuit
   - Updates DB with result or failure
5. Client polls (`GET /tasks/{id}`)

### Concurrency Model

- Async is used only for HTTP I/O
- ThreadPoolExecutor handles blocking CPU execution
- SQLite acts as coordination layer

## Design Decisions

<details>
<summary><strong>Service Separation</strong></summary>

The API and Worker are separate services to clearly demonstrate:

- Non-blocking request handling
- Background execution isolation
- Inter-service communication via HTTP

This mirrors real microservice patterns.

</details>

<details>
<summary><strong>Async Usage</strong></summary>

Async is used only where appropriate:

- Reading HTTP request bodies
- Calling Worker service

CPU-bound Qiskit execution is not async and runs in threads instead.

</details>

<details>
<summary><strong>Threading</strong></summary>

The Worker uses a ThreadPoolExecutor with limited parallelism.

This:

- Prevents blocking the HTTP layer
- Controls resource usage
- Enables concurrent execution

</details>

<details>
<summary><strong>Database</strong></summary>

SQLite is used for simplicity and inspectability.

Task lifecycle states:

- submitted
- running
- completed
- failed

The database acts as the synchronization layer between services.

</details>

<details>
<summary><strong>Container Networking</strong></summary>

Services communicate via Docker internal DNS:

```
http://worker:8001
```

The Worker service is not exposed publicly; only the API is.

This reflects common internal-service communication patterns.

</details>

## Deliverables

This repository includes:

- Full Docker-based implementation
- API + Worker separation
- Deterministic task lifecycle management
- Integration tests covering:
  - Invalid input handling
  - Failure propagation
  - Background execution behavior
  - Concurrency validation
- This README with architectural explanation

## Resources & References

- FastAPI Documentation  
  https://fastapi.tiangolo.com/

- Qiskit Aer Simulator  
  https://qiskit.org/

- Python ThreadPoolExecutor  
  https://docs.python.org/3/library/concurrent.futures.html

- Docker Compose Networking  
  https://docs.docker.com/compose/networking/

These references guided the concurrency model, service separation, and execution architecture used in QuantumTask.