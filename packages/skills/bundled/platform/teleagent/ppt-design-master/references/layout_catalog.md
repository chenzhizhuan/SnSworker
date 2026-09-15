---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '722c6b9b-8f38-4eec-b1e5-f89a81aa288e'
  PropagateID: '722c6b9b-8f38-4eec-b1e5-f89a81aa288e'
  ReservedCode1: 'b65233f8-ca82-4d2c-a4ab-7cb2c4ee909b'
  ReservedCode2: 'b65233f8-ca82-4d2c-a4ab-7cb2c4ee909b'
---

# Layout Catalog — 61-Page Template Library

## Layout Type Summary

| # | Layout Type | Count | Page Numbers |
|---|-----------|-------|--------------|
| 1 | Flowchart / progressive | 16 | 4,6,8,13,20,22,23,24,31,32,33,34,39,40,44,51 |
| 2 | Left-right split-column | 14 | 12,16,19,42,45,46,47,48,49,53,54,55,58,61 |
| 3 | Grid / modular parallel | 8 | 7,27,30,37,38,43,56,59 |
| 4 | Radial / center-anchor | 8 | 10,11,17,18,25,28,36,50 |
| 5 | Directory / TOC | 2 | 21,41 |
| 6 | Single-column list | 5 | 9,14,26,29,35 |
| 7 | Matrix / overview | 3 | 4,5,39 |
| 8 | Transition page | 1 | 52 |
| 9 | Cover page | 1 | 1 |
| 10 | Horizontal flow nav | 1 | 2 |

## Layout Details

### Cover Page (Page 1)
- Large centered title + subtitle
- Bottom gradient ribbon (yellow → orange → red)
- Date below subtitle

### Horizontal Flow Navigation (Page 2)
- Three-row layout: 售前/售中/售后
- Each row: label + flow nodes + arrows + output artifact
- Good for: high-level process overview with 3 parallel tracks

### Flowchart / Progressive (Pages 4,6,8,13,20,22-24,31-34,39-40,44,51)
- Time axis with numbered circular nodes
- Sub-items below each node
- Best for: sequential processes, step-by-step procedures
- Key function: `addFlowNode()`, `addArrowRight()`

### Left-Right Split-Column (Pages 12,16,19,42,45-49,53-55,58,61)
- Title bar on left or top
- Two content columns with cards, text, or tables
- Best for: comparisons, paired content, detail breakdowns
- Key function: `addCard()`, `makeTable()`

### Grid / Modular Parallel (Pages 7,27,30,37-38,43,56,59)
- 2×2, 2×3, or 3×3 grid of equal cards
- Each card: colored title + body text
- Best for: parallel capabilities, feature sets, module overview
- Key function: `addCard()`

### Radial / Center-Anchor (Pages 10-11,17-18,25,28,36,50)
- Central concept with radiating sub-topics
- Best for: ecosystem diagrams, capability maps, cycle processes
- Note: Pages 25/28 use simplified shapes for original hand-drawn illustrations

### Directory / TOC (Pages 21,41)
- Left section list + right preview area
- Best for: chapter navigation, section dividers

### Single-Column List (Pages 9,14,26,29,35)
- Title bar + vertical bullet list
- Best for: guidelines, key points, simple text-heavy content

### Matrix / Overview (Pages 4,5,39)
- Cross-reference table with row/column headers
- Alternating pink/white row fills
- Best for: management frameworks, capability matrices
- Key function: `makeTable()`

### Transition Page (Page 52)
- Full-screen large text (calligraphy style)
- Best for: section dividers, motivational slogans
- Example: "提能提质 提效提速"

## Matching Rules

When given new material, map content to layouts:

1. **Sequential process** → Flowchart (page 4/6/8 pattern)
2. **Parallel items (2-6)** → Grid modular (page 7/27 pattern)
3. **Two-sided comparison** → Left-right split (page 42/45 pattern)
4. **Ecosystem / hub-spoke** → Radial anchor (page 10/36 pattern)
5. **Data table** → Matrix with makeTable (page 4 pattern)
6. **Data comparison** → Bar chart cards (page 7 pattern)
7. **Data trend** → Line chart (addChart LINE)
8. **Data proportion** → Pie chart (addChart PIE)
9. **Chapter start** → Directory TOC (page 21 pattern)
10. **Key points list** → Single-column list (page 9/14 pattern)
11. **Section divider** → Transition page (page 52 pattern)
12. **Cover** → Cover page (page 1 pattern)

Combine layouts as needed — a typical 20-page PPT might use: cover + TOC + 5 flow + 3 split + 2 grid + 2 data charts + transition + 4 list + ending.

> AI生成