
# Security Checklist

> **Phase**: 2 (Pre-Flight Constraint Check)
> **Load when**: Task involves ANY file write — source code, config files (.json/.yaml/.env/.toml), cache files, log files, DB seeds, shell scripts (T0: 4 items | T1: always | T2: always — MANDATORY). See task-risk-grading.md for full activation matrix.
> **Source**: Extracted from SKILL.md v2.1

### Security Checklist (MANDATORY for any code or config writing task)

**Scope**: This checklist applies to ALL file writes — not just source code. Config files (.json/.yaml/.env/.toml), cache files, log files, database seeds, and shell scripts are equally in scope.

- [ ] **SQL injection**: No string concatenation/interpolation for SQL → use parameterized queries (`?` placeholders)
- [ ] **Secrets leakage (source code)**: No hardcoded credentials → use environment variables or config files excluded from VCS
- [ ] **Secrets leakage (config files)**: Config files (.json/.yaml/.env/.toml) MUST NOT contain real credential values. Use `_env` suffix keys (e.g., `<field>_env`) that reference environment variable names, or placeholder values like `PLACEHOLDER`. Real values come from env vars at runtime.
- [ ] **Secrets in runtime output**: API credentials MUST NOT be persisted to cache files, log files, or response dumps. If caching API responses, strip sensitive auth fields before writing. Use separate credential loading (env var / dedicated secrets file) at call time, not embedded in cached payloads.
- [ ] **Sensitive files in VCS**: Ensure `.gitignore` excludes credential files (`*_config.json`, `*.env`, `data/cache/`, and any file with auth/credential data). If no `.gitignore` exists, create one.
- [ ] **Input sanitization**: User input used in HTML → escape/sanitize for XSS. User input in file paths → validate against path traversal (`..`).
- [ ] **Command injection**: User input passed to shell commands → use argument arrays (`execFileSync([cmd, arg1, arg2])`), never string interpolation
- [ ] **Auth on sensitive APIs**: Write/modify/delete endpoints → require authentication check
- [ ] **Log safety**: Never log credentials or PII. Redact sensitive fields before logging.