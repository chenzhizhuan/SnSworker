---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '29faf5c6-fd6f-4473-83cc-b6d724f86e26'
  PropagateID: '29faf5c6-fd6f-4473-83cc-b6d724f86e26'
  ReservedCode1: 'e11f456d-99b6-439a-8299-d26ddad9c8b5'
  ReservedCode2: 'e11f456d-99b6-439a-8299-d26ddad9c8b5'
---

# 数据智能层 (Layer 1 · Data Intelligence)

> v6.0 新增 | 优先级：Phase 2

## 1. 解决什么问题

用户提供 Excel 表格时，系统不仅读取数据，还能**自动理解数据含义→生成数据点评→精准落位到PPT页面**。从"搬数据"升级为"理解数据"。

## 2. 核心能力

### 2.1 Excel 智能解析

| 能力 | 说明 | 示例 |
|------|------|------|
| 层级识别 | 自动识别表头→行标题→数据的层级关系 | 分公司→5G-A→5G→4G |
| 数据类型推断 | 区分文本/数值/百分比/日期/金额 | "35,877"→数值, "16.38%"→百分比 |
| 异常检测 | 自动识别空值、负数、极值、同比异常 | 续约率-5%→异常标记 |
| 汇总行识别 | 区分数据行与合计/全省行，合计行不参与排名 | "合计"行排除 |
| Sheet间关联 | 多Sheet同结构数据自动关联对比 | 4个Sheet的地市5G-A数据汇总排名 |

### 2.2 自动数据点评

对导入的数据自动生成3类点评：

| 点评类型 | 触发条件 | 生成模板 |
|----------|---------|---------|
| 极值点评 | 数据中出现最大/最小值 | "合肥以35,877户领先，淮北1,256户垫底" |
| 趋势点评 | 含环比/同比数据 | "5G-A渗透率环比提升3.2个百分点" |
| 结构点评 | 数据可分组对比 | "前3名合计占比51.2%，集中度较高" |
| 预警点评 | 数据低于阈值或为负 | "续约率仅16.4%，低于20%警戒线" |

点评风格遵循 `writing-style.md` 中的电信体规范。

### 2.3 Table Contract 机制

将 Excel 数据映射为 PPT 表格的精准落位规范。

完整 Table Contract 定义见 `slide-contract.md` §Table Contract。

## 3. 工作流

### Step 1A: Excel 接收与预处理

```
用户提供 Excel → 读取全部 Sheet → 识别数据结构 → 生成数据摘要 → 用户确认
```

**数据摘要模板**：

```
📊 数据摘要

文件：移动新增及合约数据统计表.xlsx
共 4 个 Sheet：5-6月、3-4月、1-2月、10-12月
每个 Sheet 结构：17行×6列（含表头）

关键数据识别：
  - 主键列：分公司（16个地市 + 1个合计行）
  - 数值列：5G-A、5G、4G、4G以下、合计
  - 汇总行：第17行"合计"（不参与排名）

跨Sheet聚合建议：
  → 将4个Sheet的5G-A列汇总排名
  → 合肥以绝对优势领先，淮南5-6月爆发

是否确认此数据理解？如需调整请说明。
```

### Step 1B: 数据点评生成

基于确认的数据理解，自动生成点评：

```javascript
// 点评生成逻辑（在代码中实现）
function generateDataComment(data, type) {
  const max = Math.max(...data.map(d => d.value));
  const min = Math.min(...data.map(d => d.value));
  const maxItem = data.find(d => d.value === max);
  const minItem = data.find(d => d.value === min);
  
  // 极值点评
  return `${maxItem.name}以${fmtNumber(max)}户领先，${minItem.name}${fmtNumber(min)}户垫底`;
}
```

点评插入位置：
- 表格下方独立文本框（推荐）
- 或 Takeaway bar 中
- 或 KPI 卡片中

### Step 1C: Table Contract 填写

根据数据结构自动填写 Table Contract：

```
TableID: TBL-01
DataSource: 移动新增及合约数据统计表.xlsx!汇总排名.A1:F17
Position: x=0.5, y=1.8, w=12.33, h=4.8
ColSpec: [
  排名:w=0.8:居中,
  分公司:w=2.0:左,
  5G-A:w=1.9:右:千分位:红色加粗,
  5G:w=1.9:右:千分位,
  4G:w=1.9:右:千分位,
  合计:w=1.9:右:千分位:加粗
]
RowSpec: [
  header:h=0.45:深红底白字加粗,
  top3:h=0.35:浅粉底红色加粗,
  data:h=0.30:交替行,
  summary:h=0.45:加粗灰底
]
ConditionFormat: 排名≤3:整体color=C00000:bold
AutoComment: 首位和末位需生成点评
```

## 4. 数据→页面模板映射

