# Qiskit QAOA Adapter

## Support Status

- Local statevector QAOA and seeded decoding: `verified`
- Qiskit Optimization/Qiskit Algorithms integration: `verified` for the version-matched path
- IBM Runtime or hardware execution: outside this skill's verified path

Target the dependency range declared by the active project and inspect active signatures before using optional APIs. Qiskit Optimization 0.7.x provides `qiskit_optimization.minimum_eigensolvers.QAOA`; older supported stacks may provide `qiskit_algorithms.QAOA`. Never combine imports copied from different release lines.

## Library-First Path

Prefer these maintained components when present and compatible:

1. `qiskit_optimization.problems.QuadraticProgram` and its converters for supported application models.
2. The installed release's `QAOA` minimum eigensolver with a supported Sampler primitive and optimizer.
3. `qiskit_optimization.algorithms.MinimumEigenOptimizer` for compatibility checks, QUBO conversion, solve orchestration, and result decoding.
4. Official optimizer callbacks/result objects for the convergence trace.

Check `MinimumEigenOptimizer.get_compatibility_msg()` before execution. Keep the neutral QUBO evaluator and feasibility decoder independent, but do not duplicate the production QAOA ansatz or solver loop.

## Independent Validation

- Compare the library-produced Ising operator with direct QUBO energies for every bitstring of a tiny instance.
- Evaluate one fixed parameter point through the selected library ansatz and independently score its returned distribution.
- Test decoding with prepared basis states; this may use basic state preparation but must not recreate QAOA.
- Recompute feasibility and the original objective outside Qiskit's optimization result.

Qiskit bitstrings display the highest classical/qubit index on the left for the standard register layout. Keep the application mapping explicit and test `q0` against the rightmost bit rather than relying on memory.

## Optimization

- Use the optimizer bundled with or supported by the active QAOA implementation after checking its installed API.
- Seed algorithm globals and any sampler used by the active implementation.
- A direct statevector energy calculation is allowed only as a fixed-point validation check, not as a replacement production optimizer.
- Record whether the objective uses exact probabilities or finite shots.

## Adapter Checklist

- No deprecated blueprint circuit is required by the implementation.
- Parameter order is passed explicitly to assignment.
- The statevector energy matches direct Ising evaluation on known states.
- The report records `sdk: qiskit`, package versions, backend, seed, and limitations.
- No IBM credentials, Runtime service, or hardware job is used by local tests.
- The report distinguishes the library production path from any validation-only native oracle.
