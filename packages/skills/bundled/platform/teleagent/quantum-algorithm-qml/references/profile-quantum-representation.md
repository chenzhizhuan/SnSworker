# Quantum Representation Profile

## Use

Use for quantum autoencoders, variational embeddings, compression, reconstruction, or learned
representations.

## Variant Scope

- `quantum_autoencoder`: compresses quantum states into latent wires with explicit trash or
  reconstruction semantics.
- `variational_embedding`: learns an embedding used through the `transform` operation.

Centering a fixed quantum feature is not a trained autoencoder or variational embedding.

## Data and Encoding

Declare `classical_data` or `quantum_data`, state-preparation or feature encoding, normalization,
wire order, train/test split, latent/trash partition, and input validity checks. Quantum data
must preserve state dimension and normalization.

## Model and Training

Define encoder, decoder when present, latent dimension, compression ratio, trainable
parameters, reconstruction or fidelity objective, optimizer, gradient method, seeds, shots,
and stopping criteria. Persist circuit structure and latent/trash wire mapping.

## Measurement and Output

The operation is `transform`. Define whether output is a classical embedding, latent quantum
state description, or reconstructed-state metric. Never claim state reconstruction when only
classical measured features are returned.

## Diagnostics

Report reconstruction error or fidelity, compression ratio, latent stability, train/test gap,
downstream utility when claimed, seed variance, and comparison with matched classical
dimensionality reduction or autoencoding.

## Failure Modes

- Invalid or unnormalized quantum states.
- Latent and trash wires swapped during measurement or reload.
- Trivial identity mapping presented as compression.
- Objective improves without held-out fidelity or downstream utility.
- A fixed feature map is mislabeled as a trained variational embedding.

## Acceptance

Require explicit data domain, compression and wire contract, finite objective, held-out
reconstruction or embedding metrics, matched classical comparison, clean reload, and fixture
reproduction under the exact `transform` schema.
