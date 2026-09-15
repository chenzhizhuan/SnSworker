---
name: qccp-service
description: "Guides backend, API, and runnable local FastAPI demo artifacts for CT TianYan Quantum Computing Cloud Platform showcases. Local standalone HTML follows qccp-ui visual rules; Vue/qccp-web work remains qccp-frontend scope. Use for Python FastAPI packaging or explicit Java/Spring Cloud qccp-service integration, endpoint contracts, deployment checks, and backend verification evidence."
name_cn: 天衍后端助手
description_cn: 提供天衍平台标准后端API及服务部署代码生成能力。支持Python FastAPI独立演示环境搭建，以及 Java/Spring Cloud 模块的规范化接口接入与联调。
---

# qccp-service Backend and Local Demo Dispatcher

Use this skill as the owner of backend/API contracts and the `local_fastapi_demo` delivery profile. First choose the backend path, then load only the reference file needed for the current task.

## When to Use

- User needs backend/API/deployment artifacts for a quantum application or cloud showcase.
- User is packaging a local Python FastAPI quantum app service with health checks, API contracts, local HTML/static demo hosting, or INTEGRATE evidence.
- User explicitly targets Java/Spring Cloud qccp-service modules, Controller/Service/Mapper/XML, Feign, config, security/current-user, Maven verification, endpoint contract, or health-check guidance.
- A quantum application needs backend or deployment packaging evidence.

## When NOT to Use

- **qccp-web Vue SFC page, route, or i18n output** -> use `qccp-ui` and `qccp-frontend`. A standalone local HTML page remains in this skill's FastAPI path, but its visual rules come from `qccp-ui`.
- **Quantum algorithm implementation or simulator/cloud circuit execution** -> use the selected `quantum-algorithm-*` skill and its SDK reference.
- **Planning only or final delivery approval** -> keep this skill out of scope.

## Backend path selection

1. **Python FastAPI quantum app service (default)**: use when the task is a local quantum application backend, demo API, static frontend service, `/health` endpoint, `/api/info`, `/api/solve`, `/api/infer`, deployment note, or INTEGRATE handoff.
2. **Java qccp-service integration**: use only when the active repository is `qccp-service`, the files are Java/Spring Cloud/POM/Mapper/XML/Nacos/Feign files, or the user explicitly asks for qccp-service-compatible Java integration.
3. If the task mixes both, keep the FastAPI app service as the demonstrable local backend and document the Java qccp-service integration boundary separately.
4. Never silently rewrite a Python FastAPI sample into Java. Never silently fall back from Java qccp-service integration to a simulator or local demo when real platform integration is requested.
5. Never commit secrets, Nacos credentials, cloud tokens, certificates, private endpoints, logs, generated temp files, or IDE config.

## Reference routing

- `references/fastapi-service.md`: Python FastAPI app service packaging, endpoint contract, static frontend hosting, config, verification, and INTEGRATE evidence.
- `references/standalone-demo-ui.md`: Required standalone HTML information architecture and its qccp-ui/qccp-frontend design alignment.
- `references/java-qccp-service.md`: Java qccp-service integration workflow and links to Java-specific module, coding, Feign/config, security, and Maven rules.
- `references/project-map.md`: Java qccp-service repository identity, stack, module responsibilities, module routing, and key files.
- `references/backend-coding-rules.md`: Java layout, Controller, Service, Mapper/XML, response model, file-stream, logging, and style rules.
- `references/feign-and-config.md`: Java Feign contracts, cross-service headers, Nacos/bootstrap config, and qccp-ctyun AI assistant paths.
- `references/security-and-commands.md`: Java current-user/security rules, safe edit workflow, search commands, Maven commands, and verification reporting.

## Backend workflow

