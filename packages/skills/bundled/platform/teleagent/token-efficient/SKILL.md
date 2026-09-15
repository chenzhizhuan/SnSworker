---
name: 省token高效
description: Minimize token consumption across various AI agents by enforcing concise-response discipline and context hygiene. FORCED for ALL conversations and ANY task (office work, coding, Q&A, writing, chatting) - always on, no need for the user to ask. Trigger on any user message, any task. Works model-agnostic (no vendor cache dependency).
name_cn: 降低token消耗-多快好省
description_cn: 任何对话、任何任务默认强制触发，无需用户要求。通过精简回复纪律和上下文精简，在任何模型下降低 token 消耗。适用于日常办公、问答、写作、编程、闲聊等一切场景。
create_source: 借鉴 lokikill123/codex-token-skills 通用化改造
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '3df17e43-15f9-4f98-b1f9-9613e5b09ec1'
  PropagateID: '3df17e43-15f9-4f98-b1f9-9613e5b09ec1'
  ReservedCode1: '22797413-52ea-4069-a85b-32600b282b36'
  ReservedCode2: '22797413-52ea-4069-a85b-32600b282b36'
---

# 省 token 高效响应

> **强制触发**：本规范对所有对话、任何任务强制生效，无需用户要求或 @ 触发。触发来源两条：①全局指令 `CLAUDE.md`（工作区根目录）已写入强制条款；②本技能描述已覆盖任意消息。跨平台/上架时，本条 skill 即全量生效。
> **豁免**：长文档写作、深度分析报告、复杂方案设计等需要完整输出的任务，可放开简短约束，按需完整输出。

遵循以下纪律减少输出与输入 token，适用于任何模型与平台。

## 回复纪律（省输出）
1. 非明确要求，一次只答要点，一句话说清
2. 不重读本轮已读过的文件，直接复用已有内容
3. 跳过开场白、总结、进度播报、客套话
4. 不主动生成计划/测试/构建，除非明确要求
5. 改文件直接说结果：文件名 + 一句描述
6. 不用 Mermaid、表格、超 10 行代码块，除非必要

## 上下文管理（省输入）
1. 稳定内容（规则、清单）放前面，动态内容（日期、最新数据）放后面
2. 长文件按需分段读，不整篇反复读
3. 批量任务合成一条 prompt，别拆成多次来回
4. 大段输出写进文件，不回灌到对话
5. 复用已有结果，不重复计算/查询已确认的数据

## 记忆复用
- 项目背景、用户偏好、已定结论写入记忆文件，跨会话直接读取，不重新解释
- 仅追加、不删旧，纠正用追加说明