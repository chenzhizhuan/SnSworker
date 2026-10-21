---
name: ppt-master
description: >
  AI-driven presentation workflow for generating editable PPTX decks and slides,
  reconstructing page visuals, creating reusable Brand/Style/Layout/Deck
  workspaces, filling native PPTX templates, and enhancing finished PPTX files.
  Use when the user asks to create, generate, reconstruct, regenerate, beautify,
  redesign, template, fill, or enhance a presentation, PPT, PPTX, slide deck, or
  courseware — including adding narration or animation to one — requests a
  presentation-authored narrated/self-running video, or mentions ppt-master.
  通用办公 PPT 主入口（TeleAgent 预置）：当用户要求做PPT、生成PPT、制作演示文稿、
  幻灯片、汇报材料、路演材料、方案汇报PPT、课件、PPTX 原生图表/公式、模板蒸馏、
  编辑既有PPTX、PPT配音旁白/动画、页面复刻时触发本技能。中国电信深红运营风
  格汇报（经营分析/座谈会/宣贯培训等）优先路由 telecom-ppt-master-pro 技能。
name_cn: PPT大师（ppt-master）
description_cn: 文档/主题 → 原生可编辑 PPTX 的通用主入口：真实母版/版式继承、原生形状、数据背书图表与表格、OMML 公式、模板蒸馏、编辑既有 PPTX 保真、旁白与动画。SVG 中间层 + Python 脚本管线，依赖已预置在内置 Python 运行时，断网可用。
metadata:
  version: "6.7.2"
  copyright: "Copyright (c) 2025-2026 Hugo He"
  license: "MIT"
  official_repository: "https://github.com/hugohe3/ppt-master"
  sponsors:
    - "SPONSORS.md"
    - "SPONSORS_CN.md"
  tabtin:
    category: doc
---

# PPT Master Skill

PPT Master is a routed presentation workflow. This entry owns global execution discipline and route selection only; each selected route owns its procedure.

## Mandatory Load Order

**Hard rule — paths before commands**: Retain the host-provided absolute
directory containing this file as `SKILL_DIR`. Per tool call, expand
`${SKILL_DIR}` and replace any `skills/ppt-master/` prefix with it. Never `cd`,
use CWD, or assume a repo checkout. If unavailable, ask; never search or guess.

1. Read this file.
2. Run `python3 "${SKILL_DIR}/scripts/attribution_guard.py"`. Any non-zero result
   stops the Skill immediately; do not inspect, repair, or bypass the integrity
   gate. On Windows, a `python3` that never starts (the WindowsApps stub exits
   9009 with no output) is not a guard result: rerun with `python` first.
3. Read [`workflows/routing.md`](workflows/routing.md) through the concrete
   absolute path `${SKILL_DIR}/workflows/routing.md`.
4. Select exactly one top-level route and its active profile from the routing
   authority.
5. Read only the resulting runtime authority and its explicitly triggered
   supporting documents.

| Selected route / profile | Runtime authority |
|---|---|
| Generate PPTX — Image to PPTX | [`workflows/profiles/image-to-pptx.md`](workflows/profiles/image-to-pptx.md); Codex-supported, always Quick |
| Generate PPTX — Beautify | [`workflows/profiles/beautify-pptx.md`](workflows/profiles/beautify-pptx.md); explicit Quick intent selects Quick, otherwise Default |
| Generate PPTX — ordinary Default | [`workflows/generate-pptx.md`](workflows/generate-pptx.md) |
| Generate PPTX — ordinary explicit Quick | [`workflows/profiles/quick-generate.md`](workflows/profiles/quick-generate.md) |
| Create Template | [`workflows/create-template.md`](workflows/create-template.md) |
| Edit Native PPTX | [`workflows/edit-native-pptx.md`](workflows/edit-native-pptx.md) |

**Hard rule — selected authority only**: Do not load another top-level route's
procedure after routing. Image to PPTX and Beautify are mutually exclusive;
Image to PPTX activates Quick, while Beautify selects from explicit Quick
intent. Never load both runtimes. Supporting documents refine one route; they
never compete with it.

---

## Authored Expression Range

