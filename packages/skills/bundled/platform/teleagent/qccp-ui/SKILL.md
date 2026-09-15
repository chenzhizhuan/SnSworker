---
name: qccp-ui
description: "Guides the strict TianYan Quantum Computing Cloud Platform UI design specification for qccp/cloud showcase pages. Use for qccp-style pages, design tokens, visual consistency, platform UI components, and layout rules before qccp-frontend work. Do NOT use for backend/API work, quantum algorithm implementation, or final delivery readiness decisions."
name_cn: 天衍UI审查助手
description_cn: 内置天衍量子云平台UI 2.0官方设计规范。支持对前端页面的色彩令牌、组件状态及响应式排版进行像素级审查，确保云平台展示界面的视觉高度一致性。
---

# UI Design Spec

This skill defines the visual discipline for TianYan Quantum Computing Cloud Platform-style pages in the `qccp_web_page` delivery profile. For qccp-web implementation, use this as the visual reference before `qccp-frontend`; qccp-frontend owns target-repository Vue/SFC integration details.

The same visual profile also applies to standalone local FastAPI HTML demos in `local_fastapi_demo` and `full_delivery`. In that case, use the tokens, layout, language, and component discipline below, but keep the demo standalone and do not require qccp-web runtime imports, routes, stores, or global components.

## When to Use

- User needs qccp/cloud showcase visual rules before generating Vue page artifacts.
- User asks for colors, typography, spacing, radius, component states, bilingual layout fit, or visual consistency review.
- User is preparing a quantum application page and needs design constraints before `qccp-frontend`.
- A qccp application needs visual consistency evidence for packaging or integration review.
- `qccp-service` is generating a local FastAPI HTML demo that must look like a qccp/TianYan showcase while remaining standalone.

## When NOT to Use

- **Vue SFC, route, i18n, or integration output** -> use `qccp-frontend` after applying this spec.
- **Backend/API/service/deployment artifacts** -> use `qccp-service`.
- **Quantum algorithm implementation** -> use the selected `quantum-algorithm-*` skill and SDK reference.
- **Final staged verification or delivery approval** -> keep this skill out of scope.

## Top rules

1. Use the exact token values below. Do not approximate colors, font sizes, spacing, or radius.
2. Prefer theme variables or SCSS variables instead of scattered hardcoded style values.
3. Reuse page-local atomic components for buttons, inputs, tabs, tags, panels, and metric blocks.
4. Do not introduce unrequested gradients, shadows, animation, decorative graphics, special fonts, or non-standard icons.
5. Do not use emoji anywhere in UI copy, labels, placeholders, comments intended for UI display, or generated assets.
6. Page layout should be mainly vertical: top banner, then stacked content sections. Avoid a primary left-right split layout unless explicitly required.
7. Keep Chinese/English text length differences in mind; layouts must not break when switched to English.
8. For standalone local demos, use Chinese-first visible text, relative API calls, and page-local CSS/JS only. Do not use generic English demo copy such as "Run Baseline" or "Compare Results".

## TianYan UI 2.0 Authority

The latest TianYan Platform Design Specification 2.0 is the highest-priority UI
rule set for generated qccp application pages. When these rules conflict with
older local habits or generic web-design instincts, follow UI 2.0 and document
the conflict.

Brand semantics:

- Quantum precision, trusted computation, calm rationality, dense data, low
  noise, and efficient operation.
- Every action has deterministic feedback: loading, success, failure, or a
  state tag. A submitted task must never appear to do nothing.
- Keep the core operation path within three visible steps whenever possible.
- Every chart, metric, model output, or result block must include a timestamp,
  run state, or source/status label.
- Use functional hover/focus/loading/status transitions only. Decorative motion
  is not allowed.

Stack boundary:

- New qccp-web page artifacts follow UI 2.0 output discipline: Vue + Tailwind
  CSS, theme tokens first, reusable atomic components, then business page code
  and a compliance checklist. qccp-frontend owns the exact Vue/SFC integration
  with the real qccp-web repository.
- Local `local_fastapi_demo` HTML remains standalone and does not import Vue,
  Tailwind, Element Plus, qccp stores, or qccp routes. It must map the same UI
  2.0 tokens into page-local CSS variables and reusable page-local classes.

