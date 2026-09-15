---
name: work-efficiency-analyzer
description: "上传工作周报/日报/月报/项目汇报等材料，自动提取工作内容，从自动化潜力、技能覆盖度、重复性、耗时占比、质量敏感度五维评估每项工作的TeleAgent适配度，生成匹配技能、优化方案、推荐提示词案例和可视化HTML单页报告。当用户提到'工作分析'、'提效分析'、'赋能分析'、'工作效率'、'能力匹配'、'工作内容分析'、'TeleAgent能帮我做什么'时触发。"
name_cn: 工作赋能分析器
description_cn: 上传工作材料，自动分析每项工作的TeleAgent适配度、优化空间和推荐提示词，生成HTML报告
create_source: super-agent-skill-creator
---

# 工作赋能分析器

## 概述

用户上传工作材料（周报/日报/月报/年报/项目汇报/工作总结），本技能分析材料中的每项工作内容，评估TeleAgent的适配程度，生成可视化HTML报告。

## 工作流

### Phase 1: 材料收集与解析

1. 接收用户上传的文件（支持 .docx/.pdf/.xlsx/.csv/.txt/.md）
2. 用对应工具读取文件内容（docx技能/pdf技能/xlsx技能/read工具）
3. 多文件时，逐个读取后合并为统一文本

**关键提取目标：**
- 用户姓名、部门/岗位（如有）
- 时间范围（周/月/季度）
- 每项具体工作内容描述
- 工作频率（日/周/月）
- 已使用工具/系统
- 协作对象/上下游

### Phase 2: 工作内容结构化

从材料文本中提取结构化工作项列表。每个工作项包含：

```json
{
  "name": "工作项名称（6-12字精炼概括）",
  "description": "工作内容描述（来自材料的原文摘要+补充）",
  "category": "所属大类（方案编制|客户经营|文档撰写|会议沟通|项目管理|技术开发|安全管理|信息采集|培训学习|行政审批|数据分析|创意设计）",
  "frequency": "高频(每日/每周多次)|中频(每周1-2次)|低频(每月/季度)",
  "estimated_hours_per_week": 估算每周耗时(小时),
  "tools_used": ["当前使用的工具/系统"],
  "pain_points": ["该工作的痛点/耗时环节"]
}
```

**提取原则：**
- 颗粒度：一份周报通常拆为5-15个工作项
- 不要把"日常巡检"和"写巡检报告"混为一项，拆开
- 从周报/日报的时间投入描述中推算耗时
- 项目制工作按阶段拆分（如：需求阶段/开发阶段/交付阶段）

### Phase 3: TeleAgent能力匹配与适配度评估

读取 [teleagent-capability-map.md](references/teleagent-capability-map.md) 获取完整技能/能力清单。

对每个工作项执行：

1. **关键词匹配**：用工作项的name+description+category+tools_used+pain_points与能力图谱中每条技能的关键词触发字段做匹配
2. **语义匹配**：对关键词未覆盖的，从技能的核心能力描述做语义判断
3. **确定匹配技能列表**，每个匹配标注 match_level: exact（精准匹配）或 partial（近似/部分覆盖）

#### 五维适配度评分

| 维度 | 代码 | 评分规则 |
|------|------|---------|
| 自动化潜力 | D1 | 纯文本生成→85-95, 数据处理→65-85, 半结构化→45-65, 需人工判断→25-45, 实地操作→5-25 |
| 技能覆盖度 | D2 | 有exact匹配技能→85-95, 只有partial→55-75, 需组合→35-55, 暂无→5-30 |
| 重复性 | D3 | 每日→90-100, 每周多次→75-90, 每周1次→55-75, 每月→35-55, 季度/年度→15-35 |
| 耗时占比 | D4 | 占30%以上→85-100, 占15-30%→60-85, 占5-15%→35-60, 占5%以下→10-35 |
| 质量敏感度 | D5 | 模板化→15-35, 半结构化→40-60, 高度定制→65-85, 合规强相关→75-95 |

#### 综合适配度

```
fitness_score = D1*0.25 + D2*0.30 + D3*0.15 + D4*0.15 + (100-D5)*0.15
```

#### 适配度等级

| 分数 | 等级 | 含义 |
|------|------|------|
| 85-100 | S | 深度适配，可实现80%+自动化 |
| 70-84 | A | 高度适配，可实现60-80%自动化 |
| 55-69 | B | 中度适配，可实现40-60%自动化 |
| 40-54 | C | 低度适配，可实现20-40%自动化 |
| 0-39 | D | 弱适配，自动化空间有限 |

#### 优化空间评级

