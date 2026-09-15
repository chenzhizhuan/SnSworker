# 输出模板与 Excel 生成脚本

> **核心变化**：新增"AI 使用信号""当前 API 供应商""Token 替换理由"列，移除"规模线索"列（对 Token 销售价值低），话术全部改为 API 替换视角。

## Excel 输出结构

### Sheet 1：目标客户清单（主表）

| 列 | 字段名 | 类型 | 说明 |
|----|--------|------|------|
| A | 序号 | int | 1-100 |
| B | 企业名称 | str | 工商注册全称 |
| C | 画像类别 | str | A/B/C/D/E/F/G + 画像名 |
| D | 所属行业 | str | 制造业/外贸/软件/教育/电商等 |
| E | AI使用信号 | str | 招聘/产品/API/融资/工具/案例（具体描述） |
| F | 当前API供应商 | str | OpenAI/文心/通义/DeepSeek/智谱/待查 |
| G | Token替换理由 | str | 降本/统一管理/稳定性/合规 |
| H | 优先级 | str | P0/P1/P2 |
| I | 搜索来源 | str | 招聘网站/新闻/天眼查/企查查等 |
| J | 建议切入话术 | str | API 替换视角的一句话开场白 |

### Sheet 2：统计汇总

| 统计维度 | 数量 | 占比 |
|---------|------|------|
| P0 高优先级 | XX | XX% |
| P1 中优先级 | XX | XX% |
| P2 低优先级 | XX | XX% |
| A类 AI开发商 | XX | XX% |
| B类 自建AI应用 | XX | XX% |
| C类 已有AI的制造 | XX | XX% |
| D类 已用AI的跨境 | XX | XX% |
| E类 已用AI编码的软件 | XX | XX% |
| F类 已部署AI实训的院校 | XX | XX% |
| G类 已用AI的内容客服 | XX | XX% |
| **总计** | **100** | **100%** |
| **排除企业数** | XX | - |

### Sheet 3：搜索记录

| 搜索序号 | 阶段 | 关键词 | 结果数量 | 说明 |
|---------|------|--------|---------|------|

### Sheet 4：排除清单（新增）

| 序号 | 企业名称 | 排除原因 | 搜索来源 |
|------|---------|---------|---------|
| 1 | XX军工科技 | 涉密/军工 | 天眼查 |
| 2 | XX银行核心系统 | 金融核心系统 | 招标网 |

---

## Python Excel 生成脚本

