---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: 'eeec8442-996b-42b1-9e2e-824d47537439'
  PropagateID: 'eeec8442-996b-42b1-9e2e-824d47537439'
  ReservedCode1: '640ed9cd-5412-4048-a739-5f4cd8b03c9d'
  ReservedCode2: '640ed9cd-5412-4048-a739-5f4cd8b03c9d'
---

# 双引擎使用指南

电信PPT大师 v7.2 起支持双引擎架构：JS引擎（pptxgenjs）与 Python引擎（SVG管道）。

---

## 引擎选择决策树

```
用户请求
│
├─ 包含"电信"/"运营"/"业务报告"/"经营分析"/"宣贯"？
│  → JS引擎 (pptxgenjs)  ← 默认，覆盖95%场景
│
├─ 包含"座谈会封面"/"杂志风格"/"Swiss Grid"/"高设计感"？
│  → Python引擎 (SVG管道)
│
├─ 要求"动画"/"过渡效果"/"语音旁白"/"视频"？
│  → Python引擎 (SVG管道)
│
├─ 要求"小红书尺寸"/"微信朋友圈"/"海报"等非16:9？
│  → Python引擎 (SVG管道)
│
├─ 提供已有.pptx模板，要求"填充内容"？
│  → Python引擎 (SVG管道) ── template-fill-pptx 工作流
│
├─ 提供Excel/数据表格为主要输入？
│  → JS引擎 (pptxgenjs) ── 数据智能层成熟
│
└─ 需要"快速出稿"（5页内/10分钟内）？
   → JS引擎 (pptxgenjs)
```

## 引擎对比速查

| 维度 | JS引擎 | Python引擎 |
|------|--------|-----------|
| **核心场景** | 日常业务PPT | 高端设计/特殊格式 |
| **速度** | ⭐⭐⭐⭐⭐ 1-3min | ⭐⭐ 10-20min |
| **内容组织** | ⭐⭐⭐⭐⭐ 19+6模式 | ⭐⭐ 无模式系统 |
| **场景预设** | ⭐⭐⭐⭐⭐ 12种 | ⭐ 无 |
| **设计精度** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **原生PPT深度** | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| **动画/旁白** | ⭐ 几乎不支持 | ⭐⭐⭐⭐ |
| **自进化** | ⭐⭐⭐⭐⭐ | ⭐ 无 |
| **电信适配** | ⭐⭐⭐⭐⭐ 深度定制 | ⭐⭐ 通用 |

## 切换示例

### JS引擎（默认，无需声明）

> 用户："帮我做一份存量固升行动的复盘PPT，用Excel数据"

→ 自动走JS引擎，数据智能层解析Excel → 19种模式匹配 → 图形布局 → pptxgenjs生成

### Python引擎（需明确触发）

> 用户："帮我做座谈会封面页，要有杂志感，带过渡动画"

→ 自动切换到Python引擎，project_manager初始化 → 策略师规划 → Executor手写SVG → SVG→PPTX编译

### 混合使用（封面Python + 正文JS）

> 用户："封面用高端设计，正文用电信标准风格"

→ 封面走Python引擎，正文走JS引擎，最终合并

## 引擎配置

### JS引擎
- 无需额外配置
- 内置 pp txgenjs 运行时
- 输出到用户工作空间

### Python引擎
- 需要 Python 3.10+ 安装
- 依赖：`pip install -r python-pipeline/source/skills/ppt-master/requirements.txt`
- 源码位于 `.temp/ppt-master-source/`
- 详见 `python-pipeline/README.md`