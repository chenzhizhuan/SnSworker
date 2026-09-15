---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '11799928-7bba-4177-94f9-001d2deaaf2b'
  PropagateID: '11799928-7bba-4177-94f9-001d2deaaf2b'
  ReservedCode1: '632b8469-a92d-4bcc-a96b-a9afa885a791'
  ReservedCode2: '632b8469-a92d-4bcc-a96b-a9afa885a791'
---

# 图形布局智能匹配指南 (v7.1)

> 本文件定义了"内容逻辑 → 图形布局"的智能匹配规则。
> 引擎代码位于 `assets/graphic-layouts.js`，提供10种原生pptxgenjs图形布局。
> 所有布局使用pptxgenjs原生形状，PPT中完全可编辑。

---

## 1. 图形布局清单 (T25-T34)

| 模板 | 布局名 | 函数名 | 适用场景 | 内容数量 |
|------|--------|--------|---------|---------|
| T25 | 时间轴 | `drawTimeline` | 历程回顾、阶段推进、里程碑 | 3-8个节点 |
| T26 | 流程箭头 | `drawProcessFlow` | 业务流程、处理步骤、加工链 | 2-7个步骤 |
| T27 | 金字塔 | `drawPyramid` | 需求层次、分层架构、优先级 | 3-6层 |
| T28 | 循环图 | `drawCycle` | PDCA闭环、持续优化、轮转机制 | 3-6个阶段 |
| T29 | 总分结构 | `drawTree` | 架构总览、组织分解、分类展开 | 2-6个分支 |
| T30 | 漏斗图 | `drawFunnel` | 转化分析、筛选漏斗、流失分析 | 3-6个阶段 |
| T31 | 殿堂框架 | `drawTemple` | 基础+支撑+目标、保障体系 | 2-5根柱子 |
| T32 | 垂直步骤 | `drawVerticalSteps` | 自上而下推进、下沉执行 | 3-7个步骤 |
| T33 | 阶梯进化 | `drawStaircase` | 能力升级、进阶路径、逐步提升 | 3-6级 |
| T34 | 价值链 | `drawValueChain` | 上下游产业链、端到端流程 | 3-6个环节 |

---

## 2. 内容逻辑识别规则

### 2.1 关键词检测矩阵

| 逻辑类型 | 触发关键词 | 推荐布局 |
|---------|-----------|---------|
| **时间序列** | 月、季度、阶段、先…再…最后、历程、里程碑、roadmap | T25 时间轴 |
| **流程递进** | 流程、步骤、输入→处理→输出、pipeline、管道 | T26 流程箭头 |
| **层级递进** | 总分、分层、需求层次、马斯洛、金字塔 | T27 金字塔 |
| **循环闭环** | 循环、闭环、PDCA、持续优化、反馈、轮转 | T28 循环图 |
| **总分展开** | 总体、总览、架构、组织、分解、结构图、树形 | T29 总分结构 |
| **逐层递减** | 漏斗、转化、筛选、逐层削减 | T30 漏斗图 |
| **基础支撑** | 基础+支柱+目标、底座、基础保障、支撑体系 | T31 殿堂框架 |
| **下行推进** | 第一步…第二步、自上而下、下沉、推进 | T32 垂直步骤 |
| **进阶提升** | 升级、进阶、逐步提升、进化、阶梯 | T33 阶梯进化 |
| **端到端链** | 价值链、上游…下游、产业链、supply chain | T34 价值链 |

### 2.2 结构特征加分

| 条目数 | 加分规则 |
|-------|---------|
| 2个 | 流程箭头 +2 |
| 3个 | 循环图 +2，金字塔 +1 |
| 4个 | 循环图 +1 |
| ≥5个 | 时间轴 +1 |

### 2.3 默认回退

当无明确关键词匹配时：
- 条目 ≤4 → 默认总分结构 (T29)
- 条目 ≥5 → 默认时间轴 (T25)

---

## 3. 使用方式

### 3.1 在生成代码中引入

```javascript
const gl = require('./graphic-layouts.js');
const layouts = gl.create(pres);

// 自动推荐
const rec = layouts.recommendLayout(contentItems);
console.log('推荐布局:', rec.layout, '原因:', rec.reason);

// 手动调用
const slide = pres.addSlide();
layouts.drawTimeline(slide, x, y, w, h, milestones, { theme: 'telecom-red' });
```

### 3.2 函数参数格式

