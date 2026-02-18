from typing import Dict
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
from qiskit.qasm3 import dumps as qasm3_dumps
from qiskit.qasm3 import loads as qasm3_loads

DEFAULT_SHOTS = 1024
def serialize_circuit(qc: QuantumCircuit) -> str:
    """
    Serialize a QuantumCircuit to a string format that can be sent over the
    network.
    We use QASM 3 for portability and readability.
    """
    return qasm3_dumps(qc)
def deserialize_circuit(qc_serialized: str) -> QuantumCircuit:
    """
    Deserialize a QASM 3 string back into a QuantumCircuit.
    """
    return qasm3_loads(qc_serialized)

def execute_circuit(qc_serialized: str, shots: int = DEFAULT_SHOTS) -> Dict[str, int]:
    """
    Execute a serialized quantum circuit on a basic simulator and return
    measurement counts.
    Returns a dict like {"00": 512, "11": 512}.
    """
    qc = deserialize_circuit(qc_serialized)
    simulator = AerSimulator()
    result = simulator.run(qc, shots=shots).result()
    counts = result.get_counts(qc)
    # Ensure a plain dict[str, int] (some Qiskit versions return a Counts-like object)
    return dict(counts)

def create_bell_state_circuit() -> QuantumCircuit:
    """
    Create a 2-qubit Bell state circuit:
    |00> --H--*--measure
    |
    |00> ----X--measure
     Expected results (ideal): ~50% "00" and ~50% "11"
 """
    qc = QuantumCircuit(2, 2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure([0, 1], [0, 1])
    return qc

# if __name__ == "__main__":
# # Example usage:
# bell = create_bell_state_circuit()
# payload = serialize_circuit(bell)
# counts = execute_circuit(payload, shots=1024)
# print("Serialized payload (QASM3):")
# print(payload)
# print("Execution result counts:")
# print(counts)