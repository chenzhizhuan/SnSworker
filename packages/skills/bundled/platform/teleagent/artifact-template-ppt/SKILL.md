---
name: artifact-template-ppt
description: "Create or edit China Telecom-style internal presentations (电信红白高密度汇报PPT) with pptxgenjs. Use when the user selects this template, names 电信红白高密度汇报PPT, asks for 电信/中国电信 red-white compact PPT materials, or explicitly invokes artifact-template-ppt for project reports, innovation results, advanced-role or craftsman presentations, training exchanges, team building, security, digitalization, AI, or internal leadership briefings."
name_cn: 电信红白高密度汇报PPT
description_cn: "按电信红白、文字紧凑、证据优先的风格生成项目与内部汇报PPT，保留参考母版视觉系统，用 pptxgenjs 输出可编辑 PPTX"
create_source: super-agent-skill-creator
---

# 电信红白高密度汇报PPT

Use `assets/reference.pptx` as the visual reference. Analyze its layout coordinates, colors, and structure with python-pptx, then replicate the visual system in pptxgenjs. Do not clone the file directly; rebuild from the design specifications.

Treat the reference content, section order, and story sequence as examples only. The customer's communication goal controls what the deck says, which sections exist, and how they are ordered. Preserve the visual system, not the sample narrative.

## Required resources

1. Read `references/design-system.md` — canvas grid, brand palette, header system, typography, information blocks, image system, density control.
2. Read `references/content-and-layout.md` — narrative models, direct title rules, page logic options, reference layout library, example structures, speaker-note rules, evidence hierarchy.
3. Read `references/master-prompts.md` when planning the deck, drafting a reusable prompt, or handing work to another agent.
4. Read `references/qa-checklist.md` before export and delivery.
5. Inspect `assets/reference.pptx` with python-pptx to extract exact shape coordinates, fill colors, and layout patterns when precision is needed.
6. View `assets/preview.png` for a quick visual reference of the cover style.

## PPT generation method

Use **pptxgenjs** (Node.js) to generate the PPTX file. Install with `npm install pptxgenjs` in a `.temp/` working directory if not already available.

Key adaptation points from reference.pptx to pptxgenjs:

- Canvas: 13.33" × 7.5" (LAYOUT_WIDE)
- All coordinates in design-system.md are in pixels at 1280×720 base; convert to inches for pptxgenjs (divide by 96)
- Alternatively, analyze reference.pptx EMU values with python-pptx and convert: inches = EMU / 914400
- Use shape naming conventions from the reference (e.g., `title-N`, `rule-red-N`, `keyword-N`) for maintainability
- Embed China Telecom logo from reference.pptx (extract with python-pptx) or use a text placeholder if logo image is unavailable

## Workflow

1. Inspect every supplied PPTX, DOCX, PDF, spreadsheet, image, and user instruction.
2. Build a fact ledger before writing:
   - verified project names;
   - dates, scale, duration, counts, before/after results;
   - roles, honors, customers or users;
   - available real screenshots and photos;
   - unresolved or conflicting claims.
3. Define the communication job in one sentence: by the end, the intended audience should understand or approve what, because of which central evidence.
4. Select a narrative model that matches the customer's request, such as question–answer, chronology, status review, comparison, decision recommendation, process explanation, case evidence, capability overview, training enablement, or another suitable structure.
5. Build a slide map with: slide number, direct title, communication job, verified evidence, layout choice, optional four-character tag, image plan, and speaker-note purpose.
6. Map each slide to the closest reference slide layout (see layout library in `references/content-and-layout.md`). Vary layouts by content; do not inherit the reference slide order or force every slide into one repeated panel arrangement.
7. Write a pptxgenjs Node.js script that reproduces the visual system from `references/design-system.md`. Preserve logo position, typography, margins, header rail, footer, palette, density, and spacing.
8. Replace sample content with current-task content. Never reuse names, numbers, honors, projects, or claims from the reference unless the current sources verify them.
9. Prefer real evidence:
   - system screenshots;
   - project-site photos;
   - training and team photos;
   - test reports, certificates, dashboards, or result records.
   If evidence is unavailable and the user wants to add it later, create a clearly labeled editable image frame. Never fabricate official evidence, UI, logos, certificates, or project scenes.
10. Add natural Chinese speaker notes after the visible slide content is stable. Align every note with the page evidence and the source speech.
11. Run the script to generate PPTX. Inspect each slide at full size, fix all issues (title wrapping, text overflow, image clipping, element overlap, logo inconsistency, empty placeholders, page numbers), and export a distinct editable PPTX.

## Hard rules

- Lead with content, evidence, and logic; use visuals to prove or organize, not decorate.
- Write every substantive title as a direct description of the page. Put the recognisable project, product, topic, decision, or module name first; state the page-specific point, result, question, or comparison second.
- Keep all title banners on one line. Shorten the wording before reducing the inherited title size.
- Keep visible body text compact but readable. Do not create large empty areas beside undersized text.
- Use authentic China Telecom brand assets. Keep the logo consistently at upper left on content slides.
- Keep cover and closing minimal. Do not add people to cover or closing unless the user explicitly asks.
- Avoid stars, wheat, city silhouettes, military silhouettes, cartoon people, decorative technology backgrounds, gratuitous gradients, and repeated stock illustrations.
- Do not use generic agenda pages unless the deck genuinely needs an agenda or the user asks for one.
- Do not force "背景—方案—成效", "问题—措施—结果", or any other fixed story pattern.
- Do not automatically add background, safety, team, training, outlook, or summary pages. Include only what the customer's goal and source materials require.
- Do not treat the retained slide sequence as the required deck sequence.
- Do not overstate "一线、基层、边疆" unless those distinctions are material to the current audience and sources.
- Do not invent data to fill a metric box. Delete, merge, or repurpose unused slots.
- Do not generate fake screenshots or pseudo-official marks.
- Use AI-generated imagery only for clearly illustrative, non-evidentiary concepts and only when real material is unavailable or the user requests it.
- Preserve user-owned files and unrelated workspace changes.

## Craftsman or advanced-role mode

Only when the task needs five craftsman dimensions without naming the formal "五力", use one near-synonym four-character tag per relevant module:

- 务实求效
- 精研求新
- 迎难攻坚
- 示范带动
- 薪火相传

Connect each tag to a verified deed on the same slide. Do not show the formal "××力" labels unless the user explicitly asks.

## Output standard

Deliver an editable PPTX with:

- one clear narrative job per slide;
- direct one-line titles;
- traceable facts and images;
- consistent telecom branding;
- concise, natural speaker notes;
- no unintended overlap, clipping, empty structural placeholders, or broken media.
