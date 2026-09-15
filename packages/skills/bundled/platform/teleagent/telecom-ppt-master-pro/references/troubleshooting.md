---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '03e04097-89f7-45d0-b0c5-f261633fd89b'
  PropagateID: '03e04097-89f7-45d0-b0c5-f261633fd89b'
  ReservedCode1: '0986bf4c-8e6e-40bb-82dc-16afb9627d06'
  ReservedCode2: '0986bf4c-8e6e-40bb-82dc-16afb9627d06'
---

# Troubleshooting

症状 → 根因 → 修复方案。遇到问题时 Ctrl+F 搜索。

## 生成错误

### `Cannot find module 'pptxgenjs'`
**根因**：`NODE_PATH` 未指向全局 `node_modules`
**修复 (Windows)**：
```powershell
$env:NODE_PATH = (npm root -g)
node gen_main.js
```

### 中文引号导致 `SyntaxError`
**根因**：中文弯引号（""''）泄露进 JS 字符串
**修复**：使用 Unicode 转义 `\u201C\u201D` 或直接改写

### `ENOENT: no such file or directory`
**根因**：图片路径错误
**修复**：使用 `path.join(__dirname, "figures", "foo.png")`

### 脚本挂起无输出
**根因**：忘记 `.then()`/`.catch()` 或文件被 PowerPoint 锁定
**修复**：
```js
pres.writeFile({ fileName: "out.pptx" })
  .then(name => console.log("DONE:", name))
  .catch(err => { console.error("ERR:", err); process.exit(1); });
```

## 版式 Bug

### 内容被页脚遮挡
**根因**：所有元素总高度超过安全区域
**通用主题修复顺序**：缩小间距 → 精简文字 → 减小填充 → 拆分页面 → 最后才减小字体
**电信主题修复**：有效内容区仅 y=0.55"~7.05"（比通用主题更紧凑），优先使用内容均分机制 `itemH = (7.05 - 0.55 - 标题占高) / 条目数`

### 右对齐标签被裁剪
**根因**：文字宽度超出文本框右边界
**修复**：缩短标签或加宽文本框

### 卡片高度/宽度不一致
**根因**：手算坐标偏离
**修复**：用统一公式 `const CW = (W - 0.8 - 0.6) / 3` 计算

### 嵌入图片像素化
**根因**：源 PNG 分辨率太低
**修复**：`pdftoppm -png -r 250 source.pdf figures/output`

### 中文显示为方框
**根因**：`fontFace` 值不匹配已安装字体
**修复**：用 `Microsoft YaHei`（Windows）或 `PingFang SC`（macOS）

### 电信主题：元素超出底部横幅
**根因**：电信底部横幅 7.08~7.50"，比通用主题页脚区域更大
**修复**：
1. 检查所有元素 y+h ≤ 7.05"
2. 使用高度均分 `itemH = (7.05 - startY) / itemCount`
3. 优先压缩底部间距 → 减小字号（最小 7pt） → 最后才拆分页面

### 电信主题：内容超出顶部通栏
**根因**：元素 y 值 < 0.55"
**修复**：所有正文起始 y ≥ 0.55"，标题文字使用 `addTelecomNav` 自动定位在通栏内

## 内容质量问题

### "看起来像文字堆砌"
→ 重构为 T6/T7/T8/T11/T13 结构化模板

### "单页信息太多"
→ 拆分为 2 页

### "视觉层级扁平"
→ 选一个元素放大 1.5 倍/加粗/主题色，降级其他元素

### "看起来像 AI 生成的"
→ 用结构化模板，嵌入实际图表，变化页面类型

### 电信主题："数字不突出"
→ 使用 `fmtNumber(text, withBg)` 格式化：红色加粗 + 可选黄底

### 电信主题："卡片像通用模板"
→ 使用 `drawTelecomCard` 生成电信风格卡片（浅粉填充 + 标题栏浅粉底板 + 红色竖条装饰）

### 电信主题："文字太长"
→ 遵循 `writing-style.md` 规范：每条 ≤15字，数字目标红色加粗，拒绝长句

## 版本节奏修复

| 失败 | 修复操作 |
|------|---------|
| 标题空泛 | 改写为"主题 + 具体结论" |
| 页面拥挤 | 拆分或换 T7/T8/T11 |
| 连续 3 页卡片 | 插入或替换为 T5/T9/T11/T12/T13/T14/T15 |
| 无证明对象 | 从来源拉图表/流程/KPI/矩阵/对比 |
| 实验页像数据倾泻 | 加 takeaway bar，高亮胜出行/系列 |
| 方法页只列组件 | 用 T11 重建为信息流/管道 |
| 总结不闭合论述 | 重写连接问题、方法、证据、意义 |

### 电信节奏修复

| 失败 | 修复操作 |
|------|---------|
| 数字目标不突出 | 使用 T13 KPI 模板或 `fmtNumber()` |
| 缺少对比分析 | 插入 T6 两栏对比页 |
| 缺少闭环逻辑 | 插入 T11 流程图，体现事前→事中→事后 |
| 总结缺少逻辑链 | T15 底部加红色横幅，含完整逻辑链 → 最终目标 |
| 内容模式选择错误 | 参考 `content-patterns.md`，按输入类型匹配模式 |
| 文字风格不统一 | 参考 `writing-style.md`，统一为电信体/通报体/管控体 |