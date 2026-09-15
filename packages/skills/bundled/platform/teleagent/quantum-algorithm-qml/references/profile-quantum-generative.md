# Quantum Generative Profile

## Use

Use for Born machines or qGAN variants that learn or sample a target distribution.

## Variant Scope

- `born_machine`: a parameterized quantum distribution trained against a target distribution.
- `qgan`: a quantum generator with an explicitly identified classical or quantum
  discriminator.

Do not call deterministic thresholding or resampling a generative quantum model.

## Data and Encoding

Define target support, normalization, discretization, latent or conditioning inputs, train/test
separation, invalid-sample policy, bit/wire ordering, and mapping between measured bitstrings
and domain samples.

## Model and Training

Record generator circuit, initial state, trainable parameters, discriminator when present,
objective, optimizer schedules, update ratio, shots, seeds, stopping criteria, and circuit
evaluation count. Keep generator and discriminator checkpoints distinct.

## Measurement and Output

The inference operation is `sample`. Return samples in the declared domain together with shot
count and optional probabilities; do not expose classification logits as generated samples.
Persist support mapping, wire order, generator state, and conditioning schema.

## Diagnostics

Report distribution distance, coverage, mode collapse indicators, seed and shot variance,
training stability, memorization checks, sample validity, and comparison with a matched
classical generator. Do not report classification accuracy as the primary result.

## Failure Modes

- Output samples are unrelated to quantum measurements.
- Mode collapse, invalid support values, or probability normalization errors.
- Generator/discriminator update imbalance or unstable adversarial loss.
- Training examples are replayed and reported as generated samples.
- A selected qGAN route has no discriminator implementation.

## Acceptance

Require normalized measured probabilities, valid-domain samples, held-out distribution
metrics, coverage and collapse diagnostics, multiple seeds or an explicit limitation,
serialized generator reload, and a known seeded sampling fixture.
