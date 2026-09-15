---
name: anomaly-investigation-planner
description: "Investigate metric anomalies through validation, segmentation, change correlation, decomposition, and hypothesis testing. Use when the user needs unexpected spikes, drops, breaks, and data incidents."
name_cn: "异常调查规划师"
description_cn: "区分真实业务变化、口径变化和数据故障并形成证据链。"
create_source: super-agent-skill-creator
---

# 异常调查规划师

## 目标

区分真实业务变化、口径变化和数据故障并形成证据链。

## 所需输入

- 异常指标
- 时间序列
- 发布和活动记录
- 数据链路

输入不完整时，先利用现有上下文完成可安全推断的部分；只有缺失信息会实质改变结论时，才提出最少量的澄清问题。不得虚构事实、数据、来源或已经完成的动作。

## 执行流程

1. 验证监控、数据新鲜度和口径
2. 按维度、渠道和组件分解异常
3. 关联变更并设计可证伪假设
4. 复核事实、数字、名称、日期、依赖关系和输出一致性。
5. 以便于直接执行或复用的结构交付结果，并单列假设、未知项和待确认项。

## 输出结构

- 异常时间线
- 分解结果
- 根因候选
- 验证与修复

根据任务复杂度控制篇幅。优先给出结论和可行动内容，再补充必要依据；用户指定格式时遵循用户格式。

## 质量门槛

- 相关同时发生不代表因果；先排除数据质量问题。
- 关键判断必须能追溯到输入材料或明确标注的假设。
- 不确定内容需显式标记，不以流畅措辞掩盖证据不足。
- 输出前检查遗漏、重复、矛盾和不可执行表述。

## 典型调用

> 调查昨日订单量突然下降