```javascript
// T25 时间轴
drawTimeline(slide, x, y, w, h, [
  { label: '启动阶段', date: 'Q1', desc: '制定方案' },
  { label: '推进阶段', date: 'Q2', desc: '全面执行' },
], { theme: 'telecom-red' })

// T26 流程箭头
drawProcessFlow(slide, x, y, w, h, [
  { label: '需求分析', desc: '调研一线痛点' },
  { label: '方案设计', desc: '制定策略' },
], { theme: 'telecom-red' })

// T27 金字塔（从顶层到底层）
drawPyramid(slide, x, y, w, h, [
  { label: '战略目标', desc: '存增一体' },
  { label: '策略层', desc: '续约+维系' },
  { label: '执行层', desc: '派单+攻坚' },
], { theme: 'telecom-red', sideNote: '从战略到执行' })

// T28 循环图
drawCycle(slide, x, y, w, h, [
  { label: '计划', desc: '' },
  { label: '执行', desc: '' },
  { label: '检查', desc: '' },
  { label: '改进', desc: '' },
], { theme: 'telecom-red', centerLabel: 'PDCA' })

// T29 总分结构
drawTree(slide, x, y, w, h,
  { label: '存量固升行动' },
  [
    { label: '到期续约', items: ['升套分期', '分类施策', '升星结合'] },
    { label: '主被动维系', items: ['抓闭环', '定责任', '优机制'] },
  ],
  { theme: 'telecom-red' })

// T30 漏斗图
drawFunnel(slide, x, y, w, h, [
  { label: '全部到期用户', value: '10000户', pct: '100%' },
  { label: '触达用户', value: '8000户', pct: '80%' },
  { label: '续约成功', value: '6000户', pct: '60%' },
], { theme: 'telecom-red' })

// T31 殿堂框架
drawTemple(slide, x, y, w, h,
  '存量固升行动',
  ['续约策略', '执行操盘', '维系体系'],
  '佣金改革·存增一体',
  { theme: 'telecom-red' })

// T32 垂直步骤
drawVerticalSteps(slide, x, y, w, h, [
  { label: '分析研判', desc: '识别流失风险' },
  { label: '策略匹配', desc: '分类施策' },
  { label: '触达执行', desc: '多触点攻坚' },
], { theme: 'telecom-red' })

// T33 阶梯进化
drawStaircase(slide, x, y, w, h, [
  { label: 'L1 基础维系', desc: '被动响应' },
  { label: 'L2 主动维系', desc: '提前触达' },
  { label: 'L3 智能维系', desc: 'AI预测' },
], { theme: 'telecom-red' })

// T34 价值链
drawValueChain(slide, x, y, w, h, [
  { label: '需求识别', desc: '到期预警' },
  { label: '策略匹配', desc: '分类施策' },
  { label: '触达执行', desc: '多触点' },
  { label: '效果评估', desc: '闭环复盘' },
], { theme: 'telecom-red' })
```

---

## 4. 安全边界

所有图形布局在使用时，需确保：
- 整体区域在电信主题安全区内：y=0.55~7.05", x=0.45~12.88"
- 预留导航栏(y=0~0.52")和页脚(y=7.05~7.50")空间
- 文字字号 ≥7pt，正文10-12pt，标题12-14pt
- 形状间距 ≥0.1"，避免重叠
- 颜色使用主题配色，不引入未定义色值

---

## 5. 与diagram-drawing技能的协作

当内容逻辑过于复杂（如含决策分支、泳道分栏、多层级嵌套），原生形状难以表达时，可调用diagram-drawing技能生成PNG嵌入：

| 场景 | 方案 | 输出 |
|------|------|------|
| 简单流程/时间轴/金字塔等 | **优先使用graphic-layouts.js** | pptxgenjs原生形状，可编辑 |
| 复杂决策流程（含判断分支） | 调用diagram-drawing生成flowchart | PNG图片嵌入 |
| 泳道图（跨角色协作） | 调用diagram-drawing生成swimlane | PNG图片嵌入 |
| 思维导图（发散结构） | 调用diagram-drawing生成mindmap | PNG图片嵌入 |
| 鱼骨图（因果分析） | 调用diagram-drawing生成fishbone | PNG图片嵌入 |

**原则：能用原生形状的优先用原生，保证可编辑性。**

---

> **版本**: v7.1 | **来源**: mck-ppt-design设计逻辑参考 + diagram-drawing协作方案 + 电信场景适配