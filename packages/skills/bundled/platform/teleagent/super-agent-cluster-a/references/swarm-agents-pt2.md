---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '806b9bd9-7fe3-4363-9055-c1198829317f'
  PropagateID: '806b9bd9-7fe3-4363-9055-c1198829317f'
  ReservedCode1: '6eed1ef4-a099-40e4-88e4-30f6899fc313'
  ReservedCode2: '6eed1ef4-a099-40e4-88e4-30f6899fc313'
---

# 蜂群智能体系统（补充）

> 从 swarm-agents.md 拆分。

## Agent标识规范

在Task Agent调用中标注Agent标识：

- 在Task Agent的prompt开头标注 `[Agent-搜索型]` `[Agent-分析型]` `[Agent-编码型]` `[Agent-核查型]` `[Agent-验证型]` `[Agent-综合型]` `[Agent-运维型]` `[Agent-元认知]` 之一（共8种类型，与SKILL.md一致）
- 返回结果时Agent自称标识
- [Agent-验证型]审查时引用标识定位问题来源
- [Agent-搜索型] 搜索前需执行搜索环境对抗性预评估
- [Agent-核查型] 的核查包含强制15项+条件触发16项检查（详见 quality-rules.md）
- [Agent-分析型] 分析包含结构因果模型SCM、多层级贝叶斯模型等高级分析方法
- [Agent-综合型] 负责文档生成（用户通过question工具选择生成时，规则14+规则15），必须通过generate_docx.py生成docx
- [Agent-运维型] ⛔系统运维操作需要管理员权限时，不自动降级为只读诊断模式；应提示用户逐项确认并说人话说明影响。⛔提权前强制披露执行内容——对每项需提权的操作，Agent必须在用户确认前完整展示将执行的确切命令/脚本内容，经用户逐项审查确认后方可提权执行。提权方式为通过 `Start-Process -Verb RunAs` 触发 UAC（用户点"是"即授权执行已审查的命令），⛔禁止将多项破坏性操作合并为单个脚本一次 UAC 授权（每项破坏性操作独立提权、独立 UAC 授权），禁止生成最终交付脚本让用户手动运行（临时脚本写入 `.temp/` 执行后自动清理）（运维能力清单与权限约束详见 SKILL.md「系统运维操作能力」章节，此处不再重复），操作前须经[Sentinel]安全审查，破坏性操作须经用户确认
- Agent标识统一使用 `[Agent-类型名]` 方括号格式，禁止混用其他写法

### Agent全生命周期7节点强制标注（与SKILL.md步骤透明化规范联动）

每个spawn的Agent在其执行的每个Step中必须完整标注以下7个生命周期节点，缺一不可（详见SKILL.md「Agent全生命周期7节点强制标注」和 step-transparency-examples.md）：

| 节点序号 | 节点名称 | 标注内容 |
|---------|---------|---------|
| 1.spawn | Agent生成 | Agent类型+子任务摘要+输入摘要+spawn时间戳 |
| 2.执行计划 | 计划制定 | TAOR-Think阶段产出+计划步骤数+预计耗时 |
| 3.关键操作 | 核心执行 | TAOR-Act阶段产出+关键工具调用+搜索轮次/来源数 |
| 4.内部决策 | 推理决策 | TAOR-Observe+Reflect阶段产出+决策依据+置信度评估 |
| 5.结果返回 | 产出交付 | 输出摘要+返回token数+证据强度等级+来源分级T1-T4 |
| 6.Handoff/消亡 | 生命周期终结 | Handoff目标Agent或消亡原因+存活时长+token消耗 |
| 7.TAOR反思 | 经验沉淀 | Reflect反思摘要+改进建议+是否触发运行时专家切换 |

**强制规则**：

- 7节点标注在Swarm阶段每个Agent的Step中完整呈现，不允许省略
- 节点5.的来源分级T1-T4与SKILL.md搜索真实性强制规则联动（详见 execution-guide.md 来源分级表）
- 节点7.TAOR反思与三组认知准则（第一性原理+提问追问、世界级专家、批判性思维）联动
- 嵌套spawn场景下，Worker的7节点标注在主Agent的Step中完整呈现，不可因嵌套而省略

