---
name: 数据分析师
description: "数据分析统一技能（合并原「数据分析师」「Excel数据可视化」「Excel关联性分析」）：对 Excel/CSV 表格数据进行统计分析、数据可视化、趋势预测与数据字典生成。当用户提到「数据分析」「统计」「数据洞察」「趋势分析」「相关性分析」「关联度分析」「数据可视化」「数据字典」「看数据」「分析一下数据」「画图表」「生成图表」，或上传 Excel/CSV 要求可视化分析时触发。支持：描述性统计、智能选图一键可视化（9种图表含环形/面积）、7种基础图表、时间序列趋势预测、多变量相关性分析（Pearson/Spearman/Kendall）、数据字典生成（表头提取+枚举统计+字段分类+关联度判断+网页可视化）。输出文字摘要 + 静态图表 + 数据字典。"
name_cn: 数据分析师
description_cn: "对 Excel/CSV 数据进行统计分析、智能可视化、趋势预测、相关性分析与数据字典生成（三技能合一），输出文字摘要与图表"
create_source: super-agent-skill-creator
metadata:
  tabtin:
    category: data
---

# 数据分析师（统一版）

基于 Python (pandas + matplotlib + numpy) 的本地数据分析工具集，直接在本地处理数据，无需上传。2026-10-19 合并「Excel数据可视化」与「Excel关联性分析」两技能，能力全部并入。

## 工作流

收到数据分析请求后：

1. **确认输入**：定位用户的数据文件（Excel/CSV），识别列名和数据类型
2. **确认分析方向**：根据用户需求或数据特征，选择合适的分析方法
3. **执行分析**：调用对应脚本，输出 JSON 统计结果 + PNG 图表
4. **解读结果**：用自然语言向用户解读关键发现和业务含义

## 核心能力

### 1. 描述性统计 (`scripts/descriptive_stats.py`)

输出关键统计指标：count、mean、std、min、Q1、median、Q3、max、IQR、偏度、峰度、缺失值数量及占比。同时输出数据概览（行数、列数、重复行、数值列/分类列）。

```bash
python scripts/descriptive_stats.py <input.csv> [--columns col1 col2] [--output result.json] [--encoding utf-8]
```

### 2. 数据可视化 (`scripts/visualize.py`)

支持7种图表类型：

| 类型 | 参数 `--type` | 必要参数 |
|------|---------------|----------|
| 直方图 | `histogram` | `--x 列名` |
| 柱状图 | `bar` | `--x 列名` |
| 折线图 | `line` | `--x 列名 --y 列名` |
| 散点图 | `scatter` | `--x 列名 --y 列名` |
| 箱线图 | `boxplot` | `--columns 列1 列2 ...` |
| 热力图 | `heatmap` | `--columns 列1 列2 ...` (可选) |
| 饼图 | `pie` | `--x 列名` |

```bash
python scripts/visualize.py <input.csv> --type histogram --x sales --output histogram.png
python scripts/visualize.py <input.csv> --type scatter --x col_a --y col_b --trend-line
python scripts/visualize.py <input.csv> --type heatmap --columns col1 col2 col3
python scripts/visualize.py <input.csv> --type bar --x category --top-n 10
```

所有图表自动适配中文字体，输出 150dpi PNG。

### 3. 趋势预测 (`scripts/trend_analysis.py`)

对时间序列数据执行：线性趋势拟合、7日/30日移动平均、日环比变化分析、未来N期线性预测。输出趋势图（含移动平均线和预测区间）+ 环比变化柱状图。

```bash
python scripts/trend_analysis.py <input.csv> --date date_col --value value_col [--periods 5] [--output-dir .]
```

输出 JSON 包含：趋势方向、每日斜率、总增长率、CAGR、均值/标准差、预测值。

### 4. 相关性分析 (`scripts/correlation.py`)

计算 Pearson/Spearman/Kendall 相关系数矩阵，识别强相关变量对（|r| >= 0.5），自动绘制热力图和强相关对的散点图（含趋势线）。

```bash
python scripts/correlation.py <input.csv> [--columns col1 col2] [--method pearson] [--output-dir .]
```

输出 JSON 包含：完整相关系数矩阵、强相关列表（变量对、系数、强度判定）、热力图路径、散点图路径。

### 5. 智能选图一键可视化 (`scripts/analyze_visualize.py`)

上传 Excel/CSV 后自动分析数据特征、提炼关键指标并推荐图表，一键生成全套可视化（原「Excel数据可视化」并入）：

```bash
# 自动分析 + 全部图表
python scripts/analyze_visualize.py <文件路径> --output-dir <输出目录>
# 仅数据摘要不生图
python scripts/analyze_visualize.py <文件路径> --no-auto --output-dir <输出目录>
# 指定图表类型 / 工作表 / 高清
python scripts/analyze_visualize.py <文件路径> --charts bar,pie,heatmap
python scripts/analyze_visualize.py <文件路径> --sheet "Sheet2"
python scripts/analyze_visualize.py <文件路径> --dpi 300
```

图表类型：line、bar、pie、donut（环形）、heatmap、scatter、histogram、boxplot、area，按数据特征自动触发（日期列+数值列→折线；分类列+数值列→柱状等）。支持 .xlsx/.xls/.csv 多文件。

### 6. 数据字典与字段关联度分析 (`scripts/excel_visualization_tool_with_summary.py`)

生成结构化数据字典（表头提取、类别枚举统计、字段说明、字段分类、关联度判断）并提供 Flask 网页可视化（原「Excel关联性分析」并入）：

```bash
python scripts/excel_visualization_tool_with_summary.py <数据文件> [--dict-out 数据字典.xlsx] [--serve]
```

适用场景：用户说「生成数据字典」「字段关联度分析」「字段可视化」「分析关联度」，或需要全表字段清单与枚举分布时。轻量场景（只算相关系数矩阵）走第 4 节 correlation.py，不要动用此重工具。

## 分析建议

- 首次拿到数据，先用 `descriptive_stats.py` 获取全局概览
- 根据概览中的分布特征和缺失值情况，选择后续分析方法
- 分类变量用柱状图/饼图，数值变量用直方图/箱线图，两变量关系用散点图/热力图
- 时间序列数据优先用趋势分析，关注移动平均和环比变化
- 相关性分析用于探索多变量间的线性关系，注意相关不等于因果
- 拿不准图表类型时，优先用 analyze_visualize.py 的智能选图；明确指定某种基础图时用 visualize.py
- 需要全表字段清单/数据字典时用 excel_visualization_tool_with_summary.py

## 依赖

运行脚本需要：`pandas`, `numpy`, `matplotlib`, `openpyxl`。如缺失，执行 `pip install pandas numpy matplotlib openpyxl`。

## 注意事项

- 所有脚本通过 PowerShell 的 `python` 命令执行，输出前设置 `$env:PYTHONIOENCODING = 'utf-8'`
- 输出图片保存到工作目录的 `.temp/` 子目录或用户指定路径
- 脚本输出为 JSON 格式，需用自然语言向用户解读关键结论

## 历史来源

本技能为三合一统一版（2026-10-19）：
- `data-analyst`（数据分析师）→ 主体：统计/可视化/趋势/相关四大基础脚本
- `excel-data-viz`（Excel数据可视化）→ analyze_visualize.py 智能选图一键可视化
- `excel-correlation-analysis`（Excel关联性分析）→ excel_visualization_tool_with_summary.py 数据字典+关联度+Flask 可视化
原两个技能目录已移除，触发词与能力全部并入本技能。
