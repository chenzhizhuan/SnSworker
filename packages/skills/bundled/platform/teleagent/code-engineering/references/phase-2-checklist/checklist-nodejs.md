
# Node.js-Specific Checklist

> **Phase**: 2 (Pre-Flight Constraint Check)
> **Load when**: Task involves Node.js/JavaScript source code editing (T1: always | T2: always). See task-risk-grading.md for full activation matrix.
> **Source**: Extracted from SKILL.md v2.1

### Node.js-Specific
- [ ] Use `execFileSync` with argument array, never `execSync` with command string (GBK encoding breaks Chinese paths)
- [ ] Use `new URL()` instead of deprecated `url.parse()`
- [ ] Bind to `'127.0.0.1'` explicitly on Windows
- [ ] All fetch calls must include HTTP status check (`if (!r.ok) throw`) + AbortSignal timeout
- [ ] Frontend API URLs use dynamic `location.origin`, never hardcode `localhost`
- [ ] Add no-cache headers for local development services
- [ ] ECharts: dispose existing instance before re-rendering; avoid markArea/markPoint/scatter with category axis + dataZoom