# qccp-service Backend Coding Rules

## Typical Java layout

Most `com.zdxlz` modules follow this shape:

```text
src/main/java/com/zdxlz/<module>/
├─ controller/
├─ service/
├─ service/impl/
├─ mapper/
├─ domain/
├─ domain/dto/
├─ domain/vo/
├─ config/
├─ utils/
└─ mq/
```

Resources usually include:

```text
src/main/resources/
├─ bootstrap.yml
├─ bootstrap-dev.yml
├─ bootstrap-prod.yml
├─ mapper/
│  └─ .../*.xml
└─ application*.yml
```

Imitate the target module's existing paths and names instead of mechanically copying another module.

## Controller rules

Controllers receive parameters, apply permission/log annotations, wrap responses, and call services.

- Use `@RestController`.
- Use the target module's existing `@RequestMapping` path style.
- Extend `BaseController` when pagination or standard Ajax helper methods are needed.
- Use DTO/domain objects for paged-query filters when that is the local convention.
- Call `startPage()` before paged service queries when using the standard pagination flow.
- Return paged data through `getDataTable(list)` when nearby code does so.
- Match the current Controller's response type, commonly `AjaxResult` or `R<T>`.
- File preview, download, and export endpoints may write directly to `HttpServletResponse`.
- Search for existing `@RequiresPermissions` keys before adding admin endpoints.
- If nearby CRUD endpoints use `@Log(title = ..., businessType = ...)`, follow that style.

Common paged-query shape:

```java
@GetMapping("/list")
public TableDataInfo list(QueryDTO query) {
    startPage();
    List<VO> list = service.selectList(query);
    return getDataTable(list);
}
```

Common operation shape:

```java
@PostMapping
public AjaxResult add(@RequestBody SaveDTO dto) {
    return toAjax(service.insert(dto));
}
```

Do not put complex SQL, external calls, or business orchestration in Controllers.

## Service rules

- If the module uses interface plus implementation, update both `service` and `service.impl`.
- Use `@Service` on implementations.
- Use `@Slf4j` when logging is needed.
- Follow the local injection style; the project commonly uses `@Resource` and `@Autowired`.
- Prefer existing exception types near the code, such as `ServiceException`, for business validation failures.
- Wrap external service calls behind Feign clients, module utilities, or service methods.
- Do not scatter HTTP calls, storage calls, or complex object assembly into Controllers.
- For batch data, prefer batch queries followed by Java-side assembly to avoid N+1 queries.

## Mapper and SQL rules

- Mapper interfaces live in each module's `mapper` package.
- XML files live under `src/main/resources/mapper/...`.
- XML `namespace` must equal the fully-qualified Java Mapper interface name.
- Prefer existing MyBatis-Plus methods for simple CRUD.
- Use custom XML SQL for complex filtering, joins, and batch queries.
- Preserve each XML file's existing `resultMap`, alias, and dynamic SQL style.
- Use `#{}` parameters. Do not concatenate SQL strings.
- Use MyBatis dynamic tags for optional conditions.
- Use `foreach` for batch parameters.
- Follow existing logical-delete, status, and timestamp conventions such as `isDel`, `status`, `createTime`, and `updateTime`.

Do not update only the Java Mapper method and forget the XML. Do not update only XML and forget the Java signature.

## Response model rules

Common wrappers:

- `AjaxResult`: map-style response with `code`, `msg`, and optional `data`.
- `R<T>`: generic response with `code`, `msg`, and `data`, often used by Feign or internal APIs.
- `TableDataInfo`: paged table response with `rows`, `total`, `code`, and `msg`.
- `BaseController`: provides `startPage()`, `getDataTable(...)`, `toAjax(...)`, `success(...)`, and `error(...)`.

Choose response types by local precedent. Prefer `TableDataInfo` for paged lists, `AjaxResult` for nearby admin operations, and `R<T>` for nearby internal API or Feign code.

## File and binary stream rules

- File-service integration usually goes through `RemoteFileService` and shared upload DTOs in the API module.
- Validate empty files, file type, and size limits before upload.
- Use buffered streaming for download/preview; do not read entire large files into memory.
- Set the correct `Content-Type`.
- Set `Content-Disposition` for downloads.
- If the frontend needs filenames, set `Access-Control-Expose-Headers: Content-Disposition`.
- Prefer the target module's existing object-storage, OSS, S3, or ZOS utility.

## Logging and style

- Use SLF4J placeholders: `log.info("xxx {}", value)`.
- Do not use `System.out.println`.
- Do not log tokens, passwords, keys, certificate contents, or full sensitive URLs.
- Prefer existing business exceptions.
- Do not swallow exceptions.
- Follow module-local Java style, Lombok usage, and Jakarta imports under Spring Boot 3.
- Do not add meaningless utility classes or over-abstract one-off logic.
