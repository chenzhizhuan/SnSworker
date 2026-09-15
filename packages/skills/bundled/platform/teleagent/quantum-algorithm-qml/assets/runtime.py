"""Standalone runtime shared by the canonical QML adapter matrix."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _descriptor() -> dict[str, Any]:
    return json.loads(Path(__file__).with_name("adapter.json").read_text())


def _expectation(sdk: str, angle: float) -> float:
    if sdk == "cqlib":
        from cqlib import Circuit
        from cqlib.simulator import SimpleSimulator

        circuit = Circuit(1)
        circuit.ry(0, angle)
        probabilities = SimpleSimulator(circuit).probs(dict_format=False)
        return float(probabilities[0] - probabilities[1])
    if sdk == "qiskit":
        from qiskit import QuantumCircuit
        from qiskit.quantum_info import Statevector

        circuit = QuantumCircuit(1)
        circuit.ry(angle, 0)
        probabilities = Statevector.from_instruction(circuit).probabilities()
        return float(probabilities[0] - probabilities[1])
    if sdk == "pennylane":
        import pennylane as qml

        device = qml.device("default.qubit", wires=1, shots=None)

        @qml.qnode(device)
        def circuit(value):
            qml.RY(value, wires=0)
            return qml.expval(qml.Z(0))

        return float(circuit(angle))
    raise ValueError(f"unsupported SDK: {sdk}")


def _features(sdk: str, rows: list[list[float]]) -> list[float]:
    return [
        sum(_expectation(sdk, float(value)) for value in row) / len(row) for row in rows
    ]


def _fit_linear(features: list[float], targets: list[float]) -> dict[str, float]:
    mean_x = sum(features) / len(features)
    mean_y = sum(targets) / len(targets)
    variance = sum((value - mean_x) ** 2 for value in features)
    slope = (
        sum(
            (value - mean_x) * (target - mean_y)
            for value, target in zip(features, targets, strict=True)
        )
        / variance
        if variance > 1e-12
        else 0.0
    )
    return {"slope": slope, "intercept": mean_y - slope * mean_x}


def _default_training_data(profile: str) -> tuple[list[list[float]], list[float]]:
    rows = [[0.1], [0.4], [1.2], [1.5]]
    if profile in {"quantum_kernel", "variational_supervised", "hybrid_neural"}:
        return rows, [0.0, 0.0, 1.0, 1.0]
    return rows, [0.1, 0.4, 1.2, 1.5]


def _qiskit_optimizer(fun, x0, jac=None, bounds=None):
    from scipy.optimize import minimize

    del jac, bounds
    return minimize(
        fun,
        x0,
        method="COBYLA",
        options={"maxiter": max(4, len(x0) + 2)},
    )


def _train_qiskit_native(
    descriptor: dict[str, Any],
    model_path: Path,
    rows: list[list[float]],
    targets: list[float],
) -> dict[str, Any]:
    import numpy as np
    from qiskit.circuit.library import real_amplitudes, z_feature_map
    from qiskit_machine_learning.algorithms import QSVC, QSVR, VQC, VQR
    from qiskit_machine_learning.kernels import FidelityStatevectorKernel

    profile = descriptor["profile"]
    variant = descriptor["selected_variant"]
    features = np.asarray(rows, dtype=float)
    labels = np.asarray(targets)
    feature_map = z_feature_map(feature_dimension=features.shape[1], reps=1)
    if profile == "quantum_kernel":
        kernel = FidelityStatevectorKernel(feature_map=feature_map)
        model = (
            QSVR(quantum_kernel=kernel)
            if variant == "qsvr"
            else QSVC(quantum_kernel=kernel)
        )
    else:
        ansatz = real_amplitudes(features.shape[1], reps=1)
        model = (
            VQR(
                num_qubits=features.shape[1],
                feature_map=feature_map,
                ansatz=ansatz,
                optimizer=_qiskit_optimizer,
            )
            if variant == "vqr"
            else VQC(
                num_qubits=features.shape[1],
                feature_map=feature_map,
                ansatz=ansatz,
                optimizer=_qiskit_optimizer,
            )
        )
    model.fit(features, labels)
    model.to_dill(str(model_path))
    return {
        "backend": type(model).__name__,
        "training_samples": len(rows),
        "model_file": model_path.as_posix(),
    }


def _build_qiskit_torch_layer():
    from qiskit import QuantumCircuit
    from qiskit.circuit import Parameter, ParameterVector
    from qiskit_machine_learning.connectors import TorchConnector
    from qiskit_machine_learning.neural_networks import EstimatorQNN

    feature = Parameter("feature")
    weights = ParameterVector("weight", 2)
    circuit = QuantumCircuit(1)
    circuit.ry(feature, 0)
    circuit.ry(weights[0], 0)
    circuit.rz(weights[1], 0)
    qnn = EstimatorQNN(
        circuit=circuit,
        input_params=[feature],
        weight_params=list(weights),
        input_gradients=True,
    )
    return TorchConnector(
        qnn,
        initial_weights=[0.1, -0.2],
    )


def _build_pennylane_torch_layer():
    import pennylane as qml
    import torch

    device = qml.device("default.qubit", wires=1, shots=None)

    @qml.qnode(device, interface="torch")
    def circuit(inputs, weights):
        qml.RY(inputs[..., 0], wires=0)
        qml.RY(weights[0], wires=0)
        qml.RZ(weights[1], wires=0)
        return qml.expval(qml.Z(0))

    return qml.qnn.TorchLayer(
        circuit,
        {"weights": (2,)},
        init_method=lambda tensor: torch.nn.init.constant_(tensor, 0.1),
    )


def _train_hybrid_native(
    descriptor: dict[str, Any],
    model_path: Path,
    rows: list[list[float]],
    targets: list[float],
) -> dict[str, Any]:
    import torch

    torch.manual_seed(7)
    layer = (
        _build_qiskit_torch_layer()
        if descriptor["sdk"] == "qiskit"
        else _build_pennylane_torch_layer()
    )
    optimizer = torch.optim.SGD(layer.parameters(), lr=0.1)
    inputs = torch.tensor(rows, dtype=torch.float32)
    labels = torch.tensor(targets, dtype=torch.float32)
    for _ in range(2):
        optimizer.zero_grad()
        predictions = layer(inputs).reshape(-1)
        loss = torch.mean((predictions - labels) ** 2)
        loss.backward()
        optimizer.step()
    torch.save(layer.state_dict(), model_path)
    return {
        "backend": type(layer).__name__,
        "training_samples": len(rows),
        "model_file": model_path.as_posix(),
        "final_loss": float(loss.detach()),
    }


def _train_framework_adapter(
    descriptor: dict[str, Any],
    model_path: Path,
    rows: list[list[float]],
    targets: list[float],
) -> dict[str, Any]:
    profile = descriptor["profile"]
    state: dict[str, Any] = {
        "adapter_id": descriptor["adapter_id"],
        "adapter_version": descriptor["adapter_version"],
    }
    if profile in {
        "quantum_kernel",
        "variational_supervised",
        "hybrid_neural",
        "quantum_reservoir",
    }:
        state["linear"] = _fit_linear(_features(descriptor["sdk"], rows), targets)
    elif profile == "quantum_generative":
        state["probability"] = sum(targets) / len(targets)
    elif profile == "quantum_representation":
        state["center"] = sum(_features(descriptor["sdk"], rows)) / len(rows)
    elif profile == "quantum_reinforcement":
        state["action_values"] = targets[:2]
    else:
        raise ValueError(f"unsupported profile: {profile}")
    model_path.write_text(json.dumps(state, sort_keys=True))
    return {
        "backend": "framework_official_primitives",
        "training_samples": len(rows),
        "model_file": model_path.as_posix(),
    }


def train_and_save(
    model_path: str | Path,
    rows: list[list[float]] | None = None,
    targets: list[float] | None = None,
) -> dict[str, Any]:
    descriptor = _descriptor()
    profile = descriptor["profile"]
    default_rows, default_targets = _default_training_data(profile)
    rows = rows or default_rows
    targets = targets or default_targets
    if len(rows) != len(targets) or not rows or any(not row for row in rows):
        raise ValueError("training rows and targets must be non-empty and aligned")
    path = Path(model_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if descriptor["sdk"] == "qiskit" and profile in {
        "quantum_kernel",
        "variational_supervised",
    }:
        return _train_qiskit_native(descriptor, path, rows, targets)
    if profile == "hybrid_neural" and descriptor["sdk"] in {
        "qiskit",
        "pennylane",
    }:
        return _train_hybrid_native(descriptor, path, rows, targets)
    return _train_framework_adapter(descriptor, path, rows, targets)


def _load_qiskit_native(
    descriptor: dict[str, Any], model_path: Path, features: list[float]
) -> float:
    import numpy as np
    from qiskit_machine_learning.algorithms import QSVC, QSVR, VQC, VQR

    model_type = {
        ("quantum_kernel", "qsvc"): QSVC,
        ("quantum_kernel", "qsvr"): QSVR,
        ("variational_supervised", "vqc"): VQC,
        ("variational_supervised", "vqr"): VQR,
    }.get((descriptor["profile"], descriptor["selected_variant"]))
    if model_type is None:
        raise ValueError("selected Qiskit native variant is unsupported")
    model = model_type.from_dill(str(model_path))
    prediction = np.asarray(model.predict(np.asarray([features], dtype=float))).reshape(
        -1
    )
    return float(prediction[0])


def _load_hybrid_native(
    descriptor: dict[str, Any], model_path: Path, features: list[float]
) -> float:
    import torch

    layer = (
        _build_qiskit_torch_layer()
        if descriptor["sdk"] == "qiskit"
        else _build_pennylane_torch_layer()
    )
    layer.load_state_dict(torch.load(model_path, weights_only=True))
    with torch.no_grad():
        return float(
            layer(torch.tensor([features], dtype=torch.float32)).reshape(-1)[0]
        )


def load_and_infer(
    model_path: str | Path, request: dict[str, Any] | None = None
) -> dict[str, Any]:
    descriptor = _descriptor()
    path = Path(model_path)
    if not path.is_file():
        raise ValueError(f"model file does not exist: {path}")
    request = request or {"features": [0.25], "shots": 8, "actions": 2}
    values = [float(value) for value in request.get("features", [0.25])]
    if not values:
        raise ValueError("features must not be empty")
    profile = descriptor["profile"]
    if descriptor["sdk"] == "qiskit" and profile in {
        "quantum_kernel",
        "variational_supervised",
    }:
        value = _load_qiskit_native(descriptor, path, values)
        return {"operation": "predict", "value": value}
    if profile == "hybrid_neural" and descriptor["sdk"] in {
        "qiskit",
        "pennylane",
    }:
        value = _load_hybrid_native(descriptor, path, values)
        return {"operation": "predict", "value": value}

    state = json.loads(path.read_text())
    if (
        state.get("adapter_id") != descriptor["adapter_id"]
        or state.get("adapter_version") != descriptor["adapter_version"]
    ):
        raise ValueError("model state does not belong to the materialized adapter")
    quantum_features = [_expectation(descriptor["sdk"], value) for value in values]
    mean = sum(quantum_features) / len(quantum_features)
    if profile in {
        "quantum_kernel",
        "variational_supervised",
        "hybrid_neural",
        "quantum_reservoir",
    }:
        linear = state["linear"]
        return {
            "operation": "predict",
            "value": linear["slope"] * mean + linear["intercept"],
        }
    if profile == "quantum_generative":
        shots = int(request.get("shots", 8))
        probability = min(1.0, max(0.0, float(state["probability"])))
        samples = [
            1 if ((index + 0.5) / shots) <= probability else 0 for index in range(shots)
        ]
        return {"operation": "sample", "samples": samples}
    if profile == "quantum_representation":
        return {
            "operation": "transform",
            "embedding": [value - state["center"] for value in quantum_features],
        }
    if profile == "quantum_reinforcement":
        action_values = state["action_values"]
        return {
            "operation": "act",
            "action": max(range(len(action_values)), key=action_values.__getitem__),
            "action_values": action_values,
        }
    raise ValueError(f"unsupported profile: {profile}")


def infer(request: dict[str, Any]) -> dict[str, Any]:
    descriptor = _descriptor()
    values = [float(value) for value in request.get("features", [0.25])]
    quantum_features = [_expectation(descriptor["sdk"], value) for value in values]
    mean = sum(quantum_features) / len(quantum_features)
    operation = descriptor["operation"]
    if operation == "predict":
        return {"operation": operation, "value": mean}
    if operation == "sample":
        return {"operation": operation, "samples": [int(mean >= 0.0)]}
    if operation == "transform":
        return {"operation": operation, "embedding": quantum_features}
    return {"operation": operation, "action": int(mean < 0.0)}


def smoke(model_path: str | Path | None = None) -> dict[str, Any]:
    path = Path(model_path or Path(__file__).with_name("smoke-model.bin"))
    training = train_and_save(path)
    result = load_and_infer(path)
    if model_path is None:
        path.unlink(missing_ok=True)
    return {
        "status": "passed",
        "adapter": _descriptor()["adapter_id"],
        "training": training,
        "result": result,
    }


if __name__ == "__main__":
    print(json.dumps(smoke(), separators=(",", ":")))
