---
name: quantum-algorithm-qaoa
description: "Guides SDK-neutral QAOA application engineering for QUBO/Ising optimization, MaxCut, portfolio selection, scheduling, unit commitment, knapsack/TSP-like problems, penalty design, feasible decoding, baseline comparison, and quantum_report.md evidence. Use after the user selects Cqlib, Qiskit, or PennyLane and the project records quantum_runtime. Load only the selected SDK reference. Do NOT use for VQE, QML, hybrid neural models, application packaging, or final delivery readiness."
name_cn: 量子组合优化
description_cn: 专业的量子近似优化算法（QAOA）开发工具。支持 QUBO/Ising 模型构建与 MaxCut 等组合优化问题求解，提供经典基线对比及多量子 SDK 的底层代码适配。
---

# Quantum Algorithm: QAOA

Build a reviewable QAOA application without coupling the problem model or evidence contract to a quantum SDK.

## When to Use

- The task is binary combinatorial optimization and can be expressed as QUBO or Ising.
- The application needs constraint penalties, top-k feasible decoding, and comparison with a classical solver.
- The selected SDK is recorded in `quantum_runtime.sdk` before implementation.

## When NOT to Use

- Ground-state or molecular energy work -> `quantum-algorithm-vqe`.
- Classification, regression, or feature maps -> `quantum-algorithm-qml`.
- A larger classical model containing a quantum layer -> `quantum-algorithm-hybrid`.
- API, UI, packaging, or delivery decisions. Use `qccp-service`, `qccp-ui`, or `qccp-frontend` when those concerns are explicitly in scope.

## Load the Selected SDK Reference

Read exactly one implementation reference after the user has selected an SDK:

| `quantum_runtime.sdk` | Reference | Local simulator |
|---|---|---|
| `cqlib` | `references/cqlib.md` | verified |
| `qiskit` | `references/qiskit.md` | verified |
| `pennylane` | `references/pennylane.md` | verified |

Do not load or mix code from another SDK. TianYan and QCIS execution are Cqlib-only capabilities in this release.

## Implementation Reuse Gate

Before writing quantum algorithm code:

1. Inspect the active environment, dependency lockfiles, installed package versions, and existing project utilities.
2. Inventory the selected SDK's QAOA algorithm, optimization-model converters, ansatz/layer helpers, optimizers, primitives, and result decoders.
3. Use the highest-level supported library implementation that preserves the required QUBO, mixer, parameter, sampling, and decoding contracts.
4. Record the fully qualified components and versions selected for production execution.

Do not reimplement a standard QAOA ansatz, optimization loop, QUBO converter, optimizer, sampler wrapper, or result container when a compatible maintained implementation is available. Custom quantum code is allowed only for a required unsupported mixer/ansatz, a missing capability in the selected SDK, or a tiny independent semantic oracle. Record the exact reason and keep validation-only code out of the production path. A missing optional package is a dependency blocker; do not silently replace it with a handwritten production implementation without user approval.

## Required Contracts

Before coding, define:

- binary variables and stable variable-to-qubit mapping
- original objective, optimization direction, and known bounds when available
- each constraint, violation function, and penalty coefficient
- QUBO convention, constant offset, and QUBO-to-Ising conversion
- QAOA depth, parameter order, mixer, initial state, and optimizer budget
- bitstring convention, decoding, feasibility check, and tie-breaking
- exact or heuristic classical baseline on the same instance
- seeds, execution mode, shots, backend, tolerances, and allowed claims

Keep the original objective separate from penalty energy. Rank candidate solutions by feasibility and original objective, not only by penalized energy.

## Planning Handoff

Before implementation, provide planner-agent the instance family, variable count,
constraint types, exact-solver limit, and any allowed TianYan execution. The plan must
freeze a tiny semantic oracle, feasible-solution rule, original-objective metric, and
resource escalation trigger. It must not select depth or penalty values only because a
generic template suggests them.

## Required Outputs

- `artifacts/results/qaoa_model.json`: variables, objective, constraints, penalties, QUBO coefficients, Ising coefficients, constant offset, and bit order.
- `artifacts/results/qaoa_trace.json`: evaluation index, parameters, expectation, best feasible objective, feasible rate, and optimizer status.
- `artifacts/results/qaoa_samples.json`: top-k bitstrings, decoded variables, probability or count, feasibility, violations, and original objective.
- `artifacts/reports/quantum_report.md`: runtime, implementation strategy, fully qualified library components and versions, custom-code justification, qubits, depth, optimizer settings, best feasible solution, commands, artifacts, and limitations.

## Workflow

1. Normalize the application instance into binary variables.
2. Implement the original objective and constraints as classical functions first.
3. Build and exhaustively verify the QUBO/Ising model on a tiny instance.
4. Declare the bit order and parameter order before selecting the implementation.
5. Load the selected SDK reference, pass the reuse gate, and configure the selected library QAOA path.
6. Run exact probabilities or seeded shots on an authorized local backend.
7. Decode top-k states, score feasibility, and compare with the classical baseline.
8. Write the required artifacts and run the project's scientific and application checks when available.

## Modeling Rules

- State whether the QUBO is upper-triangular, symmetric, or full-matrix form.
- Record the constant offset even when it does not affect the optimizer.
- Choose penalties from objective-scale bounds or a documented empirical sweep.
- Treat zero feasible samples as a modeling or search failure, not a successful run.
- Test one-hot, cardinality, capacity, and balance constraints independently.
- Preserve qubit indexing, parameter ordering, gate ordering, and measurement mapping across implementation and report artifacts.

## Optimization and Validation

- Start with shallow depth and deterministic seeds; increase depth only with evidence.
- Record initial points, bounds or periodic normalization, restarts, evaluation count, and stopping reason.
- Validate the energy function against direct QUBO evaluation for known bitstrings.
- Validate decoding with one- and two-qubit states whose expected bit order is obvious.
- Compare baseline and QAOA using the same instance, objective direction, feasibility rules, and metric.
- Never claim quantum advantage from simulator-only or single-instance evidence.
- Never silently change SDK or backend after a failure. Return to the lifecycle selection step.

## Application Handoff

Treat `application_manifest.json` as application source. Record algorithm result and report paths
plus `quantum_runtime` in code-owned evidence, and update the manifest with matching implementation
changes when endpoints, fixtures, assets, entrypoints, or selectors change. This skill contributes
algorithm evidence only and cannot declare the application ready.
