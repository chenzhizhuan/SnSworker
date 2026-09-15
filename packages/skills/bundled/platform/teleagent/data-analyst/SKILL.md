---
name: data-analyst
description: "数据分析师技能：对 Excel/CSV 表格数据进行全面的统计分析、数据可视化和趋势预测。当用户提到「数据分析」「统计」「数据洞察」「趋势分析」「相关性分析」「数据可视化」「看数据」「分析一下数据」等关键词，或要求对表格数据进行统计、画图、预测时触发。支持：描述性统计（均值、中位数、分布、缺失值等）、7种可视化图表（直方图、柱状图、折线图、散点图、箱线图、热力图、饼图）、时间序列趋势分析与简单预测、多变量相关性分析（Pearson/Spearman/Kendall）。输出形式为文字摘要 + 静态图表图片。"
name_cn: 数据分析师
description_cn: "对 Excel/CSV 数据进行统计分析、可视化和趋势预测，输出文字摘要与图表"
create_source: super-agent-skill-creator
---

# 数据分析师

基于 Python (pandas + matplotlib + numpy) 的本地数据分析工具集，直接在本地处理数据，无需上传。

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

## 分析建议

- 首次拿到数据，先用 `descriptive_stats.py` 获取全局概览
- 根据概览中的分布特征和缺失值情况，选择后续分析方法
- 分类变量用柱状图/饼图，数值变量用直方图/箱线图，两变量关系用散点图/热力图
- 时间序列数据优先用趋势分析，关注移动平均和环比变化
- 相关性分析用于探索多变量间的线性关系，注意相关不等于因果

## 依赖

运行脚本需要：`pandas`, `numpy`, `matplotlib`, `openpyxl`。如缺失，执行 `pip install pandas numpy matplotlib openpyxl`。

## 注意事项

- 所有脚本通过 PowerShell 的 `python` 命令执行，输出前设置 `$env:PYTHONIOENCODING = 'utf-8'`
- 输出图片保存到工作目录的 `.temp/` 子目录或用户指定路径
- 脚本输出为 JSON 格式，需用自然语言向用户解读关键结论
