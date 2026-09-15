---
name: quantum-cloud-execution
description: "Controls explicitly authorized execution on the TianYan Quantum Computing Cloud Platform through the existing Cqlib integration: capability preflight, credentials via environment or ignored config, device selection, compilation constraints, job submission, polling, retrieval, and provenance. Use only when the user requests TianYan execution. Do NOT use for another cloud provider or local simulation, and never silently fall back to a simulator or another device."
name_cn: 天衍云端调度助手
description_cn: 天衍量子云平台专属的物理真机调度工具。支持编译约束检查、任务提交、状态轮询与结果解析，安全代理云端算力执行，自动记录完整的物理执行状态。
---

# Quantum Cloud Execution

Execute an already validated circuit or workload on the TianYan Quantum Computing Cloud Platform without exposing secrets or changing scientific semantics.

## Supported Route

- Platform: TianYan Quantum Computing Cloud Platform only.
- SDK: Cqlib only, using the integration already present in the repository or installed Cqlib version.
- API contract: inspect existing code and available platform documentation before use. Never invent client classes, endpoints, authentication fields, device IDs, or result schemas.

Requests for another cloud platform are unsupported in this lifecycle. Return a route blocker instead of translating the workload to a different provider or SDK.

## Authorization Gate

Before any network call or job submission, confirm and record:

- user authorization for the named TianYan execution
- selected TianYan device, account scope, and expected quota or cost
- shots, queue/timeout policy, retry policy, and cancellation expectations
- credential source as an environment variable or ignored local configuration

Never request credentials in chat, print them, commit them, or copy them into artifacts. Authorization for one backend or job does not authorize another.

## Workflow

1. Read the application contract, selected Cqlib skill reference, experiment protocol, and local validation evidence.
2. Confirm the active Cqlib version exposes an existing TianYan integration. If it does not, return a dependency or capability blocker.
3. Inspect the selected TianYan device status, qubit count, topology, native gates, shot limits, and current constraints using repository code or authoritative TianYan documentation.
4. Compile without changing logical qubit/measurement meaning; record mapping, basis gates, depth, and warnings.
5. Submit once with an idempotency strategy when supported; record the returned job ID without secrets.
6. Poll with bounded intervals and timeout handling. Distinguish authentication, validation, queue, backend, timeout, cancellation, and malformed-result failures.
7. Retrieve raw and decoded results, preserving counts, bit order, shots, timestamps, and backend metadata.
8. Write `cloud_job_record.json` and hand results to independent verification.

## No Silent Fallback

Do not replace the selected TianYan execution with a local simulator, change device, reduce shots, or switch SDK after failure without a new explicit decision. Do not route to another cloud platform. If authorization, credentials, Cqlib support, or TianYan documentation is missing, return a blocker before making a remote call.

## Handoff

Return authorization scope, TianYan device, Cqlib version and integration component, compile metadata, job ID, status history, shots, timestamps, raw/decoded artifact paths, cost/quota notes, failures, and limitations. A completed TianYan job is evidence, not approval of application readiness or proof of quantum advantage.
