---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '15f5500e-1e8b-4ee3-97cf-51d920e72df8'
  PropagateID: '15f5500e-1e8b-4ee3-97cf-51d920e72df8'
  ReservedCode1: 'db5b9baf-4d9f-46ef-9ef8-497618a11517'
  ReservedCode2: 'db5b9baf-4d9f-46ef-9ef8-497618a11517'
---

# 通信协议规范

<!-- INDEX: 消息通用结构,L41 | 消息类型详解,L64 | docx_format_verified,L516 | docx_open_verified,L528 -->

## Table of Contents

- 消息通用结构
- task_assign（任务分配）
- research_result（研究结果）
- search_orchestrate（搜索编排）
- audit_result（审计结果）
- coord_directive（协调指令）
- debias_result（去偏结果）
- calibrate_result（校准结果）
- exec_result（执行结果）
- analysis_result（分析结果）
- factcheck_result（事实核查结果）
- critic_result（对抗验证结果）
- memory_baseline（记忆基线）
- security_check（安全检查）
- review_result（审查结果）
- degrade_notice（降级通知）
- search_cache（搜索缓存）
- context_compress（上下文压缩）
- meta_feedback（元反馈）
- meta_cognition（元认知）
- final_output（最终输出）
- docx_format_verified 与 docx_open_verified 字段说明

## 消息通用结构

```json
{
  "msg_id": "msg_YYYYMMDDHHMMSS_NNN",
  "msg_type": "task_assign|research_result|search_orchestrate|exec_result|analysis_result|factcheck_result|critic_result|debias_result|calibrate_result|memory_baseline|security_check|review_result|audit_result|coord_directive|degrade_notice|search_cache|context_compress|meta_feedback|meta_cognition|final_output",
  "from_agent": "Decomposer(主Agent)|[Agent-搜索型]|[Agent-分析型]|[Agent-编码型]|[Agent-核查型]|[Agent-验证型]|[Agent-综合型]|[Agent-运维型]|[Agent-元认知](别名MetaCognitor)|Sentinel|ContextManager|MemoryKeeper|MetaLearner",
  "to_agent": "Decomposer(主Agent)|[Agent-搜索型]|[Agent-分析型]|[Agent-编码型]|[Agent-核查型]|[Agent-验证型]|[Agent-综合型]|[Agent-运维型]|[Agent-元认知](别名MetaCognitor)|Sentinel|ContextManager|MemoryKeeper|MetaLearner|User",
  "timestamp": "2026-01-01T00:00:00Z",
  "task_id": "task_YYYYMMDDHHMMSS",
  "subtask_id": "ST1|ST2|...",
  "iteration": 0,
  "payload": {},
  "context_ref": ["ctx_001", "ctx_002"],
  "docx_format_verified": null,
  "docx_open_verified": null
}
```

> **A2A协议与20种消息类型的关系**：本文档定义 Agent 间通信的 **20 种结构化消息类型**（`msg_type`，见下表），是实际传递数据载荷的载体。`references/k3-enhancement-modules.md §架构总纲`（L80 A2A协议列表项） 与 `references/swarm-agents-pt2.md`（Agent全生命周期标注与协同） 中出现的 `a2a_handoff` / `a2a_collab` / `a2a_sync` / `a2a_result` / `a2a_agent_card` 属于 **A2A（Agent-to-Agent，Google 2025）标准协议层的场景标签**，用于标注"当前交互属于哪种协作场景"；实际消息内容仍通过本文档的 20 种 `msg_type` 之一承载。二者是"场景标签"与"消息载体"的分层关系，不冲突、不重复定义。

> **docx验证字段位置说明**：`docx_format_verified` 和 `docx_open_verified` 在通用结构中声明为顶层字段（默认null），在 `final_output` 消息的payload中携带完整校验结果。通用结构的顶层字段作为占位符（null表示未校验），实际校验值仅通过payload传递，不构成双重赋值。

## 消息类型详解

### task_assign

```json
{
  "msg_type": "task_assign",
  "payload": {
    "subtask_desc": "子任务描述",
    "assigned_agent_type": "搜索型|分析型|编码型|核查型|验证型|综合型|元认知",
    "agent_config": {
      "domain_knowledge": ["领域知识要点"],
      "tool_set": ["python", "search", "chart"],
      "validation_threshold": 0.85,
      "search_budget": {"max_rounds": 3, "max_width": 8}
    },
    "dependencies": ["ST1"],
    "budget": {"max_search_rounds": 3, "max_code_retries": 3, "time_limit_sec": 30},
    "expected_output": "research_result|exec_result|analysis_result|factcheck_result|critic_result"
  }
}
```

### research_result