```python
#!/usr/bin/env python3
"""
天翼云 Token 目标客户清单 Excel 生成脚本（v2 - API 替换视角）
输入：客户数据列表（JSON格式）
输出：Excel文件（4个Sheet：客户清单、统计汇总、搜索记录、排除清单）
"""

import json
import sys
from datetime import datetime

try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    from openpyxl.utils import get_column_letter
except ImportError:
    print("需要安装 openpyxl: pip install openpyxl")
    sys.exit(1)


def generate_excel(customers, city_name, search_records=None, excluded=None):
    """
    生成目标客户清单 Excel 文件

    Args:
        customers: 客户列表，每个元素是 dict，包含：
            - name: 企业名称
            - category: 画像类别（A/B/C/D/E/F/G）
            - category_name: 画像名称
            - industry: 所属行业
            - ai_signal: AI使用信号（具体描述）
            - current_api: 当前API供应商
            - replace_reason: Token替换理由
            - priority: 优先级（P0/P1/P2）
            - source: 搜索来源
            - script: 建议切入话术（API替换视角）
        city_name: 城市名称
        search_records: 搜索记录列表
        excluded: 排除企业列表，每个元素含 name, reason, source
    """
    wb = Workbook()

    # === Sheet 1: 目标客户清单 ===
    ws1 = wb.active
    ws1.title = "目标客户清单"

    # 样式定义
    header_font = Font(name="微软雅黑", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)

    p0_fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
    p1_fill = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")
    p2_fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")

    thin_border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin"),
    )

    cell_font = Font(name="微软雅黑", size=10)
    cell_align = Alignment(horizontal="left", vertical="center", wrap_text=True)
    center_align = Alignment(horizontal="center", vertical="center", wrap_text=True)

    # 标题行
    title = f"{city_name} - 天翼云Token目标客户清单（共{len(customers)}家）"
    ws1.merge_cells("A1:J1")
    ws1["A1"] = title
    ws1["A1"].font = Font(name="微软雅黑", size=14, bold=True, color="1F4E79")
    ws1["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws1.row_dimensions[1].height = 30

    # 表头（10列）
    headers = [
        "序号", "企业名称", "画像类别", "所属行业",
        "AI使用信号", "当前API供应商", "Token替换理由",
        "优先级", "搜索来源", "建议切入话术"
    ]
    for col, header in enumerate(headers, 1):
        cell = ws1.cell(row=2, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
        cell.border = thin_border

    ws1.row_dimensions[2].height = 25

    # 按优先级排序
    priority_order = {"P0": 0, "P1": 1, "P2": 2}
    sorted_customers = sorted(
        customers,
        key=lambda x: (priority_order.get(x.get("priority", "P2"), 2), x.get("category", "Z"))
    )

    # 数据行
    for idx, customer in enumerate(sorted_customers, 1):
        row = idx + 2
        category_full = f"{customer.get('category', '')}类 {customer.get('category_name', '')}"

        values = [
            idx,
            customer.get("name", ""),
            category_full,
            customer.get("industry", ""),
            customer.get("ai_signal", ""),
            customer.get("current_api", "待查"),
            customer.get("replace_reason", ""),
            customer.get("priority", "P2"),
            customer.get("source", ""),
            customer.get("script", ""),
        ]

        for col, value in enumerate(values, 1):
            cell = ws1.cell(row=row, column=col, value=value)
            cell.font = cell_font
            cell.border = thin_border
            if col in (1, 3, 8):  # 序号、画像、优先级居中
                cell.alignment = center_align
            else:
                cell.alignment = cell_align

        # 优先级颜色
        priority = customer.get("priority", "P2")
        if priority == "P0":
            ws1.cell(row=row, column=8).fill = p0_fill
        elif priority == "P1":
            ws1.cell(row=row, column=8).fill = p1_fill
        else:
            ws1.cell(row=row, column=8).fill = p2_fill

    # 列宽（10列）
    col_widths = [6, 28, 16, 14, 32, 16, 20, 8, 14, 42]
    for col, width in enumerate(col_widths, 1):
        ws1.column_dimensions[get_column_letter(col)].width = width

    # 冻结表头
    ws1.freeze_panes = "A3"

    # === Sheet 2: 统计汇总 ===
    ws2 = wb.create_sheet("统计汇总")

    # 优先级统计
    ws2["A1"] = "优先级统计"
    ws2["A1"].font = Font(name="微软雅黑", size=12, bold=True)
    ws2["A2"] = "优先级"
    ws2["B2"] = "数量"
    ws2["C2"] = "占比"
    for col in ("A2", "B2", "C2"):
        ws2[col].font = header_font
        ws2[col].fill = header_fill
        ws2[col].alignment = header_align
        ws2[col].border = thin_border

    priority_counts = {"P0": 0, "P1": 0, "P2": 0}
    for c in customers:
        p = c.get("priority", "P2")
        priority_counts[p] = priority_counts.get(p, 0) + 1

    priority_names = {
        "P0": "P0 高优先级（必跟）",
        "P1": "P1 中优先级（可跟）",
        "P2": "P2 低优先级（暂缓）"
    }
    for i, (key, name) in enumerate(priority_names.items()):
        row = i + 3
        ws2.cell(row=row, column=1, value=name).font = cell_font
        ws2.cell(row=row, column=2, value=priority_counts.get(key, 0)).font = cell_font
        pct = f"{priority_counts.get(key, 0) / len(customers) * 100:.1f}%"
        ws2.cell(row=row, column=3, value=pct).font = cell_font
        for col in range(1, 4):
            ws2.cell(row=row, column=col).border = thin_border
            ws2.cell(row=row, column=col).alignment = center_align

    # 画像统计
    ws2["A7"] = "画像分布统计"
    ws2["A7"].font = Font(name="微软雅黑", size=12, bold=True)
    ws2["A8"] = "画像类别"
    ws2["B8"] = "数量"
    ws2["C8"] = "占比"
    for col in ("A8", "B8", "C8"):
        ws2[col].font = header_font
        ws2[col].fill = header_fill
        ws2[col].alignment = header_align
        ws2[col].border = thin_border

    category_names = {
        "A": "A类 AI开发商",
        "B": "B类 自建AI应用",
        "C": "C类 已有AI的制造",
        "D": "D类 已用AI的跨境",
        "E": "E类 已用AI编码的软件",
        "F": "F类 已部署AI实训的院校",
        "G": "G类 已用AI的内容客服",
    }
    category_counts = {}
    for c in customers:
        cat = c.get("category", "Z")
        category_counts[cat] = category_counts.get(cat, 0) + 1

    for i, (key, name) in enumerate(category_names.items()):
        row = i + 9
        ws2.cell(row=row, column=1, value=name).font = cell_font
        ws2.cell(row=row, column=2, value=category_counts.get(key, 0)).font = cell_font
        pct = f"{category_counts.get(key, 0) / len(customers) * 100:.1f}%"
        ws2.cell(row=row, column=3, value=pct).font = cell_font
        for col in range(1, 4):
            ws2.cell(row=row, column=col).border = thin_border
            ws2.cell(row=row, column=col).alignment = center_align

    # 总计
    total_row = 16
    ws2.cell(row=total_row, column=1, value="总计").font = Font(name="微软雅黑", size=10, bold=True)
    ws2.cell(row=total_row, column=2, value=len(customers)).font = Font(name="微软雅黑", size=10, bold=True)
    ws2.cell(row=total_row, column=3, value="100%").font = Font(name="微软雅黑", size=10, bold=True)
    for col in range(1, 4):
        ws2.cell(row=total_row, column=col).border = thin_border
        ws2.cell(row=total_row, column=col).alignment = center_align

    # 排除统计
    exclude_row = 18
    ws2.cell(row=exclude_row, column=1, value="排除企业数").font = Font(name="微软雅黑", size=10, bold=True)
    ws2.cell(row=exclude_row, column=2, value=len(excluded) if excluded else 0).font = cell_font
    ws2.cell(row=exclude_row, column=3, value="涉密/军工/金融核心/无AI信号等").font = cell_font
    for col in range(1, 4):
        ws2.cell(row=exclude_row, column=col).border = thin_border
        ws2.cell(row=exclude_row, column=col).alignment = center_align

    ws2.column_dimensions["A"].width = 24
    ws2.column_dimensions["B"].width = 10
    ws2.column_dimensions["C"].width = 36

    # === Sheet 3: 搜索记录 ===
    if search_records:
        ws3 = wb.create_sheet("搜索记录")
        search_headers = ["搜索序号", "阶段", "关键词", "结果数量", "说明"]
        for col, header in enumerate(search_headers, 1):
            cell = ws3.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_align
            cell.border = thin_border

        for idx, record in enumerate(search_records, 1):
            row = idx + 1
            values = [
                idx,
                record.get("phase", ""),
                record.get("keyword", ""),
                record.get("result_count", 0),
                record.get("note", ""),
            ]
            for col, value in enumerate(values, 1):
                cell = ws3.cell(row=row, column=col, value=value)
                cell.font = cell_font
                cell.border = thin_border
                cell.alignment = cell_align

        col_widths_s3 = [10, 20, 40, 12, 30]
        for col, width in enumerate(col_widths_s3, 1):
            ws3.column_dimensions[get_column_letter(col)].width = width

    # === Sheet 4: 排除清单 ===
    if excluded:
        ws4 = wb.create_sheet("排除清单")
        exclude_headers = ["序号", "企业名称", "排除原因", "搜索来源"]
        for col, header in enumerate(exclude_headers, 1):
            cell = ws4.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_align
            cell.border = thin_border

        for idx, item in enumerate(excluded, 1):
            row = idx + 1
            values = [
                idx,
                item.get("name", ""),
                item.get("reason", ""),
                item.get("source", ""),
            ]
            for col, value in enumerate(values, 1):
                cell = ws4.cell(row=row, column=col, value=value)
                cell.font = cell_font
                cell.border = thin_border
                cell.alignment = cell_align

        ws4.column_dimensions["A"].width = 8
        ws4.column_dimensions["B"].width = 30
        ws4.column_dimensions["C"].width = 30
        ws4.column_dimensions["D"].width = 16

    # 保存
    date_str = datetime.now().strftime("%Y%m%d")
    filename = f"{city_name}_Token目标客户清单_{date_str}.xlsx"
    wb.save(filename)
    print(f"Excel 文件已生成: {filename}")
    return filename


if __name__ == "__main__":
    # 示例用法（API替换视角）
    sample_customers = [
        {
            "name": "XX智能科技有限公司",
            "category": "A",
            "category_name": "AI开发商",
            "industry": "人工智能",
            "ai_signal": "产品页展示AI智能客服SaaS，招聘LLM算法工程师",
            "current_api": "OpenAI",
            "replace_reason": "降本（API调用量大）+ 多模型统一管理",
            "priority": "P0",
            "source": "招聘网站+产品页",
            "script": "你们的AI客服产品现在调用的是OpenAI的API吧？天翼云提供兼容接口，替换endpoint就行，成本更优。",
        },
        {
            "name": "XX制造股份有限公司",
            "category": "C",
            "category_name": "已有AI的制造",
            "industry": "装备制造",
            "ai_signal": "新闻提到上线AI知识库+智能客服，供应商案例确认",
            "current_api": "文心一言",
            "replace_reason": "降本 + 稳定性保障",
            "priority": "P0",
            "source": "新闻+供应商案例",
            "script": "你们的AI知识库现在用的是文心的API？天翼云可以提供兼容接口替换，不停机切换，电信级稳定性保障。",
        },
    ]
    sample_excluded = [
        {"name": "XX军工科技有限公司", "reason": "涉密/军工", "source": "天眼查"},
        {"name": "XX银行核心系统", "reason": "金融核心系统", "source": "招标网"},
    ]
    generate_excel(sample_customers, "示例城市", excluded=sample_excluded)
```

