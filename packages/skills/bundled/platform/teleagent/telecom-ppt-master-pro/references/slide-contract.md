---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '0b5d9536-324a-46e3-9e7e-aed90baeead6'
  PropagateID: '0b5d9536-324a-46e3-9e7e-aed90baeead6'
  ReservedCode1: 'fbdb70de-a5ea-4144-8410-c214f3fa5883'
  ReservedCode2: 'fbdb70de-a5ea-4144-8410-c214f3fa5883'
---

# Slide Contract

在写 pptxgenjs 代码之前填写此表格。将规划变成检查清单。

| Slide | Role | Claim-or-Topic | Proof Object | Template | Source | Notes |
|-------|------|----------------|--------------|----------|--------|-------|
| 1 | Cover | 封面标题 | 封面 | T1 | 用户需求 | 日期 |

## 字段含义

- **Slide**：最终顺序中的页码
- **Role**：该页在演示中的角色（context/method/result/comparison/summary/transition/Q&A）
- **Claim-or-Topic**：该页回答的问题或表达的信息
- **Proof Object**：主要视觉证据（方法图/流程/对比表/结果图/KPI/时间线/截图/总结矩阵）
- **Template**：T1-T16 中的基础模板；如果有升级，写 `T# + local variant`
- **Source**：内容来源（用户文档/论文/数据表/生成大纲/假设/推导计算）
- **Notes**：裁剪决策、拆分警告、演讲备注线索

## Pass/Fail 规则

- 每页必须只有一个主要角色
- 每个内容页必须回答一个主要问题或表达一个主要信息
- 商业/汇报类应使用主张式标题（如"转化率下降是因为回访用户减少"）
- 学术类可用主题标题，但必须具体（如"消融实验表明图编码是主要增益来源"）
- 电信汇报类默认使用主张式标题（如"宽带渗透率环比提升3.2个百分点"）
- 每个内容页最多一个主要证明对象，辅助标签只能指向该对象
- 封面/TOC/章节分隔/总结/致谢可用 `transition/overview/closing` 作为证明对象
- 如果某页没有证明对象且不是过渡页，则规划失败
- 需要多证明对象的页面应拆分
- Template 必须是 T1-T16 或 `T# + local variant`
- Source 不能为空；仅在用户未提供素材时用 `assumption`
- 每份 deck 必须定义颜色语义并一致使用

## 受控升级规则

仅在默认模板无法清晰表达内容时使用。在 Notes 中写明原因。

**允许的升级**：
- 在 T1-T16 基础上组合轻量组件
- 将模糊标题改为具体的主张式标题
- 为关键页添加证明对象/takeaway bar/侧边栏/callout
- 替换重复模板页的节奏
- 扩展主题色以添加少量语义色

**必需条件**：
- 不从空白开始设计
- 不跳过 Slide Contract
- 不跳过视觉 QA
- 不跳过 Deck QA
- 不破坏脚本路径或使幻灯片不可复现

**回退规则**：如果升级后视觉 QA 失败两次或 Deck QA 失败一次，保留内容并返回最近的 T1-T16 基础模板。

## Table Contract (v6.0 新增 · Layer 1)

当页面包含表格数据时，需额外填写 Table Contract：

| 字段 | 含义 | 示例 |
|------|------|------|
| `TableID` | 表格标识 | `TBL-01` |
| `DataSource` | 数据来源引用 | `Excel!Sheet1.A1:F17` |
| `Position` | 表格在页面上的锚定坐标 | `x=0.5, y=2.0, w=12.33, h=4.5` |
| `ColSpec` | 列宽/对齐/格式规范 | `[w=2.0:左, w=1.5:右:千分位, ...]` |
| `RowSpec` | 行高/条件格式规范 | `[header:h=0.5:bold, data:h=0.35, ...]` |
| `ConditionFormat` | 条件格式规则 | `排名≤3:color=C00000:bold, 值<0:color=C00000` |
| `AutoComment` | 自动点评要求 | `首行/末行/极值需生成文字点评` |

### Table Contract 规则

1. **精准落位**：表格位置必须从 Layout Map 的占位符坐标获取（锚定模式）或由 Slide Contract 的 Proof Object 推导
2. **列宽总和**必须等于 Table Contract 中的 `w` 值
3. **条件格式**优先从 `refinement-mapping.md` 的映射表中查找
4. **自动点评**：标记 `AutoComment` 的表格必须附带数据点评文字

### Table Contract 示例

```
TableID: TBL-01
DataSource: 移动新增及合约数据统计表.xlsx!5-6月.A1:F17
Position: x=0.5, y=1.8, w=12.33, h=4.8
ColSpec: [分公司:w=2.5:左, 5G-A:w=1.8:右:千分位, 5G:w=1.8:右:千分位, ...]
RowSpec: [header:h=0.5:深红底白字加粗, data:h=0.3:交替行, summary:h=0.5:加粗]
ConditionFormat: 排名≤3:color=C00000:bold
AutoComment: 极值（最高/最低）需生成点评
```

## Template Contract (v6.0 新增 · Layer 2)

当用户提供模板时，Slide Contract 增加锚定列：

| Slide | Role | Claim-or-Topic | Proof Object | Template | **Layout** | **Anchors** | **Overrides** | Source | Notes |
|-------|------|----------------|--------------|----------|-----------|------------|--------------|--------|-------|

### 新增字段含义

- **Layout**：引用的 Layout Map 中的 layout 索引，格式为 `L{index}` 或 layout 名称
- **Anchors**：内容→占位符的映射，格式为 `角色→idx{N}`，多个用逗号分隔
- **Overrides**：需要覆盖的样式，格式为 `idx{N}.属性=值`，多个用分号分隔

### Template Contract 规则

1. Layout 必须是 Layout Map 中存在的合法索引或名称
2. Anchors 中的占位符索引必须存在于对应 Layout 中
3. 不走占位符的额外元素标注在 Notes 列
4. 锚定模式（全锚定/半锚定/灵感锚定）在 Notes 首行标注
5. 如果某页不使用模板锚定，Layout 列填 `-`（走标准 T1-T16）

### Template Contract 示例

| Slide | Role | Claim | Proof | Template | Layout | Anchors | Overrides | Source | Notes |
|-------|------|-------|-------|----------|--------|---------|-----------|--------|-------|
| 1 | Cover | 封面 | — | T1 | L0 | 标题→idx0, 副标题→idx1 | — | 需求 | 全锚定 |
| 3 | Result | Q3经营概览 | KPIx3 | T13 | L4 | 标题→idx0, KPI区→idx1, 结论→idx3 | idx3.font.size=10 | Excel | 半锚定 |

## 电信风格特殊规则

使用 `telecom-red` 主题（或 `telecom-report` 预设）时，Slide Contract 还需遵守：

1. **预设必须是 `telecom-report`**，除非用户明确要求其他预设
2. **主题必须是 `telecom-red`**，除非用户明确更换
3. **安全区域**：有效内容区 y=0.55"~7.05"（区别于通用主题 y=1.85"~7.1"）
4. **启动模板**：使用 `assets/telecom-boilerplate.js` 而非 `assets/boilerplate.js`
5. **内容模式**：每页需标注适用的内容模式（参见 `content-patterns.md` 的15种模式）
6. **文字风格**：遵循 `writing-style.md` 中的电信体/通报体/管控体