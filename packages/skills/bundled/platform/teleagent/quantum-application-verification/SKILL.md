---
name: quantum-application-verification
description: "Run focused delivery checks in an isolated snapshot and document observed results without certifying application correctness."
name_cn: 量子应用验证工具
description_cn:  提供隔离环境下的量子应用自动化验证服务。支持执行预检指令，探测交付物完整性及运行状态，并自动生成标准验证报告，确保最终交付资产的可靠性。
---

# Quantum Application Verification

Run only the declared focused checks through `run_app_check`, which copies the
application into a disposable snapshot. Publish
`artifacts/reports/verification_report.md`.

List:

- artifacts that are present
- commands actually executed and their observed output
- results and limitations from the isolated checks
- checks that remain unverified or cannot be run
- missing files or unresolved blockers

Do not modify production source, run commands outside `run_app_check`, fabricate
evidence, or convert an observed local pass into a broader claim. The report does not certify runtime correctness beyond the executed check, deployment readiness,
TianYan execution, scientific validity, or quantum advantage.
It does not approve the application or release.

No generated artifact escapes or duplicates the application root.

## Handoff

Return the verification report path, executed checks, missing artifacts, blockers,
and unverified checks.