```json
{
  "msg_type": "research_result",
  "payload": {
    "findings": [
      {
        "claim": "结论文本",
        "sources": [
          {"title": "来源标题", "url": "URL", "accessed": "访问日期", "reliability": "high|medium|low"}
        ],
        "verification": "strong|weak|unverified",
        "confidence": 0.85,
        "modality": "text|multimodal_pdf|multimodal_image|multimodal_chart",
        "query_intent": "factual|analytical|navigational|transactional"
      }
    ],
    "knowledge_entries": [
      {"source": "来源", "content": "内容摘要", "confidence": 0.9}
    ],
    "contradictions_found": ["发现的矛盾列表"]
  }
}
```

### search_orchestrate

```json
{
  "msg_type": "search_orchestrate",
  "payload": {
    "directed_queries": [
      {"query": "调整后的搜索词", "reason": "调整原因", "priority": "high|medium|low"}
    ],
    "quality_assessment": {
      "coverage_score": 0.75,
      "redundancy_score": 0.3,
      "gap_areas": ["信息缺口1", "信息缺口2"]
    },
    "strategy_adjustment": "broaden|deepen|pivot|stop",
    "target_agent_id": "[Agent-搜索型]-1",
    "adversarial_env_assessment": {
      "monopoly_risk": "low|medium|high",
      "seo_manipulation_risk": "low|medium|high",
      "temporal_contamination_risk": "low|medium|high",
      "censorship_risk": "low|medium|high",
      "recommended_strategy": "broaden_channels|switch_non_seo|time_window_filter|cross_platform"
    }
  }
}
```

### audit_result

```json
{
  "msg_type": "audit_result",
  "payload": {
    "audit_trail": [
      {"subtask": "ST2", "agent_type": "搜索型", "action": "搜索执行", "timestamp": "2026-01-01T00:00:00Z", "issues": []}
    ],
    "evidence_decay": [
      {"evidence_id": "E001", "original_score": 0.85, "decay_factor": 0.7, "adjusted_score": 0.60, "reason": "数据超2年且领域变化快"}
    ],
    "consistency_check": {"topology_subtasks": 15, "inconsistencies": [], "status": "pass|warning|fail"},
    "compliance_verdict": "pass|conditional|fail",
    "blocking_issues": []
  }
}
```

### coord_directive

```json
{
  "msg_type": "coord_directive",
  "payload": {
    "directive_type": "conflict_resolve|deadlock_break|resource_rebalance|health_alert",
    "target_agents": ["ST1-Agent", "ST3-Agent"],
    "action": "具体协调动作描述",
    "reason": "协调原因",
    "priority": "high|medium|low",
    "workflow_health": {"active_agents": 5, "blocked_agents": 1, "timeout_risk": "low|medium|high"}
  }
}
```

### debias_result

```json
{
  "msg_type": "debias_result",
  "payload": {
    "biases_detected": [
      {"type": "confirmation_bias", "severity": "high", "evidence": "反面证据占比仅8%"}
    ],
    "corrections_applied": [
      {"bias_type": "confirmation_bias", "method": "强制补充等量反面证据", "impact": "置信度从0.88降至0.82"}
    ],
    "remaining_risks": ["幸存者偏差无法完全消除"],
    "status": "pass|warning|fail"
  }
}
```

### calibrate_result

```json
{
  "msg_type": "calibrate_result",
  "payload": {
    "original_confidence": 0.88,
    "calibrated_confidence": 0.84,
    "calibration_coefficient": 0.95,
    "claim_dependency_issues": [
      {"claim_id": "C3", "issue": "根节点失效将影响4个下游结论", "risk": "high"}
    ],
    "formula_validation": "pass",
    "status": "pass|calibration_warning|fail"
  }
}
```

### exec_result

```json
{
  "msg_type": "exec_result",
  "payload": {
    "code_executed": "执行的代码摘要",
    "stdout": "标准输出",
    "stderr": "标准错误（如有）",
    "return_value": "返回值",
    "artifacts": [{"type": "chart|data|file", "path": "文件路径", "description": "说明"}],
    "retries": 0,
    "status": "success|failed",
    "security_check_passed": true
  }
}
```

### analysis_result

```json
{
  "msg_type": "analysis_result",
  "payload": {
    "model_type": "quantification|sensitivity|scenario|statistical",
    "assumptions": ["假设列表"],
    "results": {
      "base_case": "基准结果",
      "sensitivity": {"关键假设变动": "结论方向是否反转"},
      "scenarios": {
        "base": {"value": "值", "probability": "50%-60%"},
        "optimistic": {"value": "值", "probability": "15%-25%"},
        "pessimistic": {"value": "值", "probability": "15%-25%"},
        "black_swan": {"value": "值", "probability": "5%-10%"}
      }
    },
    "confidence_interval": "置信区间",
    "data_quality_notes": "数据质量备注"
  }
}
```

