# PennyLane SDK Contract

## Selection Boundary

Use PennyLane only when the selected `QMLRoute` names `sdk=pennylane`, the installed version
passes capability inspection, and the selected variant completes its own materialized smoke.
A working QNode does not by itself prove a kernel, reservoir, generative, representation, or
reinforcement implementation.

## Library-First Components

- Use a QNode with a local device and an explicit interface.
- Prefer maintained embeddings and ansatz templates.
- Use `pennylane.qnn.TorchLayer` for PyTorch integration instead of a custom autograd bridge.
- Select `backprop`, parameter shift, or another differentiation method from actual device
  capability and test it.

## Runtime Adapter

Call `materialize_qml_adapter`, then use:

```python
from algorithm.qml_runtime.runtime import load_and_infer, train_and_save

train_and_save("models/qml-model.bin", rows=train_rows, targets=train_targets)
result = load_and_infer("models/qml-model.bin", fixture_request)
```

Use the framework-owned profile adapter where PennyLane provides differentiable primitives
but no complete high-level learning algorithm. Keep tensors connected through the loss and
record the optimizer outside the QNode. Use `TorchLayer` for compatible PyTorch hybrid routes;
do not create a custom autograd bridge or duplicate the materialized circuit.

## Parameter and Measurement Semantics

Record device, wire labels and output order, shots, interface, differentiation method,
embedding range, template and weight shapes, observable order, tensor dtype/device, and batch
semantics. Keep trainable arguments visible to the selected interface and verify both input and
weight gradients when required.

## Persistence

Persist the materialized architecture configuration and framework state under `models/`.
Record PennyLane and PyTorch versions, preprocessing, route, parameter shapes, model hash, and
known fixture in the inference bundle. Rebuild the same QNode/TorchLayer and load the state in
a fresh process before acceptance.

## Unsupported Behavior

If the framework-owned adapter does not exercise the selected variant's actual structure and
training semantics, return unavailable. Do not relabel a generic `TorchLayer` as QCNN, QLSTM,
quanvolution, qGAN, autoencoder, reservoir, or reinforcement learner. Do not switch device,
SDK, differentiation method, or shots silently.

## Evidence

Record PennyLane and PyTorch versions, device, shots, interface, differentiation method,
wire/output mapping, template names, finite nonzero gradients or declared non-gradient path,
seeds, adapter and model hashes, reload fixture, and limitations. External plugins and cloud
devices are outside this local Skill.
