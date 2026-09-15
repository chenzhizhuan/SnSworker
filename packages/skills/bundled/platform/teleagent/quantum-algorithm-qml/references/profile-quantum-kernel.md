# Quantum Kernel Profile

## Use

Use for kernel classification, regression, or clustering when pairwise quantum-state
similarity is the selected evidence-backed route.

## Variant Scope

- `qsvc`: classification with a precomputed or callable quantum kernel.
- `qsvr`: regression with a quantum kernel.
- `kernel_clustering`: unsupervised clustering only when the selected adapter explicitly
  implements a kernel-compatible clustering estimator.

A kernel implementation does not support all three variants merely because it can evaluate
state fidelity. Exercise the selected estimator in the capability smoke.

## Data and Encoding

Use finite numeric features with an explicit feature order, training-only scaling, and a
documented reduction when feature count exceeds available qubits. Record the feature map,
repetitions, data range, qubit count, and duplicate-handling policy. Use the exact same split
and preprocessing contract as the classical kernel baseline.

## Model and Training

Separate kernel evaluation from the classical estimator. Record fidelity method, kernel
regularization or PSD repair, estimator hyperparameters, shots, seed, and any trainable kernel
parameters. Fit preprocessing and estimator state on training data only. Cache matrices only
with dataset, preprocessing, feature-map, backend, shots, and seed hashes.

## Measurement and Output

Return a square training kernel and a test-by-training evaluation kernel with declared sample
ordering. Prediction output must follow the selected operation and include class-label or
regression decoding. Clustering must publish cluster identifiers and its out-of-sample policy;
never present `QSVC` output as clustering.

## Diagnostics

Report kernel symmetry, diagonal, positive-semidefinite tolerance, train/test leakage checks,
off-diagonal variance or concentration, target alignment where justified, shot variance, and
held-out metrics. A valid matrix alone is not evidence of useful separation.

## Failure Modes

- Kernel concentration or near-constant off-diagonal values.
- Non-PSD matrices beyond the declared numerical or shot tolerance.
- Preprocessing leakage or mismatched train/test feature order.
- Excessive duplicate samples, unstable shot estimates, or estimator overfitting.
- A selected variant silently mapped to another estimator.

## Acceptance

Require deterministic sample ordering, leakage-safe preprocessing, kernel sanity checks,
successful estimator serialization and reload, a known prediction fixture, held-out metrics,
and comparison with a matched classical kernel. Report failure when the selected variant lacks
an actual estimator path.
