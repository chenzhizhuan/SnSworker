# PennyLane QAOA Adapter

## Support Status

- `default.qubit` exact-probability QAOA: `verified`
- Autograd/PyTorch optimization on supported local devices: `verified`
- External plugins, cloud devices, or hardware execution: outside this skill's verified path

Use the PennyLane version range declared by the active project and verify device/differentiation compatibility at runtime.

## Library-First Path

- Use `qml.qaoa` cost-Hamiltonian helpers for supported graph problems and `qml.qaoa.x_mixer`, `bit_flip_mixer`, or another maintained mixer helper when it matches the contract.
- Use `qml.qaoa.cost_layer`, `qml.qaoa.mixer_layer`, and `qml.layer` instead of manually decomposing standard QAOA evolution into rotations and CNOTs.
- Use a maintained PennyLane optimizer compatible with the selected interface.
- Retain independent neutral QUBO scoring and feasibility decoding outside the QNode.

For a custom QUBO, construct a validated PennyLane Hamiltonian and still reuse the maintained layer/evolution helpers. Handwrite a layer only when the required Hamiltonian or mixer is unsupported, and record that incompatibility.
A thin objective/update loop that calls the maintained QNode and optimizer is acceptable because PennyLane exposes QAOA as composable components; do not reimplement optimizer mechanics.

## Independent Validation

- Compare the `qml.qaoa` cost Hamiltonian with direct QUBO energies for every bitstring of a tiny instance.
- Evaluate one fixed parameter point through the maintained cost/mixer layers and independently score its probability distribution.
- Test wire-to-bitstring decoding with prepared basis states; do not recreate QAOA for this test.
- Recompute feasibility and the original objective outside the QNode.

`qml.probs` returns probabilities in the device's documented wire order. Convert indices to fixed-width bitstrings and test the mapping with prepared basis states before application decoding.

## Optimization

- Keep `gamma` and `beta` shapes explicit and stable across restarts.
- Use `shots=None` for deterministic semantic checks; use finite shots only when required by the application contract.
- Record the QNode interface and `diff_method` selected by the device.
- Verify at least one nonzero finite gradient before claiming differentiable optimization.

## Adapter Checklist

- Device name, shots, seed, interface, and differentiation method are recorded.
- Probability-to-bitstring mapping has a focused test.
- Energy matches direct Ising evaluation on a known parameter point.
- The report records `sdk: pennylane` and contains no cloud or hardware claim.
- The report records the `qml.qaoa` components used or the exact unsupported requirement that forced custom code.
