# Variational Supervised Profile

## Use

Use for variational classification or regression with trainable circuit parameters.

## Variant Scope

- `vqc`: supervised classification with an explicit class interpretation.
- `vqr`: supervised regression with a scalar or declared multi-output interpretation.

Do not infer classification or regression from the target dtype. The selected route fixes the
variant and output contract.

## Data and Encoding

Declare feature order, train-only preprocessing, encoding range, qubit count, feature-map
parameters, label mapping, and train/validation/test split. Document feature reuse or data
re-uploading and reject input dimensions unsupported by the selected circuit.

## Model and Training

Define ansatz, trainable parameter order, initialization, observable or sampler interpretation,
loss, optimizer, gradient method, batching, stopping criteria, seeds, shots, and circuit
evaluation count. Prefer the selected SDK's maintained `VQC` or `VQR` implementation when
available. Custom optimization may configure the adapter but must not reimplement its QNN.

## Measurement and Output

Record measurement outputs before interpretation. For classification, define class-to-output
mapping, decision rule, and probability or score semantics. For regression, define output
range, inverse target transform, and units. Persist parameter and output ordering.

## Diagnostics

Test output shape, parameter sensitivity, finite nonzero gradients or explicit non-gradient
updates, one effective optimizer step, convergence across seeds, train/validation gap, circuit
evaluation count, and shot variance when applicable.

## Failure Modes

- Disconnected or zero gradients without a declared non-gradient optimizer.
- Label/output mismatch, saturated observables, or invalid regression range.
- Parameter-order changes between training and reload.
- Barren-plateau symptoms, unstable seeds, or severe train/validation divergence.
- Replacing failed training with an unreported classical predictor.

## Acceptance

Require one effective parameter update, finite loss and outputs, reproducible parameter
binding, held-out metrics, clean-process reload, fixture reproduction, and comparison with the
matched classical baseline. Report non-convergence or unsupported differentiation honestly.
