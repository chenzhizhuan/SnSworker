# Hybrid Neural Profile

## Use

Use when a classical encoder, CNN, recurrent model, or other neural component contains a
quantum head, feature extractor, serial/parallel/residual block, QCNN, QLSTM, or quanvolution
variant.

## Variant Scope

Supported route labels include `quantum_head`, `qcnn`, `qlstm`, `quanvolution`, `serial`,
`parallel`, and `residual`. A generic quantum layer only proves `quantum_head`; claim QCNN,
QLSTM, quanvolution, or a composition variant only when the materialized adapter implements
that architecture and its state contract.

## Data and Encoding

Define classical input and target shapes, batch dimension, feature order, train-only
preprocessing, projection into the circuit input range, qubit/wire count, and tensor
dtype/device. For images and sequences, define patch, timestep, hidden-state, padding, and
aggregation semantics explicitly.

## Model and Training

Separate classical encoder, quantum layer, and classical head. Record tensor shapes at each
boundary, parameter ownership, optimizer groups, initialization, gradient method, loss,
freezing schedule, seeds, shots, and checkpoint contents. Use `TorchConnector` or `TorchLayer`
when selected instead of a custom autograd bridge.

## Measurement and Output

Define observables, wire-to-feature order, quantum output shape, classical decoding, and final
operation. Persist both quantum and classical parameters plus preprocessing and architecture
configuration. A service must load the complete checkpoint without constructing a training
optimizer.

## Diagnostics

Compare classical-only, quantum-disabled, and hybrid ablations on the same split. Verify input
and quantum-weight gradients, one effective quantum update, tensor connectivity, runtime per
sample/epoch, seed variance, and clean-process bundle loading.

## Failure Modes

- Detached tensors, dtype/device conversion, or missing quantum-parameter gradients.
- Shape changes hidden by broadcasting or flattening.
- Calling a one-layer quantum head QCNN, QLSTM, or quanvolution without structural evidence.
- Saving only classical or only quantum weights.
- Training triggered by application startup or inference requests.

## Acceptance

Require explicit intermediate shapes, finite connected gradients or a declared non-gradient
path, one quantum-weight update, matched ablations, held-out metrics, complete checkpoint
reload, fixture reproduction, and inference without optimizer or training-data access.
