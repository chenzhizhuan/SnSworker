---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '978fb4a0-0f31-4fd4-8c56-2b99216a016c'
  PropagateID: '978fb4a0-0f31-4fd4-8c56-2b99216a016c'
  ReservedCode1: '8207c15e-f36a-47e7-a116-48c4d5de2c8d'
  ReservedCode2: '8207c15e-f36a-47e7-a116-48c4d5de2c8d'
---

# 文档生成错误复盘

## 问题总览

文档生成过程中常见的格式错误和解决方案。

---

## 错误1：行间距异常（严重）

### 现象
- 一句话占一整页，文档内容极度稀疏

### 根因
python-docx 库的行间距参数容易设置错误：
```python
# 错误代码 - 被解释为28 twips，实际是336磅
para.paragraph_format.line_spacing = 28
```

### 正确做法
```python
from docx.enum.text import WD_LINE_SPACING
from docx.shared import Pt

para.paragraph_format.line_spacing_rule = WD_LINE_SPACING.EXACTLY
para.paragraph_format.line_spacing = Pt(28)  # 必须明确指定单位
```

### 验证方法
```bash
unzip -p file.docx word/document.xml | grep -o 'w:line="[^"]*"'
# 正确值应为 560（28磅）
```

---

## 错误2：空行缺失/多余

### 正确规范（请示类）

| 位置 | 空行数量 | 说明 |
|------|---------|------|
| 大标题后 | 1个 | 标题与称谓之间 |
| 结束语后 | 1个 | "妥否，请批示。"与"附件："之间 |
| 其他位置 | 0个 | 段落之间紧密相连 |

### 正确代码
```python
def add_empty_paragraph(doc):
    """添加规范的空行"""
    p = doc.add_paragraph()
    p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    p.paragraph_format.line_spacing = Pt(28)
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)
    return p
```

### 特别说明
- "附件："和"1. xxx"在同一行（不换行）
- 附件2另起一行
- 段落之间不要多余空行

---

## 错误3：引号类型错误

### 根因
代码中使用了英文直引号（U+0022）而非中文弯引号（U+201C/U+201D）。

### 对比

| 类型 | 字符 | Unicode | 视觉效果 |
|------|------|---------|---------|
| 英文直引号 | " | U+0022 | 垂直的 |
| 中文左引号 | " | U+201C | 向左弯曲 |
| 中文右引号 | " | U+201D | 向右弯曲 |

### 正确做法
```python
LQUOTE = '\u201c'  # 左引号
RQUOTE = '\u201d'  # 右引号
text = f'以下简称{LQUOTE}数据宝公司{RQUOTE}'
```

---

## 经验总结

### 1. 参考文件分析
拿到用户提供的正确样例后，应：
- 解压docx文件
- 分析XML结构（`word/document.xml`）
- 提取关键参数（行间距、缩进、字体等）

### 2. 代码生成验证
每次生成后应验证：
- 检查行间距 XML 值
- 检查引号类型 Unicode

### 3. 规范文档维护
所有格式规范应及时更新到 SKILL.md：
- 空行规范
- 常见陷阱
- 验证方法

> AI生成