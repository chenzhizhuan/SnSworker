---
name: quantum-evidence-research
description: "Researches actionable evidence for quantum application decisions: classical baselines, datasets, known methods, maintained SDK components, evaluation protocols, backend constraints, and TianYan platform requirements. Use when planning lacks sourced evidence. Do NOT use to implement code, make the final route decision, or claim application readiness."
name_cn: 量子科研检索器 
description_cn: 专业的量子前沿技术与基线调研工具。支持检索经典对比算法、公开数据集及 SDK 组件可行性，输出带有溯源依据的研究简报，为量子路线决策提供数据支撑。
---

# Quantum Evidence Research

Collect decision-grade evidence that resolves the research-owned uncertainties
in one quantum application intake contract.

## Ownership

`research-agent` owns this skill. Other agents consume its evidence but should not turn unsourced recollection into a route decision.

## Research Scope

- problem assumptions and established classical baselines
- datasets, instances, preprocessing, splits, and licensing constraints
- QAOA, VQE, QML, or hybrid suitability and known failure modes
- maintained components of the Intake-selected Cqlib, Qiskit, or PennyLane SDK
- evaluation protocols, reference values, metrics, and uncertainty treatment
- simulator or TianYan device topology, queue, quota, and documented API constraints

## Workflow

1. Consume the runtime-provided Intake contract and research questions. It names
   one application root. Do not rescan the application directory or inspect
   unrelated generated applications.
2. Start with quantum fit: identify what part of the user's objective a quantum
   PoC can test, the strongest credible classical baseline, and whether evidence
   supports a quantum route at all. A justified no-go is valid research output.
3. Turn those questions into a short search plan: quantum fit, at least one
   viable alternative, the classical baseline/evaluation contract, data
   feasibility, and SDK/runtime feasibility.
4. Inspect source-discovery availability and local capabilities of the
   Intake-selected SDK only after defining the decision questions. Use Tavily
   for authoritative web discovery and `search_scholarly_sources` for DOI
   metadata leads. Do not reopen SDK selection.
5. Prefer primary documentation, maintained repositories, peer-reviewed papers,
   dataset repositories, and authoritative platform documentation.
6. Fetch every retained source and record its access time and content hash.
   Crossref metadata and search snippets are leads, not evidence.
7. After each search, identify which decision was answered, contradictory
   evidence, and the smallest missing query.
8. Extract actionable constraints: APIs, versions, licenses, data splits,
   metric definitions, resource limits, diagnostics, and failure modes.
9. Write completed evidence cards to `evidence_report.md` before starting a
   new search. This keeps useful research when a task is interrupted.
10. Stop when the quantum-fit decision and candidate comparison are supported,
   two searches repeat existing evidence, or five searches have been used.
11. Write a readable `generated_apps/<slug>/evidence_report.md` with these headings:
   `问题与约束`, `量子适用性`, `数据可行性`, `候选路线`, `经典基线`, `反证与限制`, `来源`, `证据卡`, and
   `研究证据简报`/`Research Evidence Brief`. The final brief has exactly three subsections:
   `已验证事实`/`Verified Facts`, `预检假设`/`Preflight Hypotheses`, and
   `待由 Planner 决定`/`Planner Decisions`. The first contains only retrieved-source facts,
   observed local capability results, and Intake constraints. The second contains estimates,
   transfer assumptions, and facts requiring a local probe. The third names decisions owned by
   planning; it must not choose them for the planner. Do not label a route recommended or set an
   empirical success threshold: those require a preflight observation.

## Evidence Record

The report contains:

- research questions and decision resolutions
- fetched sources with source type, publisher, dates, version scope, retrieval
  status, URL, and access time
- findings with `supports`, `contradicts`, or `limits`, confidence, scope,
  decision impact, and required verification
- datasets with license, access status, schema, size, and split risks
- classical baselines and quantum route candidates
- search provider, actual queries, provider availability, and stop reason

Each evidence card has a stable local identifier and records: decision question,
source URL, retrieved finding, applicability, limitation, and affected candidate
routes. Planner must be able to cite these cards when it selects or rejects a
route.

For QML, each route candidate records profile, variant, data domain, SDK,
official components, local capability status, applicability, failure modes,
required diagnostics, and evidence IDs. `sdk_primitive_available` means only a
minimal SDK circuit ran; only a passed `smoke_qml_route` may be reported as
`route_smoke_passed`. A metadata lead is not evidence for route selection.
Evidence-selected QML compares at least
two viable QML candidates when two exist. When only one route is viable or the
objective has no defensible quantum fit, explain why rather than inventing an
alternative. Dataset and classical baseline records do not pretend to be
alternate quantum routes.

Separate report statements into verified facts, source-bounded expectations, and
empirical hypotheses. A literature score, an estimated runtime, or a dataset-column
name does not establish an application acceptance threshold. Do not infer the ordering
or predictive importance of anonymized PCA components without dataset documentation or
a training-fold feature-selection experiment. For quantum-kernel candidates, identify
an exact representation-matched classical kernel baseline in addition to business
baselines. Record an exact dataset schema and data access status before suggesting a
service request schema.

Never fabricate citations, benchmark values, TianYan APIs, device capability, or availability. Simulator evidence cannot establish TianYan device behavior or quantum advantage.
When source discovery is unavailable and the Intake contains no explicit public
source URLs, report the evidence blocker; model recollection is not a source.

## Handoff

Keep the three-subsection Research Evidence Brief below 3,000 characters. Return key findings,
source URLs, implementation constraints, unresolved evidence, and candidate implications to
`planner-agent`. Do not rank candidates or emit an application recommendation;
`quantum-solution-ranking` owns the route decision. Research evidence cannot approve
implementation or delivery.
