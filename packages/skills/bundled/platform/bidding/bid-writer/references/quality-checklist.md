# Quality Checklist

Use this checklist before self-review or delivery checks on AI-generated bid proposal content.

## Coverage

- The user's responsibility scope is explicit: assigned sections, out-of-scope sections, related dependencies, and handoff outputs.
- All hard requirements are identified and tracked.
- All scoring items and values are extracted.
- Each in-scope scoring item maps to at least one assigned response section or is marked `待补充`.
- Out-of-scope scoring items are not silently drafted; they are marked `范围外`, `关联项`, or `他人负责`.
- The draft content explicitly supports the target section and does not drift into unrelated material.

## Tender Grounding

- The draft is grounded in the tender document, scoring criteria, and provided materials.
- Final proposal prose does not expose source-index behavior.
- Final proposal prose avoids `根据招标文件`, `依据招标文件要求`, `详见招标文件`, `招标文件第 X 条`, or similar phrases.
- Tender terminology, service scope, deliverables, and evaluation priorities are transformed into bidder response language.

## Evidence and Hallucination Control

- Company qualifications, certifications, cases, personnel, tools, platforms, data, and commitments come from provided materials.
- Missing evidence is marked as `待补充素材` or `需人工确认` in analysis outputs.
- The draft does not invent project names, customer names, performance data, implementation methods, or legal commitments.

## Writing Quality

- The bidder perspective is consistent, usually `我司`.
- Wording is professional, stable, sincere, and specific.
- Headings are concise and not overly templated.
- Headings avoid AI-like patterns such as `XXX与XXX`, `XXX和XXX`, and overlong paired abstractions.
- Paragraphs under each heading are sufficiently developed.
- Headings with only 1-2 short paragraphs are merged or expanded.
- Empty slogans such as `加强管理`, `高度重视`, and `确保质量` are avoided unless followed by concrete measures.

## Duplicate Content

- Check for exact duplicate paragraphs.
- Check for repeated blocks with only minor word changes.
- Check for repeated tables with the same structure and similar content.
- Check for repeated headings that carry the same meaning.
- Check that page-count expansion does not rely on copied paragraphs, repeated templates, or repeated scenario blocks.
- Remove, merge, or rewrite duplicated content before delivery.

## Visual Aids

- Check whether each visual is necessary and helps explain implementation logic, process flow, schedule arrangement, responsibility flow, risk handling, or delivery closure.
- Check that visuals are not decorative filler or page-count filler.
- Check that image labels match the proposal prose and do not introduce unsupported facts.
- Check that visuals are placed near the relevant content and have a short explanation or caption.
- Remove visuals that are vague, inaccurate, redundant, or less clear than prose/table content.

## Heading Numbering

- Check whether the Word document uses automatic heading numbering.
- If automatic numbering is active, heading text must not include manual numbers such as `23.8.1`.
- Check for duplicated heading display such as `23.8.15.4 23.8.15.4 标题`.
- Fix duplicated numbering proactively before delivery.

## Structure and Format

- The outline follows the user's required section numbering if provided.
- Tables have clear field names and consistent terminology.
- Tables are used for comparable data, not to package normal prose.
- The content separates analysis notes, draft text, risks, and missing materials.
- The final output format matches the user's requested document or section format.

## Page Count

- Clarify whether page count applies to the whole document or a single section.
- Verify page count from the actual Word/PDF output, not by word count.
- If the user asks for a single section to exceed a page count, compute the start page of that section and the start page of the next section.
- Report the section page count explicitly.

## Self-Review Output

When reporting self-review results, use this structure:

```text
总体结论：可移交合规审查 / 需补充后移交 / 存在高风险，暂不移交

主要问题：
| 问题类型 | 位置 | 风险等级 | 说明 | 修改建议 |

范围说明：
- 我负责：
- 他人负责 / 范围外：
- 需协同：

待补充材料：
- ...

人工确认事项：
- ...

已完成检查：
- 评分点覆盖：
- 重复内容检查：
- 配图必要性检查：
- 标题编号检查：
- 页数检查：
```
