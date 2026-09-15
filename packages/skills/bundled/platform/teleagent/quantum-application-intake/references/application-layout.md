# Generated Quantum Application Layout

Every generated application uses:

```text
<active_workspace>/generated_apps/<application_slug>/
```

The slug is lowercase kebab-case. All manifest paths are POSIX paths relative to
the application root; absolute paths, `..`, and symlink escapes are forbidden.

## Lifecycle Artifacts

```text
generated_apps/<application_slug>/
├── requirements.md
├── application_manifest.json
├── evidence_report.md
├── plan.md
├── README.md
├── INTEGRATE.md
├── algorithm/
├── backend/                          # local FastAPI/full-delivery service
├── frontend/
│   ├── standalone/                   # local FastAPI/full-delivery HTML entry point
│   │   └── static/                   # local CSS, JS, images, vendored runtime assets
│   └── qccp/project-files/           # qccp_web_page/full-delivery Vue handoff
├── models/                           # when persisted model parameters are needed
├── scripts/
├── tests/
└── artifacts/
    ├── reports/
    │   ├── baseline_report.md
    │   ├── quantum_report.md
    │   ├── comparison_report.md
    │   ├── implementation_handoff.md
    │   └── verification_report.md
    ├── results/
    ├── plots/
    └── logs/
```

The report files are readable handoff documents. They are not machine validation
certificates; use the application's tests and recorded command results for validation.

`application_manifest.json` remains structured because launchers and service/UI
integration consume it. Its network fields come from onboard configuration.
Conditional directories are created when the intake manifest selects the relevant
delivery profile. They are empty conventions, not generated placeholder code.
Blocked work should record the blocker truthfully in its Markdown report.

## Completion Meaning

An application is ready for handoff when its expected source, documentation, and
tests exist and the recorded local checks describe their actual result. This does
not certify deployment readiness, TianYan execution, scientific validity, or
quantum advantage.
