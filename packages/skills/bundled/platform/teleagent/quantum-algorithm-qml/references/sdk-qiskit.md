# Qiskit SDK Contract

## Selection Boundary

Use Qiskit only when the selected `QMLRoute` names `sdk=qiskit`, installed Qiskit and Qiskit
Machine Learning versions pass capability inspection, and the selected variant completes its
own materialized smoke. Do not infer variant support from a successful one-qubit primitive.

## Library-First Components

- Quantum kernels: `FidelityQuantumKernel`, `FidelityStatevectorKernel`, `QSVC`, `QSVR`.
- Supervised variational models: `VQC`, `VQR`, `NeuralNetworkClassifier`,
  `NeuralNetworkRegressor`.
- Custom QNN outputs: `EstimatorQNN` or `SamplerQNN`.
- PyTorch integration: `TorchConnector`.

Use installed Qiskit 2.x and Qiskit Machine Learning 0.9.x signatures. Do not use removed
`QuantumKernel`, `CircuitQNN`, or `TwoLayerQNN`.

## Runtime Adapter

Call `materialize_qml_adapter`, then use:

```python
from algorithm.qml_runtime.runtime import load_and_infer, train_and_save

train_and_save("models/qml-model.bin", rows=train_rows, targets=train_targets)
result = load_and_infer("models/qml-model.bin", fixture_request)
```

For kernel and variational-supervised routes, reuse the maintained model selected by the
adapter. For compatible hybrid routes, reuse `EstimatorQNN` or `SamplerQNN` through
`TorchConnector`. Application code configures data and experiment parameters; it must not
duplicate the QNN, kernel, optimizer bridge, or serialization logic.

## Parameter and Measurement Semantics

Keep feature parameters and trainable weight parameters separate and ordered. Record circuit
qubit order, primitive/backend, observables, sampler interpretation, output shape, class
mapping, shots, seed, and transpilation assumptions. Set `input_gradients=True` when a
PyTorch-connected upstream layer requires input gradients and verify the resulting tensor.

## Persistence

Use the materialized runtime's format rather than raw ad hoc pickling. Persist preprocessing,
route and adapter versions, feature/weight ordering, interpretation, model hash, and known
fixture in the inference bundle. Verify `from_dill` or the adapter-selected reload path in a
fresh process.

## Unsupported Behavior

For reservoirs, generative, representation, and reinforcement profiles, use the
framework-owned adapter built from current Qiskit circuit/statevector/primitives APIs. Do not
claim Qiskit supplies a high-level algorithm when it supplies only primitives.

If that adapter does not exercise the selected variant's real training and inference
semantics, return unavailable. Do not map clustering to `QSVC`, map qGAN to threshold sampling,
or replace the selected route with another SDK or handwritten approximation.

## Evidence

Record Qiskit and Qiskit Machine Learning versions, selected fully qualified components,
primitive/backend, input and weight parameter partitions, output interpretation, gradients,
shots, seeds, adapter and model hashes, reload fixture, and limitations. Hardware and IBM
Runtime are outside this local Skill.