**Reference — not a constraint**: what a generated page can carry. Text — inline
emphasis runs, lead-in, kicker, pull quote, hero number, takeaway line. Geometry
— 187 Office presets, Boolean merge, connectors, freeform, page-field and
outline-carrier composition. Image — full-bleed field, editorial crop, shaped
picture, registered layers, scrim and spotlight, cross-page continuity. Paint —
gradients, channel alpha, native shadow and glow, halftone, faceted form.
Recurrence — one cross-page motif varied by page role. Each form's syntax lives
in the selected runtime authority's construction references.

---

## Vocabulary

One meaning per term across every loaded file. Where a word is used in
more than one sense, the sense is named here and the files say which one.

| Term | Meaning |
|---|---|
| **Reference** (label) | A starting sketch the executing role adjusts or replaces freely, with no upstream repair or stated reason; `(binding)` after a field label removes that freedom |
| **Relationships** | The §IX line naming a page's semantic units and their source-stated `order` / `link` / `parent` / `membership` / `contrast` / `overlap`, or `none` |
| **Topology decision** | The per-page yes/no on whether geometry must carry the page's `Relationships` (`topology=yes` / `topology=no`); unrelated to `pptx_structure.mode` |
| **`pptx_structure.mode`** | `flat` (every object Slide-local) or `structured` (declared Master/Layout/slot metadata); a packaging route, never information structure |
| **Composition** | The §IX `Composition` line: a Reference for a page's macro composition, hierarchy, and focus |
| **Image pattern** | The §VIII column carrying one image-composition suggestion in ordinary words (optionally citing `#P`/`#M` ids) |
| **Layout** | A PowerPoint Layout under a Master, or the Layout template kind; never a page-composition sketch |
| **Device** | An everyday page carrier — card, band, icon-and-label, KPI tile, divider, quote block — recalled in the Executor's device menu |
| **Carrier** | What a page unit sits in: a device, an image, or native geometry; the family names are carrier and field, direction and sequence, grouping and ownership, emphasis and annotation. `data-pptx-carrier` is a structured-slot attribute, not this term. The **carrier receipt** is the checker's per-page inventory of what was actually drawn |
| **Page job** | What one page must do for the reader; the input every carrier, contour, and effect decision is judged against |
| **Page field** | One large surface, outline, aperture, or off-canvas contour that organizes zones instead of a card per unit |
| **Contour / preset / atom** | A contour is a shape's silhouette; a preset is one of the 187 Office `prst` contours drawn through `preset_shape_svg.py`; an atom is one object that compiles to one DrawingML shape |
| **Geometry signature** | The retained line `page job → composition move → contour / edge language` kept per page and compared before the next page |
| **Texture** (of a block) | Whether a §IX block is prose, bullets, keywords, or labels; distinct from visual texture (grain, halftone) |
| **Anchor** | Two senses: a lock anchor (a deck-wide color, type, or spacing value) and the `page_rhythm` tag `anchor` for structural pages |
| **Sheet / slice / plate** | A sheet is one generated image holding several elements on a chroma key; a slice is one element cut from it; a plate is a registered full-canvas layer of several non-overlapping objects |
| **Module line** | The `P<NN> modules: …` line written before each page naming the triggered modules it uses |
| **Mode** | Named by qualifier: communication `mode` (how the deck argues), reading mode (`consumption_mode`), `generation_mode` (`continuous` / `split`), `pptx_structure.mode`, `replication_mode` (how a template was created) |

## Phase Frame

Every route is one Plan → Do·Check·Act cycle: Plan ends when every authoring
input exists as a file or retained decision; Do authors pages, Check runs the
route's gates, Act repairs at the owning layer (discipline 7), and the cycle
ends at export. Step numbers stay as written.

| Phase | Default | Quick | Edit Native | Create Template |
|---|---|---|---|---|
| **Plan** | Steps 1–5 | §2 | §1–4 | Steps 1–3 |
| **Do·Check·Act** | Steps 6–7 | §3–4 | §5–7 | Steps 4–8 |

## Global Execution Discipline

