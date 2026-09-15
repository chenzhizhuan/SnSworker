
# Data Integrity Checklist

> **Phase**: 2 (Pre-Flight Constraint Check)
> **Load when**: Task involves reading/writing financial data, dates, JSON with Chinese content, or numeric ID processing (T2: always). See task-risk-grading.md for full activation matrix.
> **Source**: Extracted from SKILL.md v2.1

### Data Integrity
- [ ] Numeric IDs: `str.zfill(6)` after pandas reads stock codes as int64
- [ ] Date handling: akshare Timestamps need `apply(lambda x: str(x)[:10])`
- [ ] Empty/zero values: Check for volume=0, NaN, None before division
- [ ] JSON write: Always `ensure_ascii=False` for Chinese content