1. Select the backend path from the evidence in the request and repository.
2. Read the relevant reference file before editing.
3. Read `quantum-application-intake/references/application-layout.md` and `application_manifest.json`. Keep service code under `<application_root>/backend/`, standalone UI under `<application_root>/frontend/standalone/`, launch commands under `<application_root>/scripts/`, and integration notes at `<application_root>/INTEGRATE.md`.
4. For `local_fastapi_demo`, use the small `local_demo` contract as the implementation source of truth: endpoint path, method, request schema, response schema, error cases, sample request when needed, static asset mappings, backend entry point, local demo entrypoint, and verification command. All paths are relative to the application root. Preserve `network` because onboarding owns host and port; implementation roles may update actual endpoints, assets, entrypoints, and selectors together with the source that changes them.
   Also record `api_base: /api`, `ui_profile: qccp-ui-standalone`, `language: zh-CN`, and a `browser_test` object with stable `status_selector`, `status_ready_text`, `action_selector`, and `result_selector`. The standalone page must expose those selectors through `data-testid` attributes.
5. Keep algorithm execution, backend service wrapping, frontend display schema, deployment notes, and verification evidence separate.
6. A local demo must use the Research-confirmed public dataset and a separate local offline training command. Persist the trained model and preprocessing artifacts under the application root; service startup and request handlers may infer only. They must not fit, retrain, backpropagate, step an optimizer, expose a training endpoint, return a fixed fixture, or silently substitute synthetic data. When the dataset, training, or required SDK is unavailable, report the concrete blocker rather than fabricating a demo response.
7. For QML, read the operation documented in `implementation_handoff.md`. Always expose `POST /api/infer`; predictive profiles may additionally expose `/api/predict` as a compatibility alias. `sample`, `transform`, and `act` retain their own response semantics.
8. Run the smallest relevant local verification command for the selected path.

## Application delivery handoff

For quantum application delivery, backend work contributes app packaging and verification evidence. Provide:

- endpoint paths, methods, request/response schema, and error cases
- conformance evidence against the main-owned, application-root-relative `application_manifest.json` `local_demo` contract
- service boundaries and persistence or job-execution ownership
- local training command, inference entry point, persisted model/preprocessing paths, and explicit missing/incompatible-artifact errors for trained-model applications
- required environment variables or ignored local config keys
- health-check and build/test commands for the selected backend path
- contract evidence for frontend/backend integration when both are in scope

Do not decide delivery readiness from this skill. Provide reviewable backend/API evidence for the application packaging and verification stages.

## Completion checklist

- [ ] Backend path is explicitly identified as Python FastAPI or Java qccp-service.
- [ ] Generated FastAPI, standalone frontend, scripts, and integration artifacts use the canonical application directories.
- [ ] A local FastAPI demo serves `/`, `/static/*`, `/api/health`, `/api/info`, and `/api/infer` from one origin; predictive apps may also expose `/api/predict`.
- [ ] The standalone page follows `qccp-ui` tokens and the local information architecture in `standalone-demo-ui.md`; it is not a raw API form or a qccp-web/Vue imitation.
- [ ] The standalone page can pass `run_app_check` qccp standalone preflight before API/browser smoke tests are counted as delivery evidence.
- [ ] Endpoint contract and error cases are documented.
- [ ] `local_demo` contract is recorded in `application_manifest.json` when the application manifest is in scope.
- [ ] Health check and smallest relevant verification command are reported.
- [ ] Frontend/backend integration evidence is captured when in scope.
- [ ] Trained-model previews load persisted artifacts and expose inference only; startup, API requests, and browser actions cannot trigger training.
- [ ] The first local-delivery slice has a real-public-data training command, a bounded fixed-seed training scale, a persisted model/preprocessor, `tests/test_smoke.py`, and a browser/API smoke result. Full scientific comparison is documented as later work unless explicitly requested.
- [ ] Java module/call chain is confirmed before Java edits.
- [ ] Mapper/XML and Feign/provider/caller files stay synchronized when Java contracts change.
- [ ] Secrets and environment-specific values remain outside code and docs.