---

## Markdown 输出模板

```markdown
# {城市名} Token 目标客户清单

> 生成时间：{日期}
> 搜索次数：{次数} 次
> 客户总数：100 家
> 排除企业：{排除数} 家（涉密/军工/金融核心/无AI信号等）

## 统计摘要

| 维度 | 数量 | 占比 |
|------|------|------|
| P0 高优先级 | XX | XX% |
| P1 中优先级 | XX | XX% |
| P2 低优先级 | XX | XX% |

## P0 高优先级客户（XX 家）

| 序号 | 企业名称 | 画像类别 | AI使用信号 | 当前API供应商 | Token替换理由 |
|------|---------|---------|-----------|-------------|-------------|
| 1 | XX企业 | A类 AI开发商 | 产品上线+招聘LLM工程师 | OpenAI | 降本+多模型管理 |

## P1 中优先级客户（XX 家）

（同上格式）

## P2 低优先级客户（XX 家）

（同上格式）

## 画像分布

| 画像 | 数量 | 占比 |
|------|------|------|
| A类 AI开发商 | XX | XX% |
| B类 自建AI应用 | XX | XX% |
| C类 已有AI的制造 | XX | XX% |
| D类 已用AI的跨境 | XX | XX% |
| E类 已用AI编码的软件 | XX | XX% |
| F类 已部署AI实训的院校 | XX | XX% |
| G类 已用AI的内容客服 | XX | XX% |

## 排除清单（XX 家）

| 序号 | 企业名称 | 排除原因 |
|------|---------|---------|
| 1 | XX军工科技 | 涉密/军工 |
| 2 | XX银行核心系统 | 金融核心系统 |
```

