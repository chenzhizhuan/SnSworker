# 工件合同

完整生产任务使用机器可读工件传递决策。小范围原生编辑可只使用 `source-manifest.json`、change set、`qa-report.json` 和 `delivery-manifest.json`。

## 工件链

| 工件 | 产生阶段 | 最小职责 | 对应校验 |
|---|---|---|---|
| `source-manifest.json` | 来源盘点 | 文件、哈希、用途、权威级别、敏感性 | 项目级检查 |
| `deck-requirements.json` | 需求锁定 | 字段状态、风险、来源、冲突、规划就绪状态 | `validate_requirements.py` |
| `slide-plan.json` | 页面规划 | 顺序、角色、主张、证明对象、模板、来源 | `validate_slide_plan.py` |
| `design-lock.json` | 设计锁定 | 画布、主题、模板、字体、引擎、QA 模式 | `validate_design_lock.py` |
| `build-manifest.json` | 生成 | 输入/输出、引擎、模板哈希、生成时间、能力回退 | 项目级检查 |
| `qa-report.json` | QA | 文件、内容、视觉、Deck 四层结果及逐页状态 | `validate_qa_report.py` |
| `delivery-manifest.json` | 交付 | 交付文件、哈希、已验证范围、限制 | 项目级检查 |

## source-manifest.json

```json
{
  "version": 1,
  "sources": [
    {
      "id": "SRC-001",
      "path": "sources/经营数据.xlsx",
      "sha256": "...",
      "role": "source-of-truth",
      "priority": 1,
      "confidentiality": "internal"
    }
  ]
}
```

来源路径相对项目目录；不要把用户绝对路径写入可复用 Skill 资产。

## slide-plan.json

```json
{
  "version": 1,
  "deck_title": "示例经营分析",
  "slides": [
    {
      "slide": 1,
      "role": "cover",
      "claim": "示例经营分析",
      "proof_object": "cover",
      "template": "T1",
      "source_refs": ["N/A"],
      "macro_layout": "cover-section-closing"
    },
    {
      "slide": 2,
      "role": "result",
      "claim": "核心指标总体达成，但存量续约承压",
      "proof_object": "KPI cards",
      "template": "T13",
      "source_refs": ["SRC-001#Sheet1!A1:F8"],
      "macro_layout": "single-proof"
    }
  ]
}
```

`source_refs` 必须可追溯。封面、导航、章节和纯收尾页可使用 `N/A`，其他页不得使用 `N/A` 逃避来源记录。

## design-lock.json

```json
{
  "version": 1,
  "canvas": {"width_in": 13.333, "height_in": 7.5, "aspect_ratio": "16:9"},
  "theme": "telecom-red",
  "preset": "telecom-report",
  "template": {"mode": "built-in", "path": "assets/电信5G原生模板1.0.pptx", "sha256": "..."},
  "fonts": {"cjk": "Microsoft YaHei", "latin": "Arial", "fallbacks": ["SimHei"]},
  "engine": "python-pptx",
  "qa_mode": "standard",
  "semantic_colors": {"brand": "#C00000", "positive": "#16A34A", "warning": "#D97706"}
}
```

模板模式为 `none` 时可省略路径和哈希。使用用户模板或内置模板时必须记录哈希。

## qa-report.json

```json
{
  "version": 1,
  "deck": "output/result.pptx",
  "qa_mode": "standard",
  "slide_count": 3,
  "checks": {
    "file": {"status": "pass", "evidence": ["validate_output_pptx: OK"]},
    "content": {"status": "pass", "evidence": ["source refs checked"]},
    "visual": {"status": "pass", "evidence": ["preview/contact-sheet.png"]},
    "deck": {"status": "pass", "evidence": ["contact sheet reviewed"]}
  },
  "slides": [
    {"slide": 1, "visual_status": "pass", "evidence": "preview/slide-01.png"},
    {"slide": 2, "visual_status": "pass", "evidence": "preview/slide-02.png"},
    {"slide": 3, "visual_status": "pass", "evidence": "preview/slide-03.png"}
  ],
  "limitations": []
}
```

`standard` 和 `strict` 模式要求所有页面有视觉证据。无法渲染时把视觉状态设为 `not-run`，在 `limitations` 中写明原因，且不得把正式交付标记为已完成视觉 QA。

## delivery-manifest.json

至少记录：

- 最终 PPTX 及可选 PDF/PNG/源代码的相对路径和 SHA256。
- 使用的模板、主题、引擎和 QA 模式。
- `qa-report.json` 路径。
- 未验证限制、回退和已知兼容性差异。
