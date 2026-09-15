# 能力状态

能力状态只说明 Skill 自带实现；本机是否可用仍以 `scripts/check_environment.py --json` 的结果为准。

| 能力 | 状态 | 实现/边界 |
|---|---|---|
| PptxGenJS 新建 Deck | stable | `assets/telecom-boilerplate.js`、`assets/progress-preview/`；需要 Node.js 与 `pptxgenjs` |
| python-pptx 模板起始构建 | stable | `scripts/build_on_template.py`；内置 5G 模板验证 5 种基础页型 |
| T1-T24 页面规范 | stable-guidance | `references/page-templates.md`；按项目选择实现，不代表通用构建器全部内置 |
| T25-T34 原生图形 | stable | `assets/graphic-layouts.js` |
| 模板 Layout Map | stable | `assets/template-analyzer.py`；字体继承只做有限可观察提取 |
| PowerPoint COM 渲染/编辑 | environment-dependent | Windows + 已安装 PowerPoint；不作为跨平台保证 |
| LibreOffice/Poppler 渲染 | environment-dependent | 由环境检查发现，不随 Skill 安装 |
| 原生动画/旁白/SmartArt 无损编辑 | external | 需要 PowerPoint 自动化或专用 OOXML 实现；`python-pptx` 不保证 |
| Python SVG 高级管道 | external | 本 Skill 只保留接口说明；源码和依赖未通过检查时为 unavailable |
| 输出 PPTX 文件级校验 | stable | `scripts/validate_output_pptx.py`，标准库实现 |
| 逐页视觉判断 | agent-review | 必须基于真实渲染图；脚本不能替代目视 QA |

状态含义：

- `stable`：Skill 自带确定性实现并有回归测试。
- `stable-guidance`：规范稳定，但具体页面仍由项目代码实现。
- `environment-dependent`：实现依赖本机软件。
- `external`：需要 Skill 外部组件；不得假装内置。
- `agent-review`：需要基于可见工件判断，不能只靠结构脚本。
