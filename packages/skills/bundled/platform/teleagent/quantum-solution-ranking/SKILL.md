---
name: quantum-solution-ranking
description: "Turns research evidence into a bounded, executable quantum-application plan and reflects on observed experiments."
name_cn: 量子方案决策助手
description_cn: 核心的量子技术路线规划大脑。基于调研证据自动评估算法可行性，输出结构化的工程研发计划（plan.md），并支持在实验迭代中动态反思与调整优化策略。

---

# Quantum Application Planning

Use `requirements.md` and `evidence_report.md` to choose one practical route
for QAOA, VQE, QML, hybrid QML, or explicitly authorized TianYan work. Write
one readable `plan.md`; it is the implementation contract for the application,
not a collection of workflow certificates.

## Route Selection

Start with hard constraints: user-locked SDK, execution authorization,
input/output semantics, delivery profile, available data or instances, and
locally verified dependencies. Reject a route that violates one of them rather
than compensating with a made-up score.

For the selected route, explain problem fit, retrieved evidence, SDK capability,
classical reference, resource limits, falsifier, and delivery impact. A numeric
ranking is allowed only when the user supplied criteria and weights. Keep a
classical-only conclusion visible when a quantum route is not defensible.

Prefer maintained SDK algorithms and framework adapters over handwritten quantum
cores. A primitive capability check proves only a dependency; a route smoke
proves only an implementation path; neither proves scientific performance.

## Code-Ready `plan.md`

The initial plan must let code-agent implement the requested application without
making another algorithm, SDK, data, baseline, evaluation, or delivery decision.
Use these sections:

1. **Scope and delivery**: user goal, intended audience, delivery profile, and
   claimed limitation.
2. **Selected route and SDK primitives**: one route, fully qualified library
   APIs or adapter, backend assumptions, and one fallback only when a declared
   hard constraint fails.
3. **Data and evaluation contract**: source/access method, expected schema and
   failure behavior; train, validation, and final-test roles; preprocessing fit
   boundaries; seeds; primary metric.
4. **Baseline and comparison**: primary representation-matched baseline plus
   contextual baselines. For a QML quantum kernel this is RBF-SVC on identical
   rows, transformations, validation folds, and score metric.
5. **Implementation work packages**: source modules, train/infer commands,
   model persistence, API/UI tasks when requested, and focused tests.
6. **Allowed adjustments**: the parameter family, candidate range, validation
   metric, conditions that remain fixed, and a stop condition. Do not put more
   than one parameter family in one adjustment.
7. **Stop and replan triggers**: unavailable data/SDK, a semantic contradiction,
   or an explicit user scope change. Weak metrics alone do not authorize an
   unbounded route change.

Do not turn literature values, expected runtime, PCA variance, or unmeasured
scores into gates. Record them as observations to collect. Feature selection,
hyperparameter selection, and calibration use training/validation data only;
the final test set is used once after the configuration is frozen.

## Reflection

Run `MODE: REFLECTION` only after a completed baseline, quantum experiment, or
data-analysis result. Do not reflect after documentation, ordinary debug work,
or API/UI repairs.

Append one entry to `plan.md`:

```markdown
## Iteration N

Observed: <command, result, changed paths>
Decision: keep | adjust | replan | stop
Adjustment: <one allowed parameter family, or none>
Validation: <training/validation command and metric>
Stop condition: <when this iteration ends>
```

`adjust` may tune only an already declared parameter family. Changing route,
SDK, data semantics, split boundary, primary metric, baseline family, or delivery
profile is `replan`. Reflection entries never rewrite the initial plan.

## Handoff

Return `plan.md`, selected route, next work package, and any unresolved hard
constraint. The framework limits planner reflections per LangGraph thread; when
the allowance is exhausted, continue verification and delivery or report the
best reproducible result and limitations. Planning does not approve scientific
claims, deployment, or delivery; application tests and independent verification
establish those separately.