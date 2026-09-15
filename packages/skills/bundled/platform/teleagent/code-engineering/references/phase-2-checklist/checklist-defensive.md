
# Defensive Programming Checklist

> **Phase**: 2 (Pre-Flight Constraint Check)
> **Load when**: Task involves class/module design, public API design, or data model creation (T2: always — MANDATORY for class/module design). See task-risk-grading.md for full activation matrix.
> **Source**: Extracted from SKILL.md v2.1

### Defensive Programming (MANDATORY for class/module design)
- [ ] **Immutability**: Data classes that should not be modified after creation → use `@dataclass(frozen=True)` or `__slots__`
- [ ] **Type validation**: Every public method parameter: check type, check None/empty, raise ValueError with descriptive message
- [ ] **String validation**: Empty string `""` is different from None — check both. Strip whitespace before comparing.
- [ ] **Boundary values**: price/stock/score etc. — validate `> 0` not `>= 0` unless zero is meaningful. Use `<` not `<=` for "below threshold" unless inclusive.
- [ ] **Return type contracts**: Methods returning bool — never return None silently. Methods returning list — return empty list not None.
- [ ] **Duplicate prevention**: Any field that must be unique (SKU, email, name) — check before insert, raise on conflict.
- [ ] **Soft delete safety**: After soft delete (is_active=False), ALL queries must filter by is_active. Mark the field clearly.
- [ ] **tempfile encoding**: Always use `encoding="utf-8"` in `NamedTemporaryFile()` and `open()` — never rely on system default.