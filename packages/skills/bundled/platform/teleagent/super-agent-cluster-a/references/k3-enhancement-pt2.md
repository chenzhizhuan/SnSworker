---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '2d0c0d44-1cb5-445a-b7b6-3c415e6efea5'
  PropagateID: '2d0c0d44-1cb5-445a-b7b6-3c415e6efea5'
  ReservedCode1: '78cd36a9-8bc8-4724-a8de-6284fc945029'
  ReservedCode2: '78cd36a9-8bc8-4724-a8de-6284fc945029'
---

# K3增强模块（补充）

> 从 k3-enhancement-modules.md 拆分。

## 模块10: 跨范式知识合成

将不同学科的根本范式深度融合，产生单范式无法企及的交叉学科洞见。

| 范式 | 核心问题 | 代表学科 |
|------|---------|---------|
| 实证范式 | 是什么？ | 物理学/经济学/统计学 |
| 规范式范式 | 应该是什么？ | 伦理学/法学/政策学 |
| 解释学范式 | 意味着什么？ | 历史学/人类学/文学 |
| 批判范式 | 为什么是这样？ | 社会学/哲学/政治学 |

合成路径：实证×规范、实证×解释、实证×批判、规范×解释、规范×批判、解释×批判——六路合成打破学科壁垒。L4跨学科任务必须完成至少3路合成路径。

---

## 模块11: 对抗性群体智慧

多个Agent从不同立场出发，通过多轮辩论涌现出单视角无法到达的最优解。

**对抗性辩论协议**：
1. 立场分化：Decomposer分配3-7个Agent实例，每个持有不同立场
2. 结构化辩论：多轮辩论（立场陈述→交叉质询→立场修正→共识探测）
3. 涌现收敛：所有Agent一致（强收敛）/ 分歧但知原因（弱收敛）/ 5轮上限元级裁决
4. 群体智慧结晶：各立场论证书面保留，共识区作为高置信结论，分歧区标注"未决问题"

与传统多模型共识的区别：传统共识追求"大家同意"，对抗性群体智慧保留"大家不同意及为什么"——分歧本身就是知识。

---

## 模块12: 认知边界+递归研究议程

**动态认知边界**——自动探测知识边界，明确区分「已知」「未知」和「不可知」，防止Agent在知识边界外进行幻觉性推断。

| 边界阶 | 定义 | 探测方法 | 输出标注 |
|--------|------|---------|---------|
| 已知区 | 有充足证据支撑的结论 | 证据数量≥3、来源独立性≥2维 | 正常输出 |
| 未知区 | 缺乏证据但理论上可获取 | 搜索后证据不足但存在可获取数据源 | 标注"当前证据不足" |
| 不可知区 | 理论上无法获取或验证 | 证据本质不可获取或逻辑上不可验证 | 标注"不可知晓" |

越界防护：Agent不得将"未知区"内容包装为"已知区"输出；不得对"不可知区"内容进行推测性输出。

**递归式研究议程**——Agent根据研究进展自主生成下一步研究问题，形成自驱动研究闭环：

```text
用户初始问题 → 执行研究 → 研究议程评估 → 议程生成器产出候选问题
  → 议程筛选 → 自主执行最高价值问题 → 循环回到「研究议程评估」
  → 收敛条件满足→输出最终报告
```

议程生成器从5维度产出候选问题：深化维度、广化维度、反转维度、时序维度、元维度。

收敛条件：连续2轮未生成高价值候选问题 / 预算耗尽 / 研究议程覆盖了根残差包全部要点 / 用户中断。

---

## 残差包格式规范

### 残差包字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| residual_id | string | 唯一标识，格式agent_{N}_to_agent_{N+k} |
| source_agent | string | 生成此残差包的Agent标识 |
| original_intent | string | 用户原始意图摘要，≤200字，全链路不变 |
| key_decisions | array | 关键决策列表，每项含agent/decision/rationale/confidence |
| open_questions | array | 尚未解决的悬置问题列表 |
| preserved_facts | array | 不可丢失的关键事实列表 |
| fidelity_score | float | 保真度评分0-1，低于0.7触发重建 |
| timestamp | string | ISO-8601格式时间戳 |
| hop_count | int | 已经过的Agent跳数，最大10 |

### 保真度维护规则

- 每经过一个Agent，残差包保真度必须≥0.85
- 保真度<0.7时触发残差重建——回溯至源Agent补充信息
- 残差包最大hop_count=10，超过则强制收敛
- 入口Agent生成的残差包为「根残差包」，全链路不可篡改
- Block级聚合后检查根残差包保真度，低于0.85触发补全

---

## 附录: LangGraph状态机与协议栈集成

### LangGraph状态机架构

CARS从"借鉴LangGraph"升级为显式状态机架构设计：

| 状态节点 | 职责 | 条件边路由 |
|---------|------|-----------|
| `intake` | 目标解析+记忆注入+复杂度评估+任务分解 | → `spawn`（L1轻量）/ → `spawn_deep`（L3/L4） |
| `spawn` | 动态生成Agent，分配子任务 | → `parallel_execute`（无依赖）/ → `serial_execute`（有依赖） |
| `execute` | Agent自主TAOR循环执行 | → `verify`（自验通过）/ → `retry`（偏差>20%） |
| `verify` | 交替四范式验证+DQG门禁 | → `crystallize`（全通过）/ → `backtrack`（部分未通过）/ → `degrade`（死锁3轮） |
| `crystallize` | 递归结晶+文档生成+可打开性校验 | → `reflux`（成功）/ → `regenerate`（格式校验失败） |
| `checkpoint` | 每3个子任务或50%预算自动创建 | 支持 `interrupt`（中断）+ `resume`（恢复） |

**Checkpoint恢复机制**：每个状态节点在完成关键操作后创建checkpoint（序列化完整状态），中断后可从最近checkpoint续接，避免从头执行。LangGraph的 `interrupt_before` / `interrupt_after` 支持人工审查介入点。

### MCP协议集成

Agent工具调用标准化为MCP tool call/response：

```json
{
  "mcp_tool_call": {
    "tool_id": "web_search",
    "params": {"query": "AI Agent市场2026", "max_results": 10},
    "caller_agent": "[Agent-搜索型]-3",
    "context_ref": "residual_001"
  },
  "mcp_tool_result": {
    "tool_id": "web_search",
    "status": "success",
    "result": [],
    "metadata": {"latency_ms": 1200, "source_count": 8}
  }
}
```

MCP协议为所有工具调用提供标准化接口，替代传统自定义API集成。Sentinel安全审查在MCP tool call前置执行。

### A2A协议与Handoff集成

Agent间信息传递兼容A2A标准的Handoff协议：

| 场景 | A2A消息类型 | 说明 |
|------|-----------|------|
| 任务交接 | `a2a_handoff` | 携带完整上下文+残差包+未办列表 |
| 能力发现 | `a2a_agent_card` | 标准化能力声明（角色/工具/置信度） |
| 结果返回 | `a2a_result` | 子Agent摘要返回（≤2000 token全局上限，按类型分配预算：搜索型≤800/核查型≤1200/验证型≤1000/分析型≤2000/综合型≤2000） |
| 协作请求 | `a2a_collab` | 请求其他Agent协助处理特定子问题 |
| 状态同步 | `a2a_sync` | 共享认知工作空间状态更新 |
| 嵌套spawn汇聚 | `a2a_result` | Worker(general)向主Agent返回汇聚摘要，内部Follower向Worker返回同样遵守类型预算 |

子Agent摘要返回机制定义在 [swarm-agents.md](swarm-agents.md) 协同矩阵章节，此处不再重复。