# qccp-service Security and Commands

## Security and current user

- When token or login-user context is needed, follow nearby `SecurityUtils` usage.
- Do not trust user ID, organization ID, role ID, or permission-sensitive fields from request bodies.
- Search for existing permission keys before adding admin permission annotations.
- If nearby list/query endpoints use data-scope annotations or aspects, keep that behavior.
- Preserve existing source-header conventions for internal interfaces.
- Validate file paths, download URLs, object-storage keys, and similar parameters when needed.

## Safe edit workflow

1. Locate the module and business call chain.
2. Read the target module `pom.xml`, application class, and nearby Controller/Service/Mapper/XML.
3. Confirm response wrappers, permission annotations, log annotations, exception types, and injection style.
4. Edit only the minimum necessary files.
5. If SQL is involved, update both Mapper interface and XML.
6. If Feign is involved, update the interface, fallback, provider, and callers together.
7. If config is involved, follow the existing Nacos/profile path and do not write secrets.
8. Run the smallest relevant Maven verification command.
9. Report changed files, verification results, and any reason verification could not be run.

## Search commands

Run from the repository root:

```bash
rg -n "keyword" qccp-modules qccp-api qccp-common
```

Find Controllers:

```bash
rg -n "@RestController|@RequestMapping|@GetMapping|@PostMapping" qccp-modules
```

Find application classes:

```bash
rg -n "SpringApplication.run|@SpringBootApplication" qccp-modules
```

Find module `pom.xml` files:

```bash
find qccp-modules qccp-api qccp-common -name pom.xml -maxdepth 4
```

## Maven commands

Run from the repository root.

Compile one service and its dependencies:

```bash
mvn -pl qccp-modules/<module> -am -DskipTests compile
```

Test one service and its dependencies:

```bash
mvn -pl qccp-modules/<module> -am test
```

Package one service and its dependencies:

```bash
mvn -pl qccp-modules/<module> -am -DskipTests package
```

Compile common API/common modules:

```bash
mvn -pl qccp-api/qccp-api-system,qccp-common -am -DskipTests compile
```

Compile the whole repository when the change is broad:

```bash
mvn -DskipTests compile
```

Local service startup may look like:

```bash
mvn -pl qccp-modules/<module> spring-boot:run -Dspring-boot.run.profiles=dev
```

Local startup usually depends on reachable Nacos config plus the module's required database, Redis, object storage, RocketMQ, or external services.