Strict output discipline for qccp-web work:

1. Define the complete theme variables first.
2. Define reusable atomic components before page code.
3. Build the business page from those tokens and components.
4. End with a compliance checklist that covers tokens, layout, components,
   feedback, data provenance, and brand semantics.

Do not require line-by-line style comments for local standalone HTML demos; use
clear section comments and a concise compliance checklist instead.

## Standalone Algorithm Showcase

Use this product surface for every `local_fastapi_demo` HTML page. The page must
look like a polished algorithm application showcase: the algorithm, data, result,
and operating state are visible as a coherent product surface. Do not produce a
raw API form, a field-by-field interface listing, a dark sci-fi panel, or a
marketing landing page.

The design should follow the product language used by TianYan quantum
application demos:

- Start with a short, full-width application explanation band that tells the
  scenario, the quantum/classical hybrid idea, and the user-facing value. Keep
  it readable and concrete; do not use a generic slogan.
- Make the main interaction domain-specific. For image tasks, show selected
  images, recognition process, and detected result. For forecasting tasks, show
  historical input series and predicted output series. For optimization tasks,
  show selectable candidates, constraints, and calculated recommendation. For
  circuit-centric tasks, show the circuit or operation sequence as the evidence
  of computation. The page may choose any suitable domain-specific presentation,
  but it must not collapse to raw inputs plus JSON.
- Put operation controls near the data they affect: image selection beside image
  analysis, date range beside time-series charts, candidate choices beside
  optimization cards, and circuit actions beside circuit/result evidence.
- Explain the algorithm as a visual process: data preparation, feature
  extraction or encoding, quantum layer/circuit/search, classical decoding, and
  final interpretation. This can be a diagram, step rail, card sequence, or
  annotated result area, but it must be visible on the page.
- Use generated or real domain artifacts when available: charts, heatmaps,
  sample images, recognition overlays, circuit diagrams, candidate cards, or
  result summaries. Placeholder graphics are allowed only for missing optional
  artifacts and must be clearly labeled.
- Keep long descriptions in summary bands and limitation strips. The main
  viewport should be visual and task-oriented, not paragraph-heavy.

First-viewport structure:

1. **Application masthead**: application name and one-sentence user value. Keep
   it compact; it introduces the app but does not dominate the screen. Service
   status may appear as a small inline state tag. Do not place SDK names,
   simulator/local execution mode, qubit counts, framework names, or other
   engineering metadata in first-viewport chips, cards, or badge rows unless
   the user explicitly asks for an engineering console.
2. **Algorithm showcase stage** with `data-testid="algorithm-showcase"`: the
   main visual area of the page. It should show the live model output, class or
   score distribution, route state, circuit/kernel summary, time-series forecast,
   optimization graph, or another domain-relevant visualization sourced from
   API response/static evidence. This area is larger than the input form.
3. **Operation dock**: compact input controls derived from the request schema,
   Chinese labels, inline validation, one primary action, and pending/disabled
   states. The dock supports the showcase; it is not the visual center.

Below the first viewport:

4. **Method flow** with `data-testid="method-flow"`: three to five horizontal
   or stacked steps such as public data -> preprocessing -> quantum encoding ->
   model inference -> result interpretation. Each step uses readable labels,
   concrete state/evidence text, and qccp tags; do not rely on unexplained
   letter-only glyphs such as D/S/Q/K/C as the primary communication.
5. **Evidence metrics**: training scale, public data source, model artifact
   status, simulator/TianYan status, SDK, qubit count, latency, or smoke-test
   result when available. These are supporting evidence, not first-viewport
   product badges.
6. **Limitations strip**: current scope and known limits in one compact band.

The first screen must answer: what the algorithm does, what it is running on,
what the current result means, and how to trigger one real inference. If the
page only lists endpoints or renders a generic form plus JSON output, it does
not satisfy this skill.

Product prioritization:

- The main result is the primary product content. For a classifier, foreground
  the selected class, confidence/ranking, and a compact probability or
  comparison visualization. For a forecaster, foreground the predicted series
  and input range. For an optimizer, foreground the recommended allocation and
  objective/constraint summary.