| 星级 | 条件 |
|------|------|
| ★★★★★ | fitness≥80 且 D1≥80 且 重复性高（D3≥70）→ 从数天→分钟级 |
| ★★★★ | fitness≥70 且 (D1≥70 或 D2≥80) → 从数小时→分钟级 |
| ★★★ | fitness≥55 → 从数小时→半小时级 |
| ★★ | fitness≥40 → 部分环节提效 |
| ★ | fitness<40 → 仅辅助参考 |

### Phase 4: 优化方案与提示词生成

对每个工作项生成：

#### 现状分析（current_status）
1-3句话描述当前怎么做、痛点在哪、耗时长短

#### 优化方案（optimized_approach）
1-3句话描述用TeleAgent后怎么做、哪些环节被自动化、关键技能名称

#### 推荐提示词（recommended_prompts）
针对每个匹配技能，生成2-3个实际可用的提示词案例，格式：

```json
{
  "prompt": "具体的提示词内容（用户可直接复制使用）",
  "scenario": "适用场景说明"
}
```

提示词生成原则：
- 必须具体到用户的实际工作内容，不要泛泛而谈
- 包含技能@引用（如"@电信商客三段法"）
- 考虑用户上传材料中的具体项目名/客户名
- 每个提示词应有明确的输入输出

### Phase 5: 工作方向与能力分析

基于所有工作项生成全局分析：

#### 方向分析（direction_analysis）
- 用户的核心工作方向是什么（从category分布判断）
- 哪些方向占比最多
- 有哪些被忽视但潜力方向

#### 能力画像（capability_profile）
- 用户当前擅长什么（从工作内容深度判断）
- 短板在哪（从痛点/低效环节推断）
- 与TeleAgent结合后的能力增强点

#### 赋能策略（empowerment_strategy）
- 分优先级的赋能建议（先做什么后做什么）
- ROI最高的3个入手点

#### 实施路径（implementation_path）
- 第1周/第2周/第3周/第4周的渐进式计划

#### 能力缺口（gaps）
- TeleAgent当前无法覆盖的场景
- 建议孵化的自定义技能

### Phase 6: 生成HTML报告

1. 将所有分析结果组装为JSON结构（参考下方JSON Schema）
2. 用 scripts/generate_html.py 脚本生成HTML文件
3. 保存到工作空间根目录，文件名格式：`{用户姓名}工作赋能分析报告.html`

#### JSON Schema

```json
{
  "user_name": "用户姓名",
  "department": "部门/岗位",
  "analysis_date": "2026-07-07",
  "material_summary": "材料覆盖时间范围和主要内容概述（50-100字）",
  "work_items": [
    {
      "name": "工作项名称",
      "description": "描述",
      "category": "大类",
      "frequency": "高频|中频|低频",
      "estimated_hours_per_week": 数值,
      "fitness_score": 数值(0-100),
      "fitness_grade": "S|A|B|C|D",
      "optimization_stars": 1-5,
      "saving_hours_per_week": 数值,
      "current_status": "现状分析",
      "optimized_approach": "优化方案",
      "dimensions": {
        "automation_potential": D1,
        "skill_coverage": D2,
        "repetitiveness": D3,
        "time_weight": D4,
        "quality_sensitivity": D5
      },
      "matched_skills": [
        {"id": "技能ID", "name": "技能名称", "match_level": "exact|partial"}
      ],
      "recommended_prompts": [
        {"prompt": "提示词", "scenario": "场景"}
      ]
    }
  ],
  "work_direction": {
    "direction_analysis": "工作方向分析",
    "capability_profile": "能力画像",
    "empowerment_strategy": "赋能策略",
    "implementation_path": "实施路径",
    "gaps": [
      {"title": "缺口标题", "description": "缺口描述和建议"}
    ]
  },
  "overall_assessment": {
    "avg_fitness": 平均适配度,
    "total_saving_per_week": 总周省时,
    "sa_count": S+A级数量,
    "skill_coverage_rate": 技能覆盖率
  }
}
```

## 约束

1. **必须有材料**：不能凭空分析，用户必须上传工作材料。若无材料，提示用户上传
2. **不泄露内部信息**：适配度评估过程不暴露评分算法给用户，但五维雷达图需展示
3. **提示词必须可用**：每个推荐提示词必须是用户复制粘忑就能用的，不要占位符
4. **省时估算需保守**：宁可低估不要高估，标注"估算值"
5. **等级评定严格**：S级需满足fitness≥85且D2≥80，不要轻易给S
6. **区分match_level**：核心能力精准命中=exact，边缘/间接=partial
