# qccp-service Feign and Configuration Rules

## Feign and cross-service calls

Shared Feign interfaces usually live under:

```text
qccp-api/qccp-api-system/src/main/java/com/zdxlz/api/system/
qccp-api/qccp-api-system/src/main/java/com/zdxlz/api/system/factory/
qccp-api/qccp-api-system/src/main/java/com/zdxlz/api/system/domain/
```

Common shape:

```java
@FeignClient(
    contextId = "remoteXxxService",
    value = ServiceNameConstants.SYSTEM_SERVICE,
    fallbackFactory = RemoteXxxFallbackFactory.class
)
public interface RemoteXxxService {
    @GetMapping("/xxx/{id}")
    R<XxxDTO> getXxx(
        @PathVariable("id") Long id,
        @RequestHeader(SecurityConstants.FROM_SOURCE) String source
    );
}
```

Rules:

- Search for existing `Remote*Service` before adding a cross-service call.
- Put DTO/domain types in `qccp-api` only when multiple services share them.
- Place fallback factories near existing `api/factory` code.
- Preserve internal-call headers. Existing code often uses `SecurityConstants.INNER` or `SecurityConstants.FROM_SOURCE`.
- When changing a Feign method signature, update the interface, fallback factory, provider Controller, and every caller.
- Do not hardcode another service's HTTP URL in business code.

## Configuration and environment

Runnable modules usually contain:

```text
bootstrap.yml
bootstrap-dev.yml
bootstrap-prod.yml
application.yml
```

These files load `${spring.application.name}.yml` and environment-shared config through Nacos.

Rules:

- Do not add hardcoded environment IPs, namespaces, usernames, passwords, bucket keys, or certificate paths.
- Do not leak secrets or environment credentials in code, comments, logs, docs, tests, or final responses.
- If the project already externalizes a setting, add new config through the existing Nacos/profile path.
- Before editing config, confirm whether the target module already has a similar setting.
- Do not copy development config into production config.

## qccp-ctyun AI assistant paths

AI-assistant code in `qccp-ctyun` is mainly under:

```text
qccp-modules/qccp-ctyun/src/main/java/com/zdxlz/ctyun/controller/ai/
qccp-modules/qccp-ctyun/src/main/java/com/zdxlz/ctyun/service/ai/
qccp-modules/qccp-ctyun/src/main/java/com/zdxlz/ctyun/remote/ai/
qccp-modules/qccp-ctyun/src/main/java/com/zdxlz/ctyun/dto/ai/
qccp-modules/qccp-ctyun/src/main/resources/
```

Rules:

- Conversation entry points usually start from `AiAssistantController`, `IAiAssistantService`, and `AiAssistantServiceImpl`.
- CTYun AI assistant calls usually go through `AiAssistantClient`.
- AI configuration usually lives in `AiAssistantProperties` and `AiWebClientConfig`.
- Conversation request DTOs usually start from `RagTalkReqDTO`; its `prompt` field can carry system prompts or rule prompts.
- Streaming Q&A responses use `Flux<String>` and `MediaType.TEXT_EVENT_STREAM_VALUE`.
- Do not log full prompts, sensitive user input, AK/SK, or tokens.
- Default prompt resources can live under `src/main/resources/ai/prompts/` and be loaded from the classpath before service startup or request handling.