| 数据特征 | 推荐模板 | Table Contract 要点 |
|----------|---------|-------------------|
| 排名/对比数据 | T10 表格 + T13 KPI | 前3标红，末3标灰 |
| 时间序列 | T9 图表(折线) | Y轴从0开始，关键点数据标签 |
| 多指标对比 | T9 图表(分组柱状图) | 各指标不同颜色，底部图例 |
| 占比/构成 | T9 图表(饼图) + T13 KPI | 百分比标签在外，首位放大 |
| 交叉分析 | T12 双栏 + T10 小表 | 左栏卡片+右栏数据表 |
| 大量表数据(>20行) | T10 表格(跨页) | 分页，每页≤12行，续页带表头 |
| 仪表盘型 | T14 网格(3x3/2x3) | 每格1个KPI+迷你趋势 |
| 地市排名 | T10 表格 + 条件格式 | 热力渐变或Top3标红 |

## 5. 数字格式化规范

| 数据类型 | 格式 | 代码 |
|----------|------|------|
| 整数(≥1000) | 千分位 | `Number.toLocaleString()` → "35,877" |
| 整数(<1000) | 直接显示 | "256" |
| 金额(万元) | 千分位+"万" | "300.5万" |
| 百分比 | 1位小数+"%" | "16.4%" |
| 同比/环比 | 带符号+百分比 | "+3.2%" / "-1.5%" |
| 排名 | 整数+"位" | "合肥 1位" |
| 户均 | 保留整数+单位 | "20元" |

电信主题数字强调：目标数字必须使用 `fmtNumber(text, true)` 红色加粗+黄底。

## 6. 与各层的交互

| 交互层 | 关系 |
|--------|------|
| Layer 2 · 模板锚定 | Table Contract 的 Position 从 Layout Map 的占位符坐标获取 |
| Layer 3 · 风格记忆 | 自动点评的文字风格从 WRITING_STYLE.md 获取 |
| Layer 4 · 创意设计 | 数据驱动的页面设计走本层推荐模板，创意元素由 Layer 4 补充 |
| Layer 5 · 精控执行 | 表格微调（列宽/条件格式/标红等）走 Layer 5 的映射表 |

## 7. Excel 读取代码模板

```javascript
// 读取Excel并生成表格的通用模板
function generateTableFromExcel(slide, data, contract, theme) {
  const { Position, ColSpec, RowSpec, ConditionFormat } = contract;
  
  // 构建表头行
  const headerRow = data.headers.map((h, i) => ({
    text: h,
    options: {
      bold: true,
      color: theme === 'telecom-red' ? 'FFFFFF' : 'FFFFFF',
      fill: theme === 'telecom-red' ? { color: 'C00000' } : { color: theme.primary },
      fontSize: 10,
      align: ColSpec[i].align || 'center'
    }
  }));
  
  // 构建数据行
  const tableRows = [headerRow];
  data.rows.forEach((row, rowIdx) => {
    const isTop3 = ConditionFormat && rowIdx < 3;
    const isSummary = row.isSummary;
    const dataRow = row.cells.map((cell, colIdx) => {
      let options = {
        fontSize: 9,
        align: ColSpec[colIdx].align || 'center'
      };
      
      // 条件格式
      if (isTop3) {
        options.color = 'C00000';
        options.bold = true;
      }
      if (isSummary) {
        options.bold = true;
        options.fill = { color: 'F5F5F5' };
      }
      
      // 交替行
      if (!isTop3 && !isSummary && rowIdx % 2 === 1) {
        options.fill = { color: 'FFF0F0' }; // 电信浅粉
      }
      
      // 数字格式
      if (ColSpec[colIdx].format === '千分位' && typeof cell === 'number') {
        return { text: cell.toLocaleString(), options };
      }
      
      return { text: String(cell), options };
    });
    tableRows.push(dataRow);
  });
  
  // 添加表格
  slide.addTable(tableRows, {
    x: Position.x,
    y: Position.y,
    w: Position.w,
    colW: ColSpec.map(c => c.w),
    rowH: [RowSpec.header.h, ...data.rows.map((_, i) => 
      i < 3 && RowSpec.top3 ? RowSpec.top3.h : 
      data.rows[i].isSummary ? RowSpec.summary.h : RowSpec.data.h
    )],
    border: { type: 'solid', pt: 0.5, color: 'E8B4B4' },
    autoPage: false
  });
}
```

## 8. 回退规则

1. Excel 读取失败 → 通知用户，请求提供 CSV 或截图
2. 数据结构识别不确定 → 展示识别结果让用户确认
3. 自动点评与用户期望不符 → 用户可直接修改，修改意见沉淀到 Layer 3
4. 数据量超出单页容量 → 自动分页，每页≤12行数据