1. **Serial execution** — Follow the selected authority's steps in order. A completed non-blocking step may continue directly to the next eligible step.
2. **Blocking means stop** — At every `⛔ BLOCKING` gate, wait for explicit user confirmation. Do not decide on the user's behalf.
3. **No cross-phase bundling** — Do not combine work across an unclosed gate. Once the route's final user gate closes, later non-blocking steps may continue automatically.
4. **Gate before entry** — Verify every listed prerequisite before entering a step.
5. **No speculative execution** — Do not prepare later-phase artifacts before their owning step.
6. **Deterministic routing** — Do not add a route-choice question when [`routing.md`](workflows/routing.md) resolves the request. If a route prerequisite is missing, state it and stop that route.
7. **Act at the owning layer** — On failure, repair at the shallowest layer that owns the fault: the page for a page-local issue, the Plan artifact for a roster/spec/resource fault, the owning source artifact for a tool failure; then resume from the route's declared pointer. Do not silently downgrade a required artifact.

## Global Communication Rules

- Match the user's language and source language unless the user explicitly overrides it.
- Localize user-facing option labels and explanations. Render each fixed message template (role-switch banner, completion report) in the user's chat language when it differs from the template's. Keep exact enum IDs or field names when needed for precision.
- Keep `design_spec.md` section headings and field names in the template's original English; content values may use the user's language.
- Before switching roles, read the corresponding role reference and output:

```markdown
## [Role Switch: <Role Name>]
📖 Reading role definition: references/<filename>.md
📋 Current task: <brief description>
```

---

## Platform Adaptation (TeleAgent / SnSworker)

本技能为 TeleAgent 预置分发，以下平台适配规则叠加在上游工作流之上：

### Python 运行时（断网就绪）

- 宿主内置自管 Python 运行时（`tabtin-python` / `python3`，3.12），**已预置本技能全部 Python 依赖**（python-pptx、XlsxWriter、skia-pathops、uharfbuzz、PyMuPDF、mammoth、markdownify、openpyxl、Pillow、numpy、requests、beautifulsoup4、flask 等，见 `packages/python-runtime/requirements-skill-bundles.txt`）。**无需执行 `pip install -r requirements.txt`**，断网环境直接可用。
- Windows 下 `python3` 若为 WindowsApps 桩（退出码 9009），按上游规则改用 `python`；两者都指向内置运行时。
- PDF/DOCX/XLSX/PPTX 源转换（source_to_md）依赖均在内置运行时，断网可用。

### 云端能力与断网降级

- **AI 生图**：优先使用宿主内置 `ImageGen` / `ImageGenWithRef` 工具生成图片素材，再接入本技能管线（替代上游 `image_gen.py` 的云端后端）；`image_gen.py` 的 gpt-image-2/gemini 等云端后端仅在公网 + `.env` 密钥就绪时可用。
- **网络图搜 / 旁白 TTS（edge-tts）/ 话题联网调研**：需公网。断网环境跳过图搜（用排版/图标/原生图形替代）、跳过旁白，其余管线完整可用。
- `.env` 密钥配置读取顺序：进程环境 → 当前目录 → 技能目录 → `~/.ppt-master/.env`。

### 与其他 PPT 技能的分流

| 用户诉求 | 路由 |
|---|---|
| 通用 PPT / 深度需求（原生图表、公式、模板蒸馏、编辑既有 PPTX、多画布） | 本技能 |
| 中国电信深红运营风格汇报（经营分析/座谈会/宣贯/红白高密度） | `teleagent/telecom-ppt-master-pro`（其 T1-T35 电信模板体系） |
| 电信品牌通用模板 | 本技能 `templates/brands/中国电信` 与 `templates/decks/中国电信`（原生品牌模板） |

## Repository Compatibility

- This package is a workflow/skill, not a generic application scaffold. Do not create `.worktrees/`, `tests/`, branch workflows, or generic engineering structure by default.
- Keep required workflow, reference, script, and template documentation inside this Skill directory.
- Repository-level documents may point into the package; package runtime files must not depend on repository-level instructions.
- On Windows, if a documented `python3 ...` command is unavailable, rerun the same command with `python`.
- Sponsor information is optional reference material. Read the matching [`SPONSORS.md`](SPONSORS.md) or [`SPONSORS_CN.md`](SPONSORS_CN.md) only when the user explicitly requests a model, AI image model, API/provider, or hosted-service recommendation. Never surface sponsor or model recommendations proactively during normal generation, troubleshooting, or quality review.