## Agent高频协同矩阵

Agent间协同遵循A2A协议（Agent-to-Agent，Google 2025）标准化Handoff机制。每个spawn的Agent携带标准化能力声明卡（Agent Card），主Agent通过卡片匹配任务与Agent。

| 协同组合 | 适用场景 | 典型任务 | A2A消息类型 |
|---------|---------|---------|------------|
| [Agent-搜索型] + 搜索编排 | 多维度信息采集 | 多源搜索+动态策略调整 | `a2a_collab` |
| [Agent-搜索型] + [Agent-核查型] | 采集+核查 | 采集后立即数字回溯和来源校验 | `a2a_handoff` |
| [Agent-编码型] + [Sentinel] | 代码执行+安全 | 代码生成前安全审查+沙箱逃逸检测 | MCP安全审查前置 |
| [Agent-分析型] + [Agent-验证型] | 建模+对抗 | 量化分析后红蓝攻防验证 | `a2a_result` |
| [Agent-验证型] + 元认知审查 | 双重审查 | 事实门禁+推理方法论审查 | `a2a_collab` |
| [ContextManager] + [Decomposer] | 调度+压缩 | 长程任务中资源调配+上下文压缩 | `a2a_sync` |
| [Agent-综合型] + 校准 | 输出+校准 | 文档生成前置信度校准 | `a2a_handoff` |
| MetaLearner + MemoryKeeper | 学习+记忆 | 跨任务模式提取+知识持久化 | `a2a_sync` |
| [Sentinel] + 全Agent | 安全治理 | 沙箱逃逸检测+越界行为监控+联网行为审计+多Agent串联越狱检测 | MCP安全审查+`a2a_sync` |
| Worker(general) + Follower(搜索型) | 嵌套spawn汇聚 | L3+任务中Worker内部spawn 2-4个Follower，汇聚后返回≤2000 token给主Agent，5 Worker×4 Follower=20路有效并行 | `a2a_result` |

**嵌套spawn约束**：最多2层（主→Worker→Follower），不递归扩展。Worker必须用general类型。主Agent仍执行Step标注和审视链——Worker的spawn/Handoff/返回在主Agent的Step中完整标注。原有Agent生成、TAOR循环、交叉验证、安全审查规则全部不变。

**子Agent摘要返回**：每个子Agent用数万token探索，但仅返回浓缩摘要给主Agent——关键事实+来源编号+置信度+未解决问题，消除上下文污染。≤2000 token为全局上限（不变）。按Agent类型分配返回预算以提升并行数（不改变上限）：

| Agent类型 | 建议返回上限 | 理由 |
|----------|------------|------|
| 搜索型 | ≤800 token | 数据采集者，三元组{结论,来源,置信度}足够 |
| 核查型 | ≤1200 token | 需回溯细节，比搜索型稍多 |
| 验证型 | ≤1000 token | 检查结果格式化输出，不需大段原文 |
| 分析型 | ≤2000 token | 产出复杂结论，保持原始预算 |
| 综合型 | ≤2000 token | 产出复杂结论，保持原始预算 |

效果：混合spawn一批（3搜索+1核查+1分析）总返回从10000降至6200 token，同上下文容量可从5路提升至8路。

## 运行时专家切换（每次任务100%强制监控）

借鉴K3的运行时专家切换机制：

- Agent连续2轮产出被驳回→spawn替代Agent接管该子任务
- 搜索结果揭示新领域知识→动态插入对应领域的专家Agent
- 某Agent执行超时→标记"suspended"，spawn新Agent
- **强制执行**：无论任务复杂度L1-L4，均必须持续监控上述切换条件。简单任务的Agent数量可少（1-3个），但切换监控不可省略——若Agent被驳回仍必须spawn替代，不可跳过

## Agent能力进化

Agent动态生成流程、能力模板、配置维度、运行时专家切换、Agent能力进化及信任度信用网络详见 [k3-enhancement-modules.md](k3-enhancement-modules.md) 模块1和模块8。

> AI生成