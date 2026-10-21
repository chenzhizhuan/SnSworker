---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '18e949fd-3f17-4b3b-ac53-91aea7ce355b'
  PropagateID: '18e949fd-3f17-4b3b-ac53-91aea7ce355b'
  ReservedCode1: '3458adf4-2b62-4256-8b2b-26a06af5a456'
  ReservedCode2: '3458adf4-2b62-4256-8b2b-26a06af5a456'
---

# SKILL.md 补丁意图记录（防重复审查对照）

本文件为 Review 阶段的意图备忘，不属于交付物规范。若与 SKILL.md 冲突，以 SKILL.md 为准。

## 本次变更点
1. description 触发词新增：HTML交互版、HTML幻灯片、网页版PPT
2. 素材总览表新增：templates/ppt-html-template.html
3. 参考文件索引新增模板条目；调用流程第1步新增 HTML 交互版路由
4. 新增「HTML交互版PPT（网页演示）」章节：选型表/使用流程/交互功能清单/常见陷阱（file:// 拦截、控制条自动隐藏、并行会话浏览器占用、视觉快照锚定、长文件分步构建、CSS 变量纪律）

## 验证结论（本次会话实测）
- 封面/章节/卡片/三列/流程/KPI表格/结尾 7 类页面 Playwright + 视觉模型检查通过
- 主题切换（c8→c3）全页生效并持久化 localStorage；#p3 深链正常；控制台仅 favicon 404（无碍）
- 控制条 3.5s 自动隐藏属预期；并行会话占用浏览器时用新标签页规避