---

## 字段填写指南

### AI 使用信号（必填）

从搜索结果中提取具体证据，格式：`信号类型 + 具体描述`

| 信号类型 | 填写示例 |
|---------|---------|
| 招聘信号 | "招聘LLM算法工程师，JD要求OpenAI API经验" |
| 产品信号 | "产品页展示AI智能客服SaaS，已商用" |
| API信号 | "技术博客提到调用文心一言API" |
| 融资信号 | "2024年获AI方向A轮融资5000万" |
| 工具信号 | "招聘JD要求会使用Copilot/Cursor" |
| 案例信号 | "供应商案例中列为AI知识库客户" |

### 当前 API 供应商（必填）

从搜索结果中判断，如无法确定填"待查"：

| 供应商 | 判断依据 |
|--------|---------|
| OpenAI | 提到 ChatGPT/GPT-4/OpenAI API |
| 百度文心 | 提到文心一言/ERNIE/百度AI |
| 阿里通义 | 提到通义千问/Qwen/阿里云AI |
| DeepSeek | 提到 DeepSeek/深度求索 |
| 智谱 | 提到智谱/ChatGLM/GLM |
| 待查 | 有AI应用但未明确供应商 |

### Token 替换理由（必填）

从以下选项中选择 1-2 个：

| 理由 | 适用场景 |
|------|---------|
| 降本 | API调用量大（客服/翻译/文案/编码） |
| 统一管理 | 多部门/多AI工具各自采购 |
| 稳定性 | 7x24运行的生产环境 |
| 合规 | OpenAI在国内有合规风险/信创要求 |

### 建议切入话术（API 替换视角）

**模板**：`你们的[AI应用]现在用的是[当前API]？天翼云提供兼容接口，替换endpoint就行，[替换价值]。`

**示例**：
- "你们的AI客服现在调用的是OpenAI的API吧？天翼云提供兼容接口，替换endpoint就行，成本更优。"
- "你们内部AI工具用的是文心的API？天翼云可以提供统一接口，一个账号管所有模型调用。"
- "你们开发团队用Copilot？天翼云可以提供兼容API，成本更可控，代码数据走天翼云也安全。"
