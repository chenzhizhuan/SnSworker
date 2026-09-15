---
name: quantum-application-intake
description: "Clarifies a quantum application request and records a readable Intake handoff. Use before research. Do not choose the algorithm, implement code, or approve delivery."
name_cn: 量子需求分析师
description_cn: 智能化量子应用需求梳理工具。通过结构化解析提取用户目标、输入输出限制及资源约束，自动生成标准需求文档与应用清单，为工程研发确立清晰边界。
---

# Quantum Application Intake

Turn the user's objective into enough context for research and planning without
prematurely designing the solution.

## Responsibilities

- identify the application goal, intended user, inputs, outputs, and constraints
- distinguish user requirements from assumptions and optional preferences
- ask only questions whose answers materially change scope, data access, delivery
  profile, execution authorization, or expected result
- choose a lowercase kebab-case application slug
- record the result in `requirements.md`
- publish the minimal operational `application_manifest.json`

Write both files directly under `generated_apps/<slug>/`. They are ordinary
application handoff documents; no framework state needs to be updated.

## Guidance

Do not select a QML family or variant merely from keywords. SDK is normally an internal
runtime preference, not an application type or complexity signal. Treat it as mandatory only
when the user explicitly requires it or supplies SDK-bound code/platform constraints.
Default unspecified execution to a local simulator. TianYan execution requires an
explicit user request and authorization.

Classify whether the application contains learned model parameters. Learned-model
training must be a separate local offline command, persisted model and preprocessing
artifacts must be reusable, and preview/service/browser paths are inference-only.
Declared per-instance QAOA/VQE optimization is not model training.

Unknown details can remain open in natural language. Intake is complete when the
next research agent can understand what is being built and what remains uncertain;
it does not require a field-complete scientific contract.

## Output

`requirements.md` should contain:

- application objective and target user
- available data or problem instance
- expected inputs and outputs
- constraints, preferences, and delivery profile
- execution authorization and known environment limits
- open questions for research or planning
- application archetype, input/output kind, training need, and external integrations

The report is a handoff document, not validation evidence.
Intake does not approve the selected method or final delivery.

## Handoff

Return the application slug, generated paths, assumptions, and open questions to the
research stage.
