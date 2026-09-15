---
name: people-search
description: 基于互联网公开信息的多实体关联搜索与关系图谱生成技能。对用户提供的任意实体（人物、公司、组织、事件、项目等），通过多轮迭代搜索收集关联信息，构建实体关系网络，输出交互式HTML关系图和Mermaid静态图。当用户提到"查某人信息""关系图""关联搜索""信息关联""人肉搜索""背景调查""关系梳理"等关键词时触发。
name_cn: 人肉搜索
description_cn: 从互联网公开信息中搜索实体关联，生成可视化关系图谱
create_source: super-agent-skill-creator
---

# 人肉搜索 - 实体关联搜索与关系图谱

## 工作流程

### 1. 解析目标

从用户输入提取：
- **目标实体**：姓名、公司名、事件名等
- **已知线索**：用户提供的关键词、行业、地区等
- **搜索范围**：用户指定的侧重点（可选，默认全覆盖）

### 2. 多轮迭代搜索

按 `references/search_strategies.md` 中的策略执行搜索：

**第1轮（种子搜索）**：用3-5组关键词搜索目标实体，建立基本画像，识别直接关联方。

**第2轮（一度扩展）**：对第1轮发现的关键关联节点（3-5个最显著）分别搜索，发现间接关联。

**第3-10轮（深度挖掘）**：每轮选择信息增益最大的2-3个新节点继续搜索，直到无新关联发现或达到10轮上限。

搜索规则：
- 仅使用 `online_search` 工具搜索互联网公开信息
- 关键信息至少2个独立来源交叉验证
- 标注信息源可信度（A-E级，见 `references/search_strategies.md`）
- 矛盾信息取权威来源，矛盾处标注说明

### 3. 构建关系数据

将搜索结果整理为结构化JSON：

```json
{
  "nodes": [
    {"id": "唯一标识", "label": "显示名称", "type": "person|company|organization|event|project|location", "detail": "简介信息"}
  ],
  "edges": [
    {"source": "源节点id", "target": "目标节点id", "label": "关系类型"}
  ],
  "title": "关系图谱标题"
}
```

节点类型说明：
- `person` 人物（红色圆形）
- `company` 公司（蓝色方形）
- `organization` 组织/机构（绿色菱形）
- `event` 事件（橙色体育场形）
- `project` 项目（紫色子程序形）
- `location` 地点（青色圆形）

关系类型标注规范见 `references/search_strategies.md`。

### 4. 生成可视化

**交互式HTML关系图**：运行 `scripts/generate_graph_html.py`

```bash
python scripts/generate_graph_html.py <input.json> <output.html>
```

特性：D3.js力导向图、节点拖拽、点击高亮关联、搜索过滤、悬停提示

**Mermaid静态图**：运行 `scripts/generate_mermaid.py`

```bash
python scripts/generate_mermaid.py <input.json> [output.md]
```

两个文件均保存到工作目录，HTML可直接在浏览器打开。

### 5. 输出摘要

向用户呈现：
- 搜索摘要：搜索轮次、发现节点数、关系数
- 核心发现：最关键的3-5个关联发现
- 信息源声明：数据来源及可信度说明
- 文件路径：HTML和Mermaid文件位置

## 合规红线

- 仅搜索互联网公开信息，不获取任何非公开/付费/需登录数据
- 不搜索个人隐私敏感信息（身份证号、手机号、住址等）
- 不对未成年人进行搜索
- 搜索结果仅供用户参考，不作为法律证据
- 输出中始终附带"信息来源于互联网公开数据，仅供参考"声明