### factcheck_result

```json
{
  "msg_type": "factcheck_result",
  "payload": {
    "target_claims": [
      {
        "claim": "断言文本",
        "numbers_traced": [
          {"number": "73.5%", "source_match": "来源原文", "status": "matched|mismatched|not_found"}
        ],
        "source_independence": "independent|semi_independent|non_independent",
        "timeliness_score": 0.85,
        "evidence_chain_complete": true,
        "verification_level": "A|B|C|D",
        "falsifiability": {"testable": true, "status": "falsifiable_unfalsified|falsified|unfalsifiable"},
        "simpson_paradox": {"overall_effect_direction": "positive", "subgroup_directions": {}, "paradox_detected": false},
        "ecological_fallacy": {"analysis_unit": "region", "conclusion_target": "individual", "fallacy_risk": false},
        "causal_sufficiency": {"all_confounders_measured": false, "unmeasured_confounders": [], "robustness": "sufficient"}
      }
    ],
    "overall_factuality": 0.88
  }
}
```

### critic_result

```json
{
  "msg_type": "critic_result",
  "payload": {
    "red_blue_result": {
      "red_argument": "红方论证",
      "blue_counter": "蓝方反驳",
      "verdict": "pass|fail",
      "fatal_refutation_found": false
    },
    "convergence_check": {
      "keyword_overlap_rate": 0.65,
      "source_overlap_rate": 0.45,
      "conclusion_unanimity": false,
      "independent_source_count": 4,
      "status": "pass|warning|fail"
    },
    "logical_fallacies": [],
    "self_red_team": {"attack_vectors_tried": 5, "attacks_succeeded": 0, "coefficient": 1.0}
  }
}
```

### memory_baseline

```json
{
  "msg_type": "memory_baseline",
  "payload": {
    "baseline_entries": [
      {"source": "MEMORY.md", "content": "相关记忆摘要", "relevance": 0.85, "date": "2026-07-30"}
    ],
    "search_mode": "incremental|full",
    "conflict_items": []
  }
}
```

### security_check

```json
{
  "msg_type": "security_check",
  "payload": {
    "check_type": "code|api|input|output",
    "risk_level": "high|medium|low",
    "passed": true,
    "issues": [],
    "action": "allow|warn|block"
  }
}
```

### review_result

```json
{
  "msg_type": "review_result",
  "payload": {
    "target_subtask": "ST1",
    "target_iteration": 0,
    "dimensions": {
      "factuality": {"score": 0.9, "passed": true, "notes": ""},
      "logic": {"score": 0.85, "passed": true, "notes": ""},
      "source_reliability": {"score": 0.8, "passed": true, "notes": ""},
      "completeness": {"score": 0.9, "passed": true, "notes": ""},
      "hallucination": {"score": 1.0, "passed": true, "notes": ""}
    },
    "five_fold_verification": {
      "fact_check": "pass",
      "attack_check": "pass",
      "debias_check": "pass",
      "audit_check": "pass",
      "calibration_check": "pass"
    },
    "overall_confidence": 0.87,
    "dqg_score": 0.98,
    "decision": "pass|reject",
    "rejection_reasons": [],
    "guidance": "下轮纠错指导（驳回时）"
  }
}
```

### degrade_notice

```json
{
  "msg_type": "degrade_notice",
  "payload": {
    "level": "L1|L2|L3",
    "affected_subtasks": ["ST1", "ST3"],
    "affected_agent_types": ["搜索型", "分析型"],
    "reason": "降级原因",
    "action": "retry_alternative|partial_output|single_agent_fallback",
    "preserved_outputs": ["已保留的子任务产出"]
  }
}
```

### search_cache

```json
{
  "msg_type": "search_cache",
  "payload": {
    "cache_key": "url_or_keyword+intent_hash",
    "source_subtask": "ST1",
    "requesting_subtask": "ST3",
    "hit": true,
    "cached_result_ref": "ctx_001",
    "cache_age_minutes": 45,
    "ttl_minutes": 120
  }
}
```

### context_compress

```json
{
  "msg_type": "context_compress",
  "payload": {
    "trigger": "budget_threshold|density_low|manual",
    "current_usage_pct": 82,
    "target_usage_pct": 65,
    "compression_strategy": "conclusion_first|source_index|process_delete|merge_redundant|chart_describe",
    "preserved_keys": ["结论", "关键数字", "来源编号"],
    "compressed_items": [{"original_ref": "ctx_001", "compressed_to": "摘要文本", "compression_ratio": 0.3}],
    "integrity_check": "pass|fail"
  }
}
```

### meta_feedback

