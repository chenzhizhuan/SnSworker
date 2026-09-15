---
name: quantum-algorithm-qml
description: "Routes evidence-selected quantum machine-learning work across quantum kernels, variational supervised models, hybrid neural models, quantum reservoirs, generative models, representation learning, and reinforcement learning. Use only for the qml_model workstream after plan.md selects one QMLRoute. Do not use for baseline, research, API/UI, documentation, verification, QAOA, or VQE."
name_cn: 量子机器学习
description_cn: 聚焦量子机器学习领域的全能助手。支持构建量子核方法、混合神经网络及量子生成模型，提供从数据预处理、模型训练到推理验证的端到端工程化支持。
---

# Quantum Machine Learning

QML is the capability domain. Hybrid quantum-classical neural networks are the
`hybrid_neural` profile, not a separate algorithm family.

## Core Contract

- Read the current `selected_route`; never select a profile or SDK from keywords.
- Call `inspect_qml_capabilities` and use `materialize_qml_adapter` before custom code.
- Prefer maintained SDK algorithms and connectors. Use framework-owned official-primitives
  adapters only where the SDK lacks the required high-level model.
- Keep data preparation, encoding, trainable circuit, measurement, loss, optimizer, and
  analysis separately testable.
- Train offline with fixed seeds. Persist parameters, preprocessing, output mapping, package
  versions, expected shapes, and a known inference fixture.
- Services load persisted artifacts and infer only. Never expose training through startup,
  API requests, or browser actions.
- Never silently switch SDK, profile, dataset, metric, backend, or data split.
- Preserve wire order, parameter order, measurement mapping, dtype, shots, and uncertainty.

## Planning Handoff

Planner chooses the QML profile and variant from evidence; this Skill never reselects
them. Before implementation, provide planner-agent the data provenance, task type,
baseline representation, split/resampling boundary, score-to-probability mapping when
applicable, and expected inference operation. The plan must separate a
representation-matched classical comparison from any full-feature classical reference,
and must define threshold selection without consuming the final test set.

## Implementation Workflow

1. Confirm that `selected_route` fixes `profile`, `variant`, `sdk`, `adapter_id`, and
   `adapter_version`.
2. Call `inspect_qml_capabilities`. Dependency availability is necessary but does not by
   itself prove that the selected variant is scientifically implemented.
3. Call `materialize_qml_adapter`. Treat `algorithm/qml_runtime/**` as framework-owned and
   never edit or reproduce its core algorithm in application code.
4. In an application-owned offline training script, import `train_and_save` from
   `algorithm.qml_runtime.runtime` and write the model under `models/`.
5. In a fresh process, call `load_and_infer` with the persisted model and the known fixture.
   Production service and UI paths use this load-and-infer path only.
6. If the selected variant cannot complete its own train, serialize, reload, and infer smoke,
   report the capability as unavailable. Do not substitute another variant, SDK, or handwritten
   approximation.

The materialized runtime is an executable asset, not implementation documentation. Do not read
the complete `assets/runtime.py` during normal work; load only the selected SDK reference
sections needed to integrate it.

## Progressive Disclosure

Load exactly one profile reference and, only when implementation detail is needed, exactly
one SDK reference.

| QML profile | Reference |
|---|---|
| `quantum_kernel` | `references/profile-quantum-kernel.md` |
| `variational_supervised` | `references/profile-variational-supervised.md` |
| `hybrid_neural` | `references/profile-hybrid-neural.md` |
| `quantum_reservoir` | `references/profile-quantum-reservoir.md` |
| `quantum_generative` | `references/profile-quantum-generative.md` |
| `quantum_representation` | `references/profile-quantum-representation.md` |
| `quantum_reinforcement` | `references/profile-quantum-reinforcement.md` |

SDK detail paths are `references/sdk-cqlib.md`, `references/sdk-qiskit.md`, and
`references/sdk-pennylane.md`.

Profile references expose the exact headings `Variant Scope`, `Data and Encoding`,
`Model and Training`, `Measurement and Output`, `Diagnostics`, `Failure Modes`, and
`Acceptance`. SDK references expose `Selection Boundary`, `Library-First Components`,
`Runtime Adapter`, `Parameter and Measurement Semantics`, `Persistence`,
`Unsupported Behavior`, and `Evidence`. Read only the reference section needed for the active task.

## Required Evidence

- Publish `quantum_report.md` with the selected route, reused components, execution
  semantics, profile diagnostics, commands, metrics, persisted model information, and
  limitations.
- Document operation, input/output expectations, offline train/evaluate commands,
  preprocessing, and a known fixture in the report.
- Store reproducible metrics, predictions, and training traces under
  `artifacts/results/`.

## Handoff

Return the current quantum report to data-analysis-agent. This Skill
does not compare against the baseline, approve scientific acceptance, package a service, or
approve delivery.
