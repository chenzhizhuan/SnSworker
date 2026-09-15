
# Template Specification

Standard format and quality requirements for code-engineering skill templates.

## Template File Format

Every template file in `references/` must follow this structure:

```markdown
# [Template Name]

One-line description: what this template produces and when to use it.

## [Skeleton Name] (`path/to/file.ext`)

\`\`\`[language]
// Complete, runnable skeleton code here
// Every section annotated with comments explaining its purpose
\`\`\`

## Key Points

| Concern | Solution |
|---------|----------|
| [Problem domain] | [How the template handles it] |
| [Problem domain] | [How the template handles it] |

## Usage Checklist When Copying

- [ ] [Step to customize before using]
- [ ] [Step to customize before using]
<!-- Updated: YYYY-MM-DD, initial creation -->
```

## Quality Requirements

### Completeness
- The skeleton must be **copy-paste runnable** (with placeholder substitution only)
- Include all necessary imports, error handling, and entry points
- No `// ... your code here ...` gaps that leave the user guessing structure

### Annotation
- Every major section must have a comment explaining **what** it does and **why** it's needed
- Mark customization points clearly: `[CONFIGURE: description]` or similar markers
- Include inline comments for non-obvious decisions (e.g., `// GBK: cmd.exe native format`)

### Key Points Table
- Must cover the top 5-8 "gotchas" this template prevents
- Each row: specific problem → how the template solves it
- Focus on mistakes that would happen without the template, not obvious best practices

### Usage Checklist
- List every customization step needed before the template produces a working result
- Order: most impactful first (change port, update endpoints, then minor tweaks)
- End with a verification step (test command, expected output)

## Customization Point Conventions

Use these markers in skeleton code to indicate where users must fill in values:

```python
# [CONFIGURE: Server port]
PORT = 19998

# [CONFIGURE: API endpoint path]
ENDPOINT = '/api/data'
```

Markers must:
- Be in `# //` comment syntax appropriate to the language
- Include a brief description of what to fill in
- Not use placeholder values that look like real code (avoid `xxx`, `TODO`, `fixme`)

## Template Categories

Templates are organized by their primary technology stack:

| Category | Directory Convention | Examples |
|----------|---------------------|----------|
| Node.js backend | `references/nodejs-*.md` | HTTP server, WebSocket, CLI tool |
| Python processing | `references/python-*.md` | Data pipeline, API client, file processor |
| Frontend UI | `references/frontend-*.md` | SPA, dashboard, form page |
| Infrastructure | `references/infra-*.md` | Docker, CI config, deployment script |

## Anti-Patterns (DO NOT)

- **Ghost sections**: Empty sections with only `// implement this` — provide at least a stub
- **Over-abstracted**: Template so generic it requires more customization than writing from scratch
- **Tightly coupled to one project**: Include project-specific data/config in the skeleton — keep skeletons project-agnostic
- **Missing error handling**: A template without error handling teaches bad habits
- **No encoding awareness**: Templates that assume ASCII or don't specify encoding will fail on Chinese content

## Template Lifecycle

```
Draft → Tested → Stable → Deprecated → Removed

Draft:    Just created, used 0-1 times
Tested:   Successfully used 1+ times on real tasks
Stable:   Used 3+ times without major changes needed
Deprecated: Superseded by a better template, marked with <!-- Deprecated: reason, use X instead -->
Removed:   Deleted after being deprecated for 30+ days
```

## Iteration Changelog

Every template modification appends a comment at the bottom:

```markdown
<!-- Updated: 2026-04-26, added retry decorator for API calls -->
<!-- Updated: 2026-04-28, fixed GBK encoding in error messages -->
<!-- Updated: 2026-05-01, added ECharts dispose pattern -->
```

Changelogs preserve why changes were made — critical for avoiding regressions.