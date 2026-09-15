# Quantum Reservoir Profile

## Use

Use for forecasting, classification, regression, or anomaly detection with a fixed quantum
reservoir and trained classical readout.

## Variant Scope

Variants are `forecasting`, `classification`, `regression`, and `anomaly_detection`. All use a
fixed quantum reservoir and a separately trained readout; a trainable variational circuit is
not a reservoir merely because it processes a sequence.

## Data and Encoding

Use chronological splitting for temporal tasks and leakage-safe splitting otherwise. Define
input injection, timestep, context window, washout, missing-value handling, scaling fit on
training data, reservoir reset policy, and rollout horizon.

## Model and Training

Record reservoir circuit, depth, wires, fixed random seed, evolution rule, measured features,
memory depth, shots, and backend. Freeze every reservoir parameter. Train only the declared
classical readout and persist both reservoir configuration and readout state.

## Measurement and Output

Preserve timestep and feature ordering. Define one-step versus recursive rollout, class or
regression decoding, anomaly score and threshold when applicable, and state reset between
independent samples.

## Diagnostics

Prove reservoir parameters remain fixed, train only the readout, compare against persistence
and matched classical reservoirs, report memory/forecast metrics by horizon, seed variance,
feature rank, and temporal leakage checks.

## Failure Modes

- Reservoir parameters change during readout training.
- Random train/test shuffling leaks future information.
- Hidden state crosses independent sequences without a declared stateful protocol.
- Recursive forecasting is evaluated as teacher-forced one-step prediction.
- Quantum features are constant, rank deficient, or replaced by raw inputs.

## Acceptance

Require an immutable reservoir hash before and after training, leakage-safe evaluation,
readout-only optimization, horizon-specific metrics, matched persistence and classical
reservoir baselines, clean reload, and a known state-reset inference fixture.