- Classical baselines, SDK, simulator, and qubit information are evidence
  details. Show them below the main task surface or in a compact limitation
  strip; do not give them equal visual weight with the user-facing result unless
  the user explicitly requests an algorithm-comparison page.
- Avoid large empty panels. Every first-viewport panel must contain a meaningful
  visualization, current result, compact empty state, or clearly labeled
  pending state with stable dimensions.

Standalone CSS pattern:

```css
:root {
  --qccp-primary: #1664FF;
  --qccp-primary-deep: #4F9DF7;
  --qccp-cyan: #00C7E7;
  --qccp-danger: #FB4214;
  --qccp-title: #020814;
  --qccp-sub: #41464F;
  --qccp-body: #939AAB;
  --qccp-page: #F4F7FC;
  --qccp-card: #FFFFFF;
  --qccp-card-blue: #F3F7FF;
  --qccp-border: #DCE0EB;
  --qccp-success: #34C759;
  --qccp-action-text: #7A8391;
}

body {
  margin: 0;
  background: var(--qccp-page);
  color: var(--qccp-title);
  font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", Arial, sans-serif;
}
```

Use light qccp pages by default. A strong visual hierarchy comes from layout,
scale, token color blocks, status tags, chart/table structure, and whitespace,
not from gradients or glow. Dark pages require an explicit user or product
requirement and still cannot use gradients, glow shadows, arbitrary colors, or
decorative animation.

Dark mode is allowed only when explicitly required. In that case, use exactly:
`#0A0E1A`, `#131A2E`, `#2A3457`, `#E8EDFF`, and `#9AA6CF`; do not mix custom
night-mode values into light pages.

## QML Operation Labels

Read the operation documented in `implementation_handoff.md` instead of assuming every QML model predicts:

- `predict`: use prediction/classification/regression labels.
- `sample`: use sampling controls and generated-sample results.
- `transform`: use encoding/reconstruction/representation labels.
- `act`: use observation, action, policy score, and episode-oriented labels.

All modes call relative `POST /api/infer`. Only a predictive profile may use
`/api/predict` as a declared compatibility alias.

## Locked layout values

| Token | Value | Use |
| --- | --- | --- |
| canvas | 1920px | desktop design base |
| containerX | 140px | left/right page margin in strict spec mockups |
| containerTop | 60px | top margin / header-aware offset |
| containerBottom | 140px | bottom page margin |
| base20 | 20px | grid gap |
| base30 | 30px | grid gap |
| radiusBtn | 4px | buttons |
| radiusTag | 6px | tags |
| radiusModal | 8px | cards, panels, modals |

When implementing in qccp-web, `.wrapper` may provide the 1440px centered project container. Do not alter global `.wrapper`.

## Color tokens

| Token | HEX | Use |
| --- | --- | --- |
| primary | `#1664FF` | main brand blue |
| primaryDeep | `#4F9DF7` | auxiliary blue |
| linkBlue | `#1F84FC` | links |
| danger | `#FB4214` | errors and warning dots |
| cyan | `#00C7E7` | cyan accent |
| textTitle | `#020814` | titles |
| textSub | `#41464F` | secondary text |
| textBody | `#939AAB` | body/help text |
| pageBg | `#F4F7FC` | page background |
| cardBg | `#FFFFFF` | white card background |
| cardBgBlue | `#F3F7FF` | light blue panel background |
| borderLine | `#DCE0EB` | borders/dividers |
| extend2 | `#BB79E1` | limited accent |
| extend3 | `#A58DF8` | limited accent |
| extend4 | `#4A86FF` | limited accent |
| success | `#34C759` | success toast only |
| actionText | `#7A8391` | card-bottom text action only |

Use the `#ECF2FF` to `#B5BFFF` range only when the design explicitly calls for that extension background. Do not add arbitrary gradients.

Dark-mode tokens are exclusive to explicit dark-mode work:

| Token | HEX | Use |
| --- | --- | --- |
| bgDark | `#0A0E1A` | dark page background |
| cardDark | `#131A2E` | dark card background |
| borderDark | `#2A3457` | dark border |
| textPrimaryDark | `#E8EDFF` | dark primary text |
| textSecondaryDark | `#9AA6CF` | dark secondary text |