```json
{
  "msg_type": "meta_feedback",
  "payload": {
    "task_pattern": "market_research",
    "complexity_prediction": {"level": "L3", "estimated_time_min": 12, "search_rounds": 8},
    "agent_performance_scores": [
      {"agent_type": "搜索型", "score": 0.85, "trend": "stable"},
      {"agent_type": "分析型", "score": 0.72, "trend": "declining"}
    ],
    "strategy_suggestions": [
      {"type": "search_optimization", "suggestion": "优先使用'销量数据'关键词，历史命中率85%", "confidence": 0.8}
    ]
  }
}
```

### meta_cognition

```json
{
  "msg_type": "meta_cognition",
  "from_agent": "[Agent-元认知](别名MetaCognitor)",
  "payload": {
    "cognition_level": "L1|L2|L3",
    "review_scope": "reasoning_process|review_process",
    "target_agent_types": ["分析型", "验证型"],
    "target_subtasks": ["ST3", "ST5"],
    "findings": [
      {
        "dimension": "implicit_assumption|path_dependency|information_bias|framework_limitation|confidence_calibration",
        "description": "发现的具体元认知问题",
        "severity": "critical|major|minor",
        "affected_conclusions": ["受影响的结论编号或描述"],
        "recommendation": "可执行改进建议"
      }
    ],
    "cognitive_boundary": {
      "known_zone": ["有充足证据的结论"],
      "unknown_zone": ["证据不足但可获取的结论"],
      "unknowable_zone": ["理论上不可验证的结论"],
      "boundary_violations": ["跨边界使用的结论列表"]
    },
    "confidence_calibration": {
      "agent_type": "分析型",
      "self_reported_confidence": 0.92,
      "actual_accuracy": 0.75,
      "calibration_status": "overconfident",
      "adjustment_factor": 0.81
    },
    "research_agenda": [
      {"dimension": "deepening|broadening|reversal|temporal|meta", "question": "自驱生成的研究问题", "priority": 0.85}
    ]
  }
}
```

### final_output

```json
{
  "msg_type": "final_output",
  "payload": {
    "output_format": "docx|dialog",
    "content": "输出内容或文件路径",
    "confidence_level": "high|medium|low|very_low",
    "confidence_score": 0.87,
    "verification_summary": {
      "fact_check": "pass",
      "attack_check": "pass",
      "debias_check": "pass",
      "audit_check": "pass",
      "calibration_check": "pass",
      "reproducibility_check": "pass|not_applicable"
    },
    "degraded_items": [],
    "unverified_items": [],
    "sources": [
      {"id": 1, "title": "来源标题", "url": "URL", "accessed": "访问日期", "reliability": "A|B|C|D", "modality": "text|multimodal"}
    ],
    "docx_format_verified": {
      "status": "pass|fail|not_applicable",
      "format_source": "generate_docx.py",
      "errors": [],
      "timestamp": "2026-01-01T00:00:00Z"
    },
    "docx_open_verified": {
      "status": "pass|fail|not_applicable",
      "open_method": "zipfile",
      "paragraph_count": 0,
      "structure_intact": true,
      "content_readable": true,
      "errors": []
    }
  }
}
```

## docx_format_verified 字段说明

> **用户选择获取方式**：用户是否选择生成docx的决策，必须直接通过question工具以交互式问答形式获取，⛔禁止在询问前以正文形式输出分析结论（仅Step标注可正常展示），禁止以普通文本形式提问（规则14+规则15）。`output_format` 的值（`docx`或`dialog`）由此交互结果决定。

- 用户选择生成docx时，`output_format` 为 `docx`，`docx_format_verified` 为**必填字段**，缺少该字段的 final_output 消息将被拒绝传递给用户
- 用户选择不生成docx时，`output_format` 为 `dialog`，`docx_format_verified` 为 null，不适用该字段校验
- `status=pass`：文档通过 generate_docx.py 生成且格式自校验全部通过
- `status=fail`：文档格式校验失败，此消息应被拦截，[Agent-综合型]必须重新生成
- `format_source` 必须为 `generate_docx.py`，任何其他值均视为格式违规
- 禁止调用Word文档助手（docx skill / doc-coauthoring / 任何Word文档处理skill）
- 此字段构成通信协议层条件性验证——仅在用户选择生成docx时生效

## docx_open_verified 字段说明

- 用户选择生成docx时，`docx_open_verified` 为**必填字段**，与 `docx_format_verified` 共同构成双重验证
- 用户选择不生成docx时，`docx_open_verified` 为 null，不适用该字段校验
- `status=pass`：zipfile成功打开生成的docx文件，文档结构完整、含document.xml/styles.xml、XML标签闭合
- `status=fail`：文档无法打开或结构损坏，此消息应被拦截，[Agent-综合型]必须重新生成
- 用户选择生成docx时，必须同时通过docx_format_verified和docx_open_verified双重验证