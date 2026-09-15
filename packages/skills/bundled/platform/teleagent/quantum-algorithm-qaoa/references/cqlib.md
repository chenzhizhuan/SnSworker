# Cqlib QAOA Adapter

## Support Status

- Local exact probabilities and seeded sampling: `verified`
- TianYan and QCIS workflow: `experimental` until an authorized job is run
- Native differentiable QAOA execution: `unsupported` unless the active Cqlib version proves otherwise

Inspect the installed Cqlib API before implementation. Do not infer behavior from a private checkout or another version.

## Reuse-First Capability Check

Search the installed Cqlib package, its bundled examples, and the active project for a maintained QAOA solver, QUBO/Ising converter, ansatz builder, optimizer adapter, or result decoder. Reuse every compatible component found and record its import path and version. Do not recreate a project-local implementation under a new name.

If no maintained algorithm layer exists, record the inspected modules and missing capabilities before using the fallback circuit below. The fallback is allowed because of a demonstrated Cqlib capability gap, not merely because handwritten code is convenient.

## Fallback Circuit Pattern

Declare every parameter and keep the order `gamma_0..gamma_p-1`, then `beta_0..beta_p-1`.

```python
import numpy as np
from cqlib import Circuit, Parameter


def build_qaoa(n_qubits, linear, quadratic, layers):
    names = [f"gamma_{i}" for i in range(layers)] + [f"beta_{i}" for i in range(layers)]
    circuit = Circuit(n_qubits, parameters=names)
    for q in range(n_qubits):
        circuit.h(q)

    for layer in range(layers):
        gamma = Parameter(f"gamma_{layer}")
        beta = Parameter(f"beta_{layer}")
        for q, coeff in linear.items():
            circuit.rz(q, 2.0 * coeff * gamma)
        for (u, v), coeff in quadratic.items():
            circuit.cx(u, v)
            circuit.rz(v, 2.0 * coeff * gamma)
            circuit.cx(u, v)
        for q in range(n_qubits):
            circuit.rx(q, 2.0 * beta)
    circuit.measure_all()
    return circuit, names


def bind(circuit, names, values):
    return circuit.assign_parameters(dict(zip(names, np.asarray(values, dtype=float), strict=True)))
```

Confirm the sign and factor convention by comparing circuit energies with direct Ising energies. Use a verified native `rzz` only when the active version exposes it; otherwise retain CNOT-RZ-CNOT.

## Execution and Bit Order

```python
from cqlib.simulator import StatevectorSimulator

bound = bind(circuit, names, values)
sim = StatevectorSimulator(circuit=bound)
probabilities = sim.measure()
counts = sim.sample(shots=2048, rng_seed=123)
```

Existing Cqlib examples map qubit `q` from `bitstring[-1 - q]`. Prove that convention with known basis states before decoding application variables.

## Cloud Boundary

- Use externalized credentials only.
- Preserve QCIS, machine name, shots, transpilation settings, query IDs, and raw result schema.
- Never fall back to a local simulator after a TianYan failure without a new user decision.
- Treat TianYan evidence as experimental until the exact project job is authorized and retrieved.

## Adapter Checklist

- Active Cqlib version and imports are recorded.
- Parameter order and bit order have focused tests.
- Sampling uses a seed and tolerant assertions.
- The report records `sdk: cqlib`, backend metadata, shots, seed, and limitations.
- The report lists reused Cqlib/project components or the evidence supporting each fallback component.
