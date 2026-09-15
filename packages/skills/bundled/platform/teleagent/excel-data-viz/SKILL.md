---
name: excel-data-viz
description: >-
  Upload one or more Excel/CSV files to automatically analyze key data points,
  extract insights, and generate visualizations (line charts, bar charts, pie charts,
  donut charts, heatmaps, scatter plots, histograms, box plots, area charts).
  Use when user asks to "visualize Excel data", "analyze spreadsheet", "chart data",
  "数据可视化", "分析Excel", "画图表", "生成图表", "可视化数据", or uploads Excel/CSV
  files and wants visual analysis.
name_cn: Excel数据可视化
description_cn: 上传Excel/CSV文件，自动分析关键数据并生成折线图、饼图、柱状图、环形图、热力图等可视化图表
create_source: super-agent-skill-creator
---

# Excel 数据可视化

## 概述

对上传的 Excel/CSV 文件进行智能数据分析和可视化，自动识别数据特征、提炼关键指标，并选择最合适的图表类型呈现。

## 工作流程

1. **读取文件**：接收用户上传的一个或多个 Excel（.xlsx/.xls）或 CSV 文件
2. **数据摘要**：运行 `analyze_visualize.py --no-auto` 获取 JSON 摘要，了解列类型、统计信息和相关性
3. **智能选图**：根据数据特征自动推荐图表类型和列组合
4. **生成图表**：运行 `analyze_visualize.py` 生成可视化图片
5. **呈现结果**：向用户展示图片和数据洞察

## 核心脚本

### scripts/analyze_visualize.py

功能完整的命令行工具，支持：

```bash
# 自动分析 + 全部图表
python scripts/analyze_visualize.py <文件路径> --output-dir <输出目录>

# 仅输出数据摘要（不生成图表）
python scripts/analyze_visualize.py <文件路径> --no-auto --output-dir <输出目录>

# 指定图表类型
python scripts/analyze_visualize.py <文件路径> --charts bar,pie,heatmap

# 指定工作表
python scripts/analyze_visualize.py <文件路径> --sheet "Sheet2"

# 高清输出
python scripts/analyze_visualize.py <文件路径> --dpi 300
```

### 支持的图表类型

| 类型 | 适用场景 | 自动触发条件 |
|------|----------|-------------|
| line（折线图） | 时间趋势 | 日期列 + 数值列 |
| bar（柱状图） | 分类对比 | 分类列 + 数值列 |
| pie（饼图） | 分类占比 | 分类列（2-8个类别） |
| donut（环形图） | 分类占比 | 分类列（2-8个类别） |
| heatmap（热力图） | 相关性矩阵 | ≥2个数值列 |
| scatter（散点图） | 数值关系 | ≥2个数值列 |
| histogram（直方图） | 数值分布 | 单个数值列 |
| box（箱线图） | 分组分布 | 分类列 + 数值列 |
| area（面积图） | 趋势面积 | 日期列 + 数值列 |

### 输出文件

脚本在 `--output-dir` 目录下生成：

- `data_summary.json`：数据摘要（列类型、统计信息、相关系数）
- `viz_result.json`：生成结果汇总（图表路径列表）
- `*.png`：各图表图片文件

### 关键参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--output-dir` | `./viz_output` | 图片输出目录 |
| `--sheet` | 第一个工作表 | 指定工作表名 |
| `--charts` | 全部推荐 | 指定图表类型（逗号分隔） |
| `--max-categories` | 10 | 分类列最大类别数 |
| `--dpi` | 150 | 图片分辨率 |
| `--cmap` | YlOrRd | 热力图色系 |
| `--no-auto` | false | 仅输出摘要不画图 |

## 多文件处理

对多个 Excel 文件逐一运行脚本，将各文件输出到不同子目录：

```bash
python scripts/analyze_visualize.py file1.xlsx --output-dir output/file1
python scripts/analyze_visualize.py file2.xlsx --output-dir output/file2
```

## 智能体使用指南

1. 用户上传 Excel/CSV 文件后，先运行 `--no-auto` 获取摘要
2. 根据摘要向用户简要说明数据特征（行数、列数、关键指标）
3. 运行完整分析生成图表
4. 向用户展示图表图片，并提供数据洞察总结
5. 如用户需要特定图表，用 `--charts` 参数指定
6. 如 Excel 有多个工作表，用 `--sheet` 参数切换