## Typography tokens

| Token | Size | Weight | Use |
| --- | --- | --- | --- |
| textBanner | 60px | Bold | banner title only |
| textH1 | 40px | Bold | page title |
| textH2 | 30px | Regular | section title, data value |
| textH3 | 24px | Regular | block title |
| textSubHead | 20px | Regular | subtitle |
| textContent | 18px | Regular | body paragraphs |
| textMinor | 16px | Regular | secondary text |
| textTip | 14px | Regular | tables, notes, helper text |

Do not bold text that the spec marks as Regular.

## Component rules

Buttons:

- `PrimaryBtn`: filled primary button.
- `LineBtn`: border button.
- `TextBtn`: text/link button.
- `DisabledBtn`: disabled gray button.
- Button width must not exceed 128px.
- Card-bottom actions are text-only, use `#7A8391`, and hover to `primary`.

Tabs:

- Active: primary background and white text.
- Inactive: card background and `textBody`.

Inputs:

- Default border: `borderLine`.
- Focus border: `primary`.
- Readonly background: `pageBg`.

Icons:

- Use 1.5px linear outline style.
- Default color is `primary`.
- Status dot uses `danger`.
- No solid, colorful, thick, emoji, or decorative icons.

Tags:

- Radius: `radiusTag` 6px.
- Padding: 4px vertical, 8px horizontal.
- State color must come from the token list.
- State mapping: pending/submitted uses `primary`; running uses `cyan`;
  completed uses `primaryDeep`; failed uses `danger`.

Cards:

- Radius: `radiusModal` 8px.
- Background: `cardBg` for normal cards and `cardBgBlue` for emphasis panels.
- Padding: 24px.
- Prefer `shadow-sm` for hierarchy. Do not write custom shadow values.

Feedback:

- Submit/loading state uses an inline 16px spinner and changes text to
  "提交中..." or the domain-equivalent Chinese phrase.
- Success feedback uses a top toast for 3 seconds with `#34C759`.
- Failure feedback uses a closeable top toast with `danger`.
- Use at most three feedback forms on one page: toast, loading, and status tag.

## Prohibited

- Emoji.
- Non-token color values.
- Non-token radius values.
- Decorative gradients, shadows, bokeh/orbs, or animation beyond necessary hover feedback.
- Dark sci-fi backgrounds, glowing borders, glassmorphism cards, gradient
  headings, and page-wide visual effects for ordinary local demos.
- Raw endpoint listings, JSON-only result panes, and pages where the input form
  is larger or more prominent than the algorithm/result showcase.
- Primary layout built as a left-right marketing split when a vertical structure works.
- Random web images or invented asset URLs.
- Hardcoded one-language UI text in bilingual qccp pages.
- Generic English standalone demo labels when the requested or default delivery target is Chinese-first.

## Output checklist

- [ ] Layout is primarily top-to-bottom.
- [ ] First viewport contains `data-testid="algorithm-showcase"` and the
      showcase is the primary visual focus.
- [ ] Page contains `data-testid="method-flow"` explaining the algorithm path
      from data to output.
- [ ] No emoji appears in UI or generated assets.
- [ ] Colors come from token list.
- [ ] Typography size and weight match token mapping.
- [ ] Spacing uses the allowed grid values or project container conventions.
- [ ] Radius uses 4px, 6px, or 8px according to component type.
- [ ] Components are reused rather than hand-styled repeatedly.
- [ ] Chinese and English text both fit without overlap.
- [ ] Standalone local demos record `local_demo.ui_profile = "qccp-ui-standalone"` and `local_demo.language = "zh-CN"` in `application_manifest.json`.

When `application_manifest.json` is in scope, record or request a `qccp_web` UI evidence entry that identifies the SFC path, token/color/radius/font checks, bilingual-fit status, and any visual limitations. This is evidence for validation, not final delivery approval.

## Handoff

Use this skill to constrain visual decisions and record visual consistency evidence. Use `qccp-frontend` for Vue SFC structure, route snippets, i18n entries, API integration, output folders, and `INTEGRATE.md`.
