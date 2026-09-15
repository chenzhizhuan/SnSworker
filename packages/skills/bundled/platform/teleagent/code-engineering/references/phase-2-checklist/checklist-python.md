
# Python-Specific Checklist

> **Phase**: 2 (Pre-Flight Constraint Check)
> **Load when**: Task involves Python source code editing (T1: always | T2: always). See task-risk-grading.md for full activation matrix.
> **Source**: Extracted from SKILL.md v2.1

### Python-Specific
- [ ] No `print()` to stdout in modules consumed by other modules (use `print(..., file=sys.stderr)`)
- [ ] No trailing comma in function args that creates unintended tuples: `str(x,)` is wrong
- [ ] `akshare` calls: Add retry + multi-source fallback if called in a loop
- [ ] DataFrame operations: Never reference global `df` in helper functions; pass as parameter
- [ ] Path encoding: Use `pathlib.Path` or explicit UTF-8, never assume system encoding
- [ ] Windows控制台中文乱码：代码页936(GBK)下stdout/stderr输出中文乱码，需加`sys.stdout/stderr.reconfigure(encoding="utf-8")`修复块（详见checklist-windows.md）
- [ ] Install packages with `python -m pip install`, not `pip install`