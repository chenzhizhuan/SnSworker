# qccp-service Project Map

## Identity and stack

- Project: CT TianYan Quantum Computing Cloud Platform backend.
- Repository: `qccp-service`.
- Architecture: Maven multi-module Java microservices.
- Main package: most modules use `com.zdxlz.*`; `qccp-code` also contains `com.ffcs.ctc.code.*`.
- Stack source of truth: root `pom.xml` and target module `pom.xml`.

Confirmed stack in the current rule set:

- Java 21
- Spring Boot 3.5.6
- Spring Cloud 2025.0.0
- Spring Cloud Alibaba 2025.0.0.0
- Nacos service discovery and configuration through `bootstrap-*.yml`
- MyBatis-Plus 3.5.14 and MyBatis XML
- PageHelper, `PageUtils`, and `TableDataInfo`
- springdoc-openapi 2.8.13
- Redis through `qccp-common-redis`
- project security through token context, login user context, permission annotations, and request-header interceptors
- RocketMQ, Hutool, Apache Commons, POI, Fastjson2
- MinIO / AWS S3 API / module-local object-storage utilities
- Spring Boot 3 Jakarta packages such as `jakarta.servlet.*` and `jakarta.annotation.*`

Do not introduce a new stack or dependency without explicit request and repository evidence.

## Top-level layout

```text
qccp-service/
├─ pom.xml
├─ qccp-api/
├─ qccp-common/
├─ qccp-modules/
├─ qccp-tools/
└─ docs/
```

## Common modules

- `qccp-common-core`: constants, exceptions, utilities, response wrappers, base controllers, pagination objects.
- `qccp-common-security`: token handling, login user context, security utilities, permission annotations, request-header interceptors.
- `qccp-common-datasource`: datasource and MyBatis infrastructure.
- `qccp-common-datascope`: data-permission annotations and aspects.
- `qccp-common-log`: operation-log annotations and aspects.
- `qccp-common-redis`: Redis support.
- `qccp-api/qccp-api-system`: Feign interfaces, fallback factories, and shared API domain/DTO types.

Modify a common module only when at least two services reuse the capability, the common module already owns it, or a shared Feign/API contract requires it.

## Business modules

| Module | Primary responsibility |
| --- | --- |
| `qccp-modules/qccp-gateway` | Gateway service |
| `qccp-modules/qccp-auth` | Authentication and authorization |
| `qccp-modules/qccp-system` | System and web-client services |
| `qccp-modules/qccp-file` | File service |
| `qccp-modules/qccp-job` | Scheduled jobs |
| `qccp-modules/qccp-manage` | Admin/management service |
| `qccp-modules/qccp-learn` | Learning and education center |
| `qccp-modules/qccp-quantum` | Quantum experiment service |
| `qccp-modules/qccp-ctyun` | CTYun/supercomputing integrations, including AI-assistant integration |
| `qccp-modules/qccp-rocketmq` | Queue and message consumers |
| `qccp-modules/qccp-algorithm` | Algorithm framework service |
| `qccp-modules/qccp-hybrid` | Hybrid quantum/classical computing service |
| `qccp-modules/qccp-order` | Order service |
| `qccp-modules/qccp-code` | Code, GitLab, Sonar, and related services; common package is `com.ffcs.ctc.code` |

## Module routing

- Admin operations, review workflows, order management, user management backend features: start with `qccp-manage`.
- Platform, user, and system capabilities with existing routes or domain objects in `qccp-system`: start with `qccp-system`.
- Quantum experiments, experiment tasks, quantum computers, quantum circuits, and experiment execution: start with `qccp-quantum`.
- Algorithm tasks, algorithm models, components, and algorithm workflows: start with `qccp-algorithm`.
- Hybrid quantum/classical execution: start with `qccp-hybrid`.
- Upload, download, preview, and object storage: start with `qccp-file` or the target business module's existing storage utility.
- Login, token, authentication, authorization, OAuth, and mini-program login: start with `qccp-auth`.
- Gateway, routing, captcha, and gray routing: start with `qccp-gateway`.
- AI assistant, knowledge-base Q&A, model lists, conversation history, and Q&A quota: start with `qccp-ctyun`.
- Interfaces called by multiple services: start with `qccp-api/qccp-api-system`.

Do not create a new module or common class before locating the existing ownership boundary.

## Key files

```text
pom.xml
qccp-modules/pom.xml
qccp-api/pom.xml
qccp-common/pom.xml
qccp-modules/<module>/pom.xml
qccp-modules/<module>/src/main/resources/bootstrap*.yml
qccp-modules/<module>/src/main/resources/mapper
qccp-common/qccp-common-core/src/main/java/com/zdxlz/common/core/web/controller/BaseController.java
qccp-common/qccp-common-core/src/main/java/com/zdxlz/common/core/web/domain/AjaxResult.java
qccp-common/qccp-common-core/src/main/java/com/zdxlz/common/core/domain/R.java
qccp-common/qccp-common-core/src/main/java/com/zdxlz/common/core/web/page/TableDataInfo.java
qccp-common/qccp-common-security/src/main/java/com/zdxlz/common/security/utils/SecurityUtils.java
```
