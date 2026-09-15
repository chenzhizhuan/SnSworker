# Java qccp-service Integration

Use this path only when the task explicitly targets the Java/Spring Cloud `qccp-service` repository or qccp-service-compatible Java artifacts.

## First steps

1. Confirm the active repository is `qccp-service` or that the requested output is a Java qccp-service-compatible artifact.
2. Read the root `pom.xml`, target module `pom.xml`, application class, and nearby Controller/Service/Mapper/XML files before editing.
3. Locate the owner module by business keywords, endpoint paths, class names, table names, permission keys, and Feign names.
4. Keep diffs narrow. Modify `qccp-api` or `qccp-common` only when the contract or utility is genuinely shared.
5. Never commit secrets, Nacos credentials, certificates, private endpoints, logs, generated temp files, or IDE config.

## Reference order

- `project-map.md`: repository identity, stack, module responsibilities, module routing, and key files.
- `backend-coding-rules.md`: Java layout, Controller, Service, Mapper/XML, response model, file-stream, logging, and style rules.
- `feign-and-config.md`: Feign contracts, cross-service headers, Nacos/bootstrap config, and qccp-ctyun AI assistant paths.
- `security-and-commands.md`: current-user/security rules, safe edit workflow, search commands, Maven commands, and verification reporting.

## Java backend workflow

1. Determine module ownership using `project-map.md`.
2. Inspect the existing call chain:
   `controller -> service/service.impl -> mapper -> resources/mapper/*.xml -> domain/dto/vo`.
3. Design the smallest API contract that satisfies the caller and follows local response wrappers.
4. Implement within the target module's naming, package, injection, exception, and logging style.
5. If SQL is involved, update both Mapper interface and XML together.
6. If Feign is involved, update the interface, fallback factory, provider Controller, and callers together.
7. If config is involved, follow the existing Nacos/profile path and keep secrets external.
8. Run the smallest relevant Maven command from `security-and-commands.md`.

## Completion evidence

Provide:

- target module and call chain
- endpoint paths, methods, request/response schema, and error cases
- response wrapper and permission/log annotations used by local precedent
- Mapper/XML synchronization evidence when SQL changes
- Feign provider/interface/fallback/caller synchronization evidence when contracts change
- smallest relevant Maven verification command and result

Do not decide final delivery readiness from this path. Provide Java backend/API evidence for integration verification.
