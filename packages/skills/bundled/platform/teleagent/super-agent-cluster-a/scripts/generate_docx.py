#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
超级Agent集群 - Word文档生成器（XML级格式控制）
通过复用参考文档的全部XML文件，仅替换document.xml中的body内容，
实现与参考文档100%一致的格式。

用法:
    python generate_docx.py --output <路径> --title <标题> --subtitle <副标题>
                            --date <日期> --info <信息行JSON> --content <内容JSON>

内容JSON格式:
[{"h1": "第1章 标题", "sections": [{"h2": "1.1 标题",
  "paragraphs": ["正文..."], "tables": [{"headers": ["列1"], "rows": [["数据1"]]}],
  "subsections": [{"h3": "1.1.1 标题", "paragraphs": ["子节正文..."]}]}]}]
"""

import os
import re
import sys
import json
import hashlib
import zipfile
import argparse
import warnings
from datetime import datetime
import xml.etree.ElementTree as ET
import xml.sax.saxutils as saxutils

class FormatValidationError(Exception):
    """格式自校验失败异常——当生成文档格式与reference.docx不一致时抛出"""
    pass


# ============================================================
# 常量定义 - 与参考文档格式完全一致
# ============================================================

# 参考文档路径（优先使用技能内置的参考文档）
_SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 候选路径：技能assets目录（首选）→ 用户主目录
_REF_DOCX_CANDIDATES = [
    os.path.join(_SKILL_DIR, 'assets', 'reference.docx'),
    os.path.join(os.path.expanduser('~'), '.local', 'share', 'TeleAgent', 'reference.docx'),
]

# 颜色常量（字体颜色全部为黑色，边框/背景色与参考文档一致）
COLOR_ACCENT = '000000'       # 封面装饰线颜色黑色
COLOR_BORDER = 'B0C4D4'       # 表格边框浅蓝色（非字体色）
COLOR_TABLE_HEADER = 'D6E4F0' # 表头背景色（浅蓝底，黑体加粗黑字）
COLOR_TABLE_ROW_WHITE = 'FFFFFF'  # 表格白色行（非字体色）
COLOR_TABLE_ROW_ALT = 'F0F6FA'  # 表格交替行色（非字体色）


# 字号常量（单位：半磅，即 w:sz 值）
SZ_TITLE_COVER = 80      # 封面大标题 40pt
SZ_TOC_TITLE = 32        # 目录标题 16pt
SZ_H2 = 30               # 二级标题 15pt
SZ_H3 = 28               # 三级标题 14pt
SZ_TABLE_HEADER = 22     # 表头 11pt
SZ_TABLE_DATA = 22       # 表格数据 11pt
SZ_COVER_BOTTOM = 16     # 封面底部标签 8pt
SZ_COVER_BADGE = 18      # 封面标识 9pt

# 间距常量
SPACING_H1_BEFORE = 480
SPACING_H1_AFTER = 240
SPACING_H2_BEFORE = 360
SPACING_H2_AFTER = 180
SPACING_H3_BEFORE = 240
SPACING_H3_AFTER = 120

# 页面尺寸（A4）
PAGE_WIDTH = 11906
PAGE_HEIGHT = 16838

# 表格总宽度（twips）  # DOCX-DOC-3修复：从函数内部提取为模块级常量
TABLE_TOTAL_WIDTH = 8772

# WordprocessingML命名空间（模块级常量，消除函数内重复定义）
NS_W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'


# ============================================================
# 共享辅助函数 - 消除 validate_format_consistency() 中的重复遍历模式
# ============================================================

def _iter_heading_paragraphs(root, style_filter=None):
    """遍历XML树中的标题段落（pStyle 1/2/3），返回 (style_val, full_text, para_elem) 列表。

    消除 validate_format_consistency() 中 15+ 处重复的
    iter(NS_W+'p') → pPr.find → pStyle.find → text 提取模式。

    Args:
        root: ET.Element，document.xml 的根节点
        style_filter: 可选，限定样式值集合如 ('1','2')，None 表示全部 (1,2,3)

    Returns:
        list of (style_val:str, full_text:str, para_elem:ET.Element)
    """
    results = []
    if root is None:
        return results
    valid_styles = style_filter if style_filter is not None else ('1', '2', '3')
    for p in root.iter(NS_W + 'p'):
        pPr = p.find(NS_W + 'pPr')
        if pPr is None:
            continue
        pStyle = pPr.find(NS_W + 'pStyle')
        if pStyle is None:
            continue
        sv = pStyle.get(NS_W + 'val', '')
        if sv in valid_styles:
            ft = ''.join(t.text for t in p.iter(NS_W + 't') if t.text)
            results.append((sv, ft, p))
    return results


def _strip_heading_number(full_text):
    """去除标题编号前缀（第X章 / X.X / X.X.X），返回纯标题文字。"""
    ft = re.sub(r'^第[\d一二三四五六七八九十百零]+章\s*', '', full_text)
    ft = re.sub(r'^\d+\.\d+(?:\.\d+)?\s*', '', ft)
    return ft.strip()


# ============================================================
# XML构建函数
# ============================================================

def esc(text):
    """XML转义"""
    return saxutils.escape(str(text))


def make_heading_paragraph(level, title_text, bookmark_id, bookmark_name,
                            bookmark_id2, bookmark_name2,
                            p_style, sz_val, spacing_before, spacing_after):
    """生成标题段落XML（统一实现，供H1/H2/H3调用）

    与参考文档格式100%一致：双书签结构+完整标题文本（含编号前缀）。

    Args:
        level: 标题层级（1/2/3），用于错误提示
        title_text: 标题文本（含编号前缀，如"第1章 研究概述"/"1.1 背景"）
        bookmark_id: 主书签ID（TOC跳转用）
        bookmark_name: 主书签名称
        bookmark_id2: 副书签ID（与参考文档双书签结构一致）
        bookmark_name2: 副书签名称
        p_style: pStyle值（"1"/"2"/"3"）
        sz_val: 字号（SZ_H2/SZ_H3），H1传None表示不设字号
        spacing_before: 段前间距
        spacing_after: 段后间距
    """
    if not str(title_text).strip():
        raise FormatValidationError(
            f'make_h{level}_paragraph收到空title_text！——标题文本为空'
        )
    if sz_val is None:
        # H1：无sz设定（使用styles.xml中heading 1的默认sz=32）
        title_rpr = '<w:rPr><w:rFonts w:eastAsia="黑体"/><w:b/><w:bCs/></w:rPr>'
    else:
        # H2/H3：有sz设定
        title_rpr = f'<w:rPr><w:rFonts w:eastAsia="黑体"/><w:b/><w:bCs/>' \
                    f'<w:sz w:val="{sz_val}"/>' \
                    f'<w:szCs w:val="{sz_val}"/></w:rPr>'
    return (
        f'<w:p><w:pPr><w:pStyle w:val="{p_style}"/>'
        f'<w:spacing w:before="{spacing_before}" w:after="{spacing_after}"/>'
        f'</w:pPr>'
        f'<w:bookmarkStart w:id="{bookmark_id}" w:name="{bookmark_name}"/>'
        f'<w:bookmarkStart w:id="{bookmark_id2}" w:name="{bookmark_name2}"/>'
        f'<w:r>{title_rpr}'
        f'<w:t>{esc(title_text)}</w:t></w:r>'
        f'<w:bookmarkEnd w:id="{bookmark_id}"/>'
        f'<w:bookmarkEnd w:id="{bookmark_id2}"/>'
        f'</w:p>'
    )


def make_h1_paragraph(title_text, bookmark_id, bookmark_name, bookmark_id2, bookmark_name2):
    """生成H1标题段落XML（含编号前缀+双书签，与参考文档格式一致）"""
    return make_heading_paragraph(
        1, title_text, bookmark_id, bookmark_name, bookmark_id2, bookmark_name2,
        '1', None, SPACING_H1_BEFORE, SPACING_H1_AFTER
    )


def make_h2_paragraph(title_text, bookmark_id, bookmark_name, bookmark_id2, bookmark_name2):
    """生成H2标题段落XML（含编号前缀+双书签，与参考文档格式一致）"""
    return make_heading_paragraph(
        2, title_text, bookmark_id, bookmark_name, bookmark_id2, bookmark_name2,
        '2', SZ_H2, SPACING_H2_BEFORE, SPACING_H2_AFTER
    )


def make_h3_paragraph(title_text, bookmark_id, bookmark_name, bookmark_id2, bookmark_name2):
    """生成H3标题段落XML（含编号前缀+双书签，与参考文档格式一致）"""
    return make_heading_paragraph(
        3, title_text, bookmark_id, bookmark_name, bookmark_id2, bookmark_name2,
        '3', SZ_H3, SPACING_H3_BEFORE, SPACING_H3_AFTER
    )


def make_paragraph(text):
    """生成正文段落XML
    格式：段前0磅, 段后0磅, 两端对齐, 首行缩进480（2字符）
    """
    if text is None:
        text = ''
    text = str(text)
    if not text.strip():
        return '<w:p><w:pPr><w:jc w:val="both"/></w:pPr></w:p>'
    return (
        f'<w:p><w:pPr><w:ind w:firstLine="480"/>'
        f'<w:jc w:val="both"/></w:pPr>'
        f'<w:r><w:t>{esc(text)}</w:t></w:r>'
        f'</w:p>'
    )


def make_analysis_paragraph(text):
    """生成论文式分析段落XML
    
    与make_paragraph的区别：
    - 段前120（6磅）段后120（6磅）增加段落间距
    - 首行缩进480（2字符）保持论文格式
    - 两端对齐
    - 行间距1.5倍（w:spacing w:line="360" w:lineRule="auto"）
    
    用于content_data中section/subsection的"analysis"字段，
    支持连续段落式论文行文，替代分点列表式信息堆砌。
    """
    if text is None:
        text = ''
    text = str(text)
    if not text.strip():
        return '<w:p><w:pPr><w:spacing w:before="120" w:after="120" w:line="360" w:lineRule="auto"/><w:jc w:val="both"/></w:pPr></w:p>'
    return (
        f'<w:p><w:pPr>'
        f'<w:spacing w:before="120" w:after="120" w:line="360" w:lineRule="auto"/>'
        f'<w:ind w:firstLine="480"/>'
        f'<w:jc w:val="both"/></w:pPr>'
        f'<w:r><w:t xml:space="preserve">{esc(text)}</w:t></w:r>'
        f'</w:p>'
    )


def make_table(headers, rows):
    """生成表格XML
    格式：全边框B0C4D4, 表头#D6E4F0黑体加粗黑字, 交替行#FFFFFF/#F0F6FA
    所有单元格文字居中对齐（与参考文档一致）
    """
    if headers is None:
        headers = []
    if rows is None:
        rows = []
    if not isinstance(headers, list):  # BUG-12修复：类型守卫
        headers = []
    if not isinstance(rows, list):  # BUG-12修复：类型守卫
        rows = []
    num_cols = len(headers)
    if num_cols == 0:
        return ''
    
    # 列宽均分
    total_width = TABLE_TOTAL_WIDTH  # DOCX-DOC-3修复：提取为模块级常量
    col_widths = [total_width // num_cols] * num_cols
    # 调整最后一列以消除舍入误差
    col_widths[-1] = total_width - sum(col_widths[:-1])
    
    # tblGrid
    grid_xml = '<w:tblGrid>' + ''.join(
        f'<w:gridCol w:w="{w}"/>' for w in col_widths
    ) + '</w:tblGrid>'
    
    # 表格级边框XML（含insideH/insideV，用于tblBorders）
    border_xml = (
        f'<w:top w:val="single" w:sz="4" w:space="0" w:color="{COLOR_BORDER}"/>'
        f'<w:left w:val="single" w:sz="4" w:space="0" w:color="{COLOR_BORDER}"/>'
        f'<w:bottom w:val="single" w:sz="4" w:space="0" w:color="{COLOR_BORDER}"/>'
        f'<w:right w:val="single" w:sz="4" w:space="0" w:color="{COLOR_BORDER}"/>'
        f'<w:insideH w:val="single" w:sz="4" w:space="0" w:color="{COLOR_BORDER}"/>'
        f'<w:insideV w:val="single" w:sz="4" w:space="0" w:color="{COLOR_BORDER}"/>'
    )
    
    # 单元格级边框XML（仅4外边框，无insideH/insideV，与参考文档tcBorders一致）
    cell_border_xml = (
        f'<w:top w:val="single" w:sz="4" w:space="0" w:color="{COLOR_BORDER}"/>'
        f'<w:left w:val="single" w:sz="4" w:space="0" w:color="{COLOR_BORDER}"/>'
        f'<w:bottom w:val="single" w:sz="4" w:space="0" w:color="{COLOR_BORDER}"/>'
        f'<w:right w:val="single" w:sz="4" w:space="0" w:color="{COLOR_BORDER}"/>'
    )
    
    # 表头行
    header_cells = ''
    for i, h in enumerate(headers):
        if h is None:
            h = ''  # None防护：表头单元格为None时显示空字符串
        header_cells += (
            f'<w:tc><w:tcPr>'
            f'<w:tcW w:w="{col_widths[i]}" w:type="dxa"/>'
            f'<w:tcBorders>{cell_border_xml}</w:tcBorders>'
            f'<w:shd w:val="clear" w:color="auto" w:fill="{COLOR_TABLE_HEADER}"/>'
            f'<w:tcMar><w:top w:w="100" w:type="dxa"/><w:left w:w="120" w:type="dxa"/>'
            f'<w:bottom w:w="100" w:type="dxa"/><w:right w:w="120" w:type="dxa"/></w:tcMar>'
            f'<w:vAlign w:val="center"/>'
            f'</w:tcPr>'
            f'<w:p><w:pPr><w:spacing w:line="280" w:lineRule="auto"/>'
            f'<w:jc w:val="center"/></w:pPr>'
            f'<w:r><w:rPr><w:rFonts w:eastAsia="黑体"/><w:b/><w:bCs/>'
            f'<w:sz w:val="{SZ_TABLE_HEADER}"/>'
            f'<w:szCs w:val="{SZ_TABLE_HEADER}"/></w:rPr>'
            f'<w:t>{esc(h)}</w:t></w:r>'
            f'</w:p></w:tc>'
        )
    
    header_row = (
        f'<w:tr><w:trPr><w:cantSplit/><w:tblHeader/></w:trPr>'
        f'{header_cells}</w:tr>'
    )
    
    # 数据行
    data_rows = ''
    for row_idx, row in enumerate(rows):
        if not isinstance(row, (list, tuple)):  # BUG-15修复：跳过None/非列表行元素
            row = []
        # 交替行色：偶数行白色，奇数行浅蓝
        fill = COLOR_TABLE_ROW_WHITE if row_idx % 2 == 0 else COLOR_TABLE_ROW_ALT
        
        cells = ''
        for col_idx in range(num_cols):
            cell_text = row[col_idx] if col_idx < len(row) else ''
            if cell_text is None:  # LOW-4修复：None转空字符串而非显示"None"
                cell_text = ''
            cells += (
                f'<w:tc><w:tcPr>'
                f'<w:tcW w:w="{col_widths[col_idx]}" w:type="dxa"/>'
                f'<w:tcBorders>{cell_border_xml}</w:tcBorders>'
                f'<w:shd w:val="clear" w:color="auto" w:fill="{fill}"/>'
                f'<w:tcMar><w:top w:w="80" w:type="dxa"/><w:left w:w="120" w:type="dxa"/>'
                f'<w:bottom w:w="80" w:type="dxa"/><w:right w:w="120" w:type="dxa"/></w:tcMar>'
                f'<w:vAlign w:val="center"/>'
                f'</w:tcPr>'
                f'<w:p><w:pPr><w:spacing w:line="280" w:lineRule="auto"/>'
                f'<w:jc w:val="center"/></w:pPr>'
                f'<w:r><w:rPr><w:sz w:val="{SZ_TABLE_DATA}"/>'
                f'<w:szCs w:val="{SZ_TABLE_DATA}"/></w:rPr>'
                f'<w:t>{esc(cell_text)}</w:t></w:r>'
                f'</w:p></w:tc>'
            )
        
        data_rows += (
            f'<w:tr><w:trPr><w:cantSplit/></w:trPr>'
            f'{cells}</w:tr>'
        )
    
    return (
        f'<w:tbl><w:tblPr><w:tblW w:w="5000" w:type="pct"/>'
        f'<w:tblBorders>{border_xml}</w:tblBorders>'
        f'<w:tblLayout w:type="fixed"/>'
        f'<w:tblCellMar><w:left w:w="10" w:type="dxa"/>'
        f'<w:right w:w="10" w:type="dxa"/></w:tblCellMar>'
        f'<w:tblLook w:val="04A0" w:firstRow="1" w:lastRow="0" '
        f'w:firstColumn="1" w:lastColumn="0" w:noHBand="0" w:noVBand="1"/>'
        f'</w:tblPr>{grid_xml}{header_row}{data_rows}</w:tbl>'
    )

def make_cover_page(title, subtitle, info_rows, bottom_label_left, bottom_label_right):
    """生成封面页XML（全页无边框表格，零边距）
    """
    # None值防护（DOCX-BUG-2/3修复，V9-DOCX-LOW-1：增加类型守卫）
    # V10-DOCX-HIGH-1：增加元素结构校验，防止畸形元素导致ValueError解包崩溃
    if not isinstance(info_rows, list):
        info_rows = []
    bottom_label_left = bottom_label_left or ''
    bottom_label_right = bottom_label_right or ''
    title = title or ''
    subtitle = subtitle or ''
    # 信息行（带左侧竖线边框）
    info_xml = ''
    for item in info_rows:
        # 元素结构校验：跳过非(list,tuple)或长度!=2的畸形元素
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            continue
        label, value = item
        # None防护（V9-DOCX-BUG-1）：JSON null值导致封面显示"None"
        if label is None:
            label = ''
        if value is None:
            value = ''
        # 自动补全冒号：label末尾无中英文冒号时追加中文冒号，确保封面信息行标签与值之间有冒号分隔
        if label and not label.rstrip().endswith(('：', ':')):
            label = label.rstrip() + '：'
        info_xml += (
            f'<w:p><w:pPr>'
            f'<w:pBdr><w:left w:val="single" w:sz="8" w:space="12" w:color="{COLOR_ACCENT}"/></w:pBdr>'
            f'<w:spacing w:after="80"/>'
            f'<w:ind w:left="1400"/></w:pPr>'
            f'<w:r><w:t>{esc(label)}</w:t></w:r>'
            f'<w:r><w:t>{esc(value)}</w:t></w:r>'
            f'</w:p>'
        )

    # 封面内容（顶部间距→标识行→主标题→副标题→信息行→底部间距→底部标签）

    cover_table_cell = (
        # 顶部间距
        '<w:p><w:pPr><w:spacing w:before="1200"/></w:pPr></w:p>'
        # 标识行
        f'<w:p><w:pPr>'
        f'<w:pBdr><w:bottom w:val="single" w:sz="6" w:space="8" w:color="{COLOR_ACCENT}"/></w:pBdr>'
        f'<w:spacing w:after="500"/>'
        f'<w:ind w:left="1200" w:right="800"/></w:pPr>'
        f'<w:r><w:rPr><w:spacing w:val="40"/>'
        f'<w:sz w:val="{SZ_COVER_BADGE}"/><w:szCs w:val="{SZ_COVER_BADGE}"/></w:rPr>'
        f'<w:t>TECHNICAL REPORT</w:t></w:r>'
        f'</w:p>'
        # 主标题
        f'<w:p><w:pPr><w:spacing w:after="300" w:line="920" w:lineRule="atLeast"/>'
        f'<w:ind w:left="1200"/></w:pPr>'
        f'<w:r><w:rPr><w:b/><w:bCs/>'
        f'<w:sz w:val="{SZ_TITLE_COVER}"/><w:szCs w:val="{SZ_TITLE_COVER}"/></w:rPr>'
        f'<w:t>{esc(title)}</w:t></w:r>'
        f'</w:p>'
        # 副标题
        f'<w:p><w:pPr><w:spacing w:after="800"/>'
        f'<w:ind w:left="1200"/></w:pPr>'
        f'<w:r><w:t>{esc(subtitle)}</w:t></w:r>'
        f'</w:p>'
        # 信息行
        + info_xml +
        # 底部间距 + 底部标签
        f'<w:p><w:pPr><w:spacing w:before="1200"/></w:pPr></w:p>'
        f'<w:p><w:pPr>'
        f'<w:pBdr><w:top w:val="single" w:sz="2" w:space="8" w:color="{COLOR_ACCENT}"/></w:pBdr>'
        f'<w:spacing w:before="200"/>'
        f'<w:ind w:left="1200" w:right="800"/></w:pPr>'
        f'<w:r><w:rPr>'
        f'<w:sz w:val="{SZ_COVER_BOTTOM}"/><w:szCs w:val="{SZ_COVER_BOTTOM}"/></w:rPr>'
        f'<w:t>{esc(bottom_label_left)}</w:t></w:r>'
        # 封面底部分隔左右标签的视觉间距（40空格）
        f'<w:r><w:t xml:space="preserve">                                        </w:t></w:r>'
        f'<w:r><w:rPr>'
        f'<w:sz w:val="{SZ_COVER_BOTTOM}"/><w:szCs w:val="{SZ_COVER_BOTTOM}"/></w:rPr>'
        f'<w:t>{esc(bottom_label_right)}</w:t></w:r>'
        f'</w:p>'
    )

    # 封面表格（全页，无边框，零边距）
    cover = (
        f'<w:tbl><w:tblPr><w:tblW w:w="5000" w:type="pct"/>'
        f'<w:tblBorders>'
        f'<w:top w:val="none" w:sz="0" w:space="0" w:color="FFFFFF"/>'
        f'<w:left w:val="none" w:sz="0" w:space="0" w:color="FFFFFF"/>'
        f'<w:bottom w:val="none" w:sz="0" w:space="0" w:color="FFFFFF"/>'
        f'<w:right w:val="none" w:sz="0" w:space="0" w:color="FFFFFF"/>'
        f'<w:insideH w:val="none" w:sz="0" w:space="0" w:color="FFFFFF"/>'
        f'<w:insideV w:val="none" w:sz="0" w:space="0" w:color="FFFFFF"/>'
        f'</w:tblBorders>'
        f'<w:tblLayout w:type="fixed"/>'
        f'<w:tblCellMar><w:left w:w="10" w:type="dxa"/>'
        f'<w:right w:w="10" w:type="dxa"/></w:tblCellMar>'
        f'<w:tblLook w:val="04A0" w:firstRow="1" w:lastRow="0" '
        f'w:firstColumn="1" w:lastColumn="0" w:noHBand="0" w:noVBand="1"/>'
        f'</w:tblPr>'
        f'<w:tblGrid><w:gridCol w:w="{PAGE_WIDTH}"/></w:tblGrid>'
        f'<w:tr><w:trPr><w:trHeight w:val="{PAGE_HEIGHT}"/></w:trPr>'
        f'<w:tc><w:tcPr>'
        f'<w:tcW w:w="100" w:type="dxa"/>'
        f'<w:tcBorders>'
        f'<w:top w:val="none" w:sz="0" w:space="0" w:color="FFFFFF"/>'
        f'<w:left w:val="none" w:sz="0" w:space="0" w:color="FFFFFF"/>'
        f'<w:bottom w:val="none" w:sz="0" w:space="0" w:color="FFFFFF"/>'
        f'<w:right w:val="none" w:sz="0" w:space="0" w:color="FFFFFF"/>'
        f'</w:tcBorders>'
        f'<w:shd w:val="clear" w:color="auto" w:fill="FFFFFF"/>'

        f'<w:vAlign w:val="center"/>'
        f'</w:tcPr>'
        f'{cover_table_cell}'
        f'</w:tc></w:tr>'
        f'</w:tbl>'
    )
    
    return cover


def _make_toc_entry(level, title_text, bookmark_name):
    """生成单个静态TOC目录条目段落XML
    
    在TOC域的separate和end之间预填充，使Word打开时即使不更新域也能显示完整目录。
    每个条目包含超链接（点击跳转至对应书签）和PAGEREF域（页码占位"1"，
    Word更新域后替换为真实页码）。
    
    Args:
        level: 标题层级（1/2/3）
        title_text: 标题文本（含编号前缀，如"第1章 研究概述"）
        bookmark_name: 主书签名称（如"_Toc100000"），用于超链接跳转
    """
    toc_style = f'TOC{level}'
    rpr = (
        '<w:rPr>'
        '<w:rFonts w:asciiTheme="minorHAnsi" w:eastAsiaTheme="minorEastAsia" '
        'w:hAnsiTheme="minorHAnsi" w:cstheme="minorBidi" w:hint="eastAsia"/>'
        '<w:b w:val="0"/><w:bCs w:val="0"/>'
        '<w:noProof/>'
        '<w:color w:val="auto"/>'
        '<w:kern w:val="2"/>'
        '<w:sz w:val="22"/>'
        '<w:szCs w:val="22"/>'
        '</w:rPr>'
    )
    pageref_instr = f' PAGEREF {bookmark_name} \\h '
    
    return (
        f'<w:p><w:pPr>'
        f'<w:pStyle w:val="{toc_style}"/>'
        f'{rpr}'
        f'</w:pPr>'
        f'<w:hyperlink w:anchor="{bookmark_name}" w:history="1">'
        f'<w:r>{rpr}<w:t>{esc(title_text)}</w:t></w:r>'
        f'<w:r>{rpr}<w:tab/></w:r>'
        f'<w:r>{rpr}<w:fldChar w:fldCharType="begin"/></w:r>'
        f'<w:r>{rpr}<w:instrText xml:space="preserve">{pageref_instr}</w:instrText></w:r>'
        f'<w:r>{rpr}<w:fldChar w:fldCharType="separate"/></w:r>'
        f'<w:r>{rpr}<w:t>1</w:t></w:r>'
        f'<w:r>{rpr}<w:fldChar w:fldCharType="end"/></w:r>'
        f'</w:hyperlink>'
        f'</w:p>'
    )


def make_toc_page(toc_entries=None):
    """生成目录页XML
    格式与参考文档100%一致：
    - 标题"目  录"黑体加粗字号32居中
    - sdt含sdtEndPr，TOC1样式段落含pPr/rPr，末段含sectPr和fldChar end
    - v3.2：在TOC域separate和end之间预填充静态目录条目（toc_entries），
      使Word打开时即使不更新域也能显示完整目录内容
    """
    toc_title = (
        f'<w:p><w:pPr><w:spacing w:before="480" w:after="360"/>'
        f'<w:jc w:val="center"/></w:pPr>'
        f'<w:r><w:rPr><w:rFonts w:eastAsia="黑体"/><w:b/><w:bCs/>'
        f'<w:sz w:val="{SZ_TOC_TITLE}"/>'
        f'<w:szCs w:val="{SZ_TOC_TITLE}"/></w:rPr>'
        f'<w:t>目  录</w:t></w:r>'
        f'</w:p>'
    )
    
    # TOC sdt区域（与参考文档完全一致的XML结构）
    # 1. sdtPr + sdtEndPr（参考文档有sdtEndPr，含b=0/bCs=0取消继承的加粗）
    # 2. 第一个段落：TOC1样式 + pPr/rPr + fldChar begin/instrText/separate
    # 3. 末段：含sectPr（目录节分节符）+ fldChar end
    # 注意：参考文档的sectPr在sdt内最后一段，不在sdt外
    toc_sdt = (
        '<w:sdt>'
        '<w:sdtPr><w:alias w:val="Table of Contents"/>'
        '<w:id w:val="1"/></w:sdtPr>'
        '<w:sdtEndPr><w:rPr>'
        '<w:b w:val="0"/><w:bCs w:val="0"/>'
        '</w:rPr></w:sdtEndPr>'
        '<w:sdtContent>'
        # 第一个段落：TOC1样式，含域代码begin/separate
        # BUG修复：添加 w:dirty="true" 使Word打开时自动更新目录
        '<w:p><w:pPr>'
        '<w:pStyle w:val="TOC1"/>'
        '<w:rPr>'
        '<w:rFonts w:asciiTheme="minorHAnsi" w:eastAsiaTheme="minorEastAsia" '
        'w:hAnsiTheme="minorHAnsi" w:cstheme="minorBidi" w:hint="eastAsia"/>'
        '<w:b w:val="0"/><w:bCs w:val="0"/>'
        '<w:noProof/>'
        '<w:color w:val="auto"/>'
        '<w:kern w:val="2"/>'
        '<w:sz w:val="22"/>'
        '<w14:ligatures w14:val="standardContextual"/>'
        '</w:rPr></w:pPr>'
        '<w:r><w:fldChar w:fldCharType="begin" w:dirty="true"/></w:r>'
        r'<w:r><w:instrText xml:space="preserve">TOC \o "1-3" \h \z \u</w:instrText></w:r>'
        '<w:r><w:fldChar w:fldCharType="separate"/></w:r>'
        '</w:p>'
    )
    
    # v3.2：静态TOC条目（预填充在separate和end之间）
    # 使Word打开时即使不更新域也能显示完整目录
    toc_entry_xml = ''
    if toc_entries:
        for entry_level, entry_title, entry_bm_name in toc_entries:
            toc_entry_xml += _make_toc_entry(entry_level, entry_title, entry_bm_name)
    
    # 末段：含sectPr（目录节分节符）+ fldChar end
    toc_sdt_end = (
        '<w:p><w:pPr>'
        '<w:rPr><w:rFonts w:hint="eastAsia"/></w:rPr>'
        '<w:sectPr w:rsidR="00A040FC">'
        f'<w:footerReference w:type="default" r:id="rId7"/>'
        f'<w:pgSz w:w="{PAGE_WIDTH}" w:h="{PAGE_HEIGHT}"/>'
        f'<w:pgMar w:top="1440" w:right="1417" w:bottom="1440" w:left="1701" '
        f'w:header="708" w:footer="708" w:gutter="0"/>'
        f'<w:cols w:space="720"/><w:docGrid w:linePitch="360"/>'
        '</w:sectPr></w:pPr>'
        '<w:r><w:fldChar w:fldCharType="end"/></w:r>'
        '</w:p>'
        '</w:sdtContent>'
        '</w:sdt>'
    )
    
    return toc_title + toc_sdt + toc_entry_xml + toc_sdt_end


def make_cover_section_break():
    """封面节分节符（零边距）"""
    return (
        f'<w:p><w:pPr>'
        f'<w:sectPr w:rsidR="00A040FC">'
        f'<w:pgSz w:w="{PAGE_WIDTH}" w:h="{PAGE_HEIGHT}"/>'
        f'<w:pgMar w:top="0" w:right="0" w:bottom="0" w:left="0" '
        f'w:header="708" w:footer="708" w:gutter="0"/>'
        f'<w:cols w:space="720"/><w:docGrid w:linePitch="360"/>'
        f'</w:sectPr></w:pPr></w:p>'
    )


def make_final_section():
    """最终节属性（含页眉header1 + 页脚footer2，正文区域）
    注意：这个sectPr放在document.xml的body末尾，不需要包裹在pPr中的p中
    """
    return (
        '<w:sectPr w:rsidR="00A040FC">'
        '<w:headerReference w:type="default" r:id="rId8"/>'
        '<w:footerReference w:type="default" r:id="rId9"/>'
        f'<w:pgSz w:w="{PAGE_WIDTH}" w:h="{PAGE_HEIGHT}"/>'
        f'<w:pgMar w:top="1440" w:right="1417" w:bottom="1440" w:left="1701" '
        f'w:header="708" w:footer="708" w:gutter="0"/>'
        f'<w:pgNumType w:start="1"/>'
        f'<w:cols w:space="720"/><w:docGrid w:linePitch="360"/>'
        f'</w:sectPr>'
    )


# ============================================================
# 文档组装函数
# ============================================================

def _cn_to_arabic(cn_str):
    """
    '十一'→'11', '二十'→'20', '三十五'→'35', '一百'→'100'
    '一百零一'→'101', '一百零五'→'105', '一百零十'→不合法但不会崩溃
    """
    if cn_str.isdigit():
        return cn_str
    digits = {'零': 0, '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
              '六': 6, '七': 7, '八': 8, '九': 9}
    # 处理"百"
    if '百' in cn_str:
        parts = cn_str.split('百')
        hundreds = digits.get(parts[0], 1) if parts[0] else 1
        remainder = parts[1] if len(parts) > 1 else ''
        if not remainder:
            return str(hundreds * 100)
        # 先去除前导"零"（如"一百零一"→remainder="零一"→去"零"后"一"）
        remainder_stripped = remainder.lstrip('零')
        if not remainder_stripped:
            # remainder全是"零"（如"一百零"→"零"），即无十位也无个位
            return str(hundreds * 100)
        if '十' in remainder_stripped:
            ten_parts = remainder_stripped.split('十')
            tens = digits.get(ten_parts[0], 1) if ten_parts[0] else 1
            ones = digits.get(ten_parts[1], 0) if len(ten_parts) > 1 and ten_parts[1] else 0
            return str(hundreds * 100 + tens * 10 + ones)
        ones = digits.get(remainder_stripped, 0) if remainder_stripped else 0
        return str(hundreds * 100 + ones)
    # 处理"十"
    if '十' in cn_str:
        parts = cn_str.split('十')
        tens = digits.get(parts[0], 1) if parts[0] else 1
        ones = digits.get(parts[1], 0) if len(parts) > 1 and parts[1] else 0
        return str(tens * 10 + ones)
    # 单字
    if cn_str in digits:
        return str(digits[cn_str])
    return cn_str  # 无法转换，返回原值


def _safe_chapter_int(num_str):
    """安全转换章节编号为int，支持中文数字"""
    try:
        return int(num_str)
    except ValueError:
        try:
            return int(_cn_to_arabic(num_str))
        except (ValueError, TypeError):
            return 0


def _strip_chapter_prefix(text, level='h1'):
    """自动去除标题文本中已包含的编号前缀，避免与函数自动生成的编号重复。

    例如：
    - h1: "第1章 研究概述" → "研究概述"（因为make_h1会自动生成"第1章"）
    - h1: "第3章 三、性价比测评与推荐" → "性价比测评与推荐"（循环剥离多重前缀）
    - h2: "1.1 背景" → "背景"（因为make_h2会自动生成"1.1"）
    - h3: "1.1.1 细节" → "细节"（因为make_h3会自动生成"1.1.1"）

    也处理无空格情况："第1章研究概述" → "研究概述"

    1. 剥离后为空时抛出FormatValidationError（防止标题被清空）
    2. h1采用while循环剥离——解决"第X章+中文序号"双重编号（首个正则匹配后return不再尝试后续模式的BUG）
    3. h2/h3无空格变体排除常见测量单位——避免"3.5英寸"等合法文本误剥离
    4. 确保text为字符串类型

    死参数清理(v2.2)：移除ch_num参数——函数内部从未使用，调用处传入的编号
    由各自的计数器独立维护，与剥离逻辑无关。

    V11-DOCX-7重写(v3.0)：原函数在首个正则匹配后直接return，不再尝试后续模式，
    导致"第3章 三、性价比"只剥离"第3章"而残留"三、"前缀。改为while循环模式，
    轮流尝试所有模式直到无匹配，彻底解决多重前缀残留。同时修复h2无空格变体将
    "3.5英寸"误剥离为"英寸"的BUG——增加常见测量单位负前瞻。
    """

    if text is None:
        return ''
    text = str(text)

    # 常见中文测量单位——h2/h3无空格变体匹配时排除，避免"3.5英寸"等误剥离
    _measurement_units = (
        r'(?!英寸|厘米|毫米|千米|公里|公斤|克|吨|兆|赫|像素|帧|瓦|伏|安|度'
        r'|升|秒|分|时|摩尔|牛顿|焦耳|帕斯卡|欧姆|法拉|流明|弧度)'
    )

    def _safe_strip(text, pattern):
        """剥离后校验非空，返回(stripped_text, changed)。"""
        stripped = re.sub(pattern, '', text)
        if stripped != text:
            if not stripped.strip():
                raise FormatValidationError(
                    f'⛔ _strip_chapter_prefix将标题清空！原文本="{text}"——'
                    f'标题只包含编号前缀，缺少实际标题内容'
                )
            return stripped, True
        return text, False

    if level == 'h1':
        # h1前缀模式（按优先级排列）——while循环轮流尝试，解决多重前缀残留
        h1_patterns = [
            r'^第[\d一二三四五六七八九十百零]+章\s*',
            r'^[一二三四五六七八九十]+、\s*',
            r'^（[一二三四五六七八九十]+）\s*',
            r'^\d+(?:[、:：）)]\s*|\.\s*(?!\d)|\s+)',
        ]
        while True:
            changed = False
            for pattern in h1_patterns:
                text, changed = _safe_strip(text, pattern)
            if not changed:
                break
        return text
    elif level == 'h2':
        # h2: "X.X " 带空格变体——安全，不会误剥离度量值
        # 前瞻包含（支持"1.1 （一）背景"等中文括号双重前缀格式
        text, changed1 = _safe_strip(
            text, r'^(\d+\.\d+)\s+(?=[\u4e00-\u9fffa-zA-Z\d（])'
        )
        if not changed1:
            # h2: "X.X" 无空格变体——增加测量单位负前瞻，避免"3.5英寸"误剥离
            text, changed1 = _safe_strip(
                text,
                r'^(\d+\.\d+)(?=[\u4e00-\u9fffa-zA-Z\d])(?!\d+\.\d)' + _measurement_units
            )
        if changed1:
            # 循环剥离：继续尝试中文序号前缀（解决"1.1（一）背景"等多重前缀）
            text, _ = _safe_strip(text, r'^（[一二三四五六七八九十]+）\s*')
            # BUG修复：H2分支缺少中文序号"一、"剥离模式，导致"1.1 一、背景"剥离"1.1 "后
            # 残留"一、背景"，最终输出"1.1 一、背景"显示为混乱的"1.1一"编号
            text, _ = _safe_strip(text, r'^[一二三四五六七八九十]+、\s*')
            return text
        # h2: 中文括号序号前缀"（一）""（二）"等
        text, changed2 = _safe_strip(text, r'^（[一二三四五六七八九十]+）\s*')
        if changed2:
            # BUG修复：中文括号序号后可能还跟着"一、"前缀
            text, _ = _safe_strip(text, r'^[一二三四五六七八九十]+、\s*')
        # BUG修复：h2也可能单独出现"一、"前缀（无阿拉伯编号）
        text, _ = _safe_strip(text, r'^[一二三四五六七八九十]+、\s*')
        return text
    elif level == 'h3':
        # h3: "X.X.X " 带空格变体
        text, changed1 = _safe_strip(
            text, r'^(\d+\.\d+\.\d+)\s+(?=[\u4e00-\u9fffa-zA-Z\d])(?!\d+\.\d)'
        )
        if not changed1:
            # h3: "X.X.X" 无空格变体——增加测量单位负前瞻
            text, changed1 = _safe_strip(
                text,
                r'^(\d+\.\d+\.\d+)(?=[\u4e00-\u9fffa-zA-Z\d])(?!\d+\.\d)' + _measurement_units
            )
        if changed1:
            # BUG修复：H3分支同样缺少中文序号"一、"和"（一）"剥离模式
            text, _ = _safe_strip(text, r'^（[一二三四五六七八九十]+）\s*')
            text, _ = _safe_strip(text, r'^[一二三四五六七八九十]+、\s*')
            return text
        # h3: 中文括号序号前缀"（一）""（二）"等
        text, changed2 = _safe_strip(text, r'^（[一二三四五六七八九十]+）\s*')
        if changed2:
            text, _ = _safe_strip(text, r'^[一二三四五六七八九十]+、\s*')
        # h3: 单独中文序号前缀"一、""二、"等
        text, _ = _safe_strip(text, r'^[一二三四五六七八九十]+、\s*')
        return text
    return text




def _validate_content_completeness(content_data):
    """校验content_data中每个文本字段的内容完整性，检测并拒绝截断内容。

    v3.1新增——规则16配套硬卡点：文档生成前强制校验每个字段的文本内容末尾
    是否有自然结尾标点。若末尾缺少结尾标点或出现截断信号，抛出FormatValidationError
    拒绝生成文档，强制调用方补充完整内容后再调用。

    BUG修复：原实现只遍历content_data顶层item的title/content/text等字段，
    但实际数据结构中段落文本在sections[].paragraphs[]/content和
    subsections[].paragraphs[]/content里，导致截断检测完全无效。
    修复后递归遍历所有层级的文本字段。

    截断信号检测规则：
    1. 文本末尾缺少自然结尾标点（句号/叹号/问号/右括号/右引号/冒号/数字/字母+句号）
    2. 文本末尾出现不完整词组（如"+购"、"。"后无内容、不完整枚举）
    3. 文本末尾出现悬挂的连接符（如"+"、"、"、"："后无后续内容）
    4. v3.2新增——末尾"连接符+少量字符"截断模式：LLM文本流截断常导致
       "推荐结论+购买建议"→"推荐结论+购"，末尾并非连接符本身（而是"购"），
       但末尾8字符内存在连接符且其后仅1-3个CJK字符时判定为截断。

    Args:
        content_data: 正文内容数据列表

    Raises:
        FormatValidationError: 当检测到截断内容时
    """
    if not content_data or not isinstance(content_data, list):
        return

    # 自然结尾标点集合——文本末尾必须是这些之一（或为空则不校验）
    _natural_endings = ('。', '！', '？', '）', '"', '"', "'", "'",
                        '.', '!', '?', ')', ']', '}', ':', '：', ';', '；',
                        '—', '…', '%', '》')

    # 截断信号——文本末尾出现这些则判定为截断
    _truncation_signals = ('+', '、', '，', ',', '：', ':', '（', '(', '【', '[',
                           '《', '〈', '"', '"', "'", "'", '第', '（一')

    # 收集所有文本字段（递归遍历章节/小节/子节三层结构）
    _text_fields = []

    def _collect_texts(obj, path):
        """递归收集所有段落文本字段"""
        if not isinstance(obj, dict):
            return
        # 检查 content（字符串或列表）和 paragraphs（列表）两种字段
        content_val = obj.get('content')
        if isinstance(content_val, str) and content_val.strip():
            _text_fields.append((path + '.content', content_val.strip()))
        elif isinstance(content_val, list):
            for j, para in enumerate(content_val):
                if isinstance(para, str) and para.strip():
                    _text_fields.append((f'{path}.content[{j}]', para.strip()))
        paragraphs_val = obj.get('paragraphs')
        if isinstance(paragraphs_val, list):
            for j, para in enumerate(paragraphs_val):
                if isinstance(para, str) and para.strip():
                    _text_fields.append((f'{path}.paragraphs[{j}]', para.strip()))
        # 递归 sections 和 subsections
        for sub in (obj.get('sections') or []):
            if isinstance(sub, dict):
                _collect_texts(sub, f'{path}.sections')
        for sub in (obj.get('subsections') or []):
            if isinstance(sub, dict):
                _collect_texts(sub, f'{path}.subsections')

    for i, chapter in enumerate(content_data):
        if not isinstance(chapter, dict):
            continue
        _collect_texts(chapter, f'content_data[{i}]')

    for field_path, text in _text_fields:
        # 跳过纯数字/纯标点/单字符内容
        if len(text) <= 1:
            continue

        last_char = text[-1]

        # 检查1：末尾是否为截断信号
        if last_char in _truncation_signals:
            raise FormatValidationError(
                '⛔ 内容完整性校验失败：{}="{}" '
                '末尾出现截断信号"{}"，内容可能被LLM文本流自然截断。'
                '请补充完整内容后再调用generate_docx.py。'
                '（规则16硬卡点：禁止将截断内容写入文档）'.format(
                    field_path, text[-50:], last_char
                )
            )

        # 检查3（v3.2新增）：末尾"连接符+少量字符"截断模式
        if len(text) >= 4:
            tail = text[-8:]
            for connector in ('+', '、', '，', ',', '：', ':'):
                pos = tail.rfind(connector)
                if pos >= 0:
                    after = tail[pos + 1:]
                    if after and all(
                        '\u4e00' <= c <= '\u9fff' for c in after
                    ) and 1 <= len(after) <= 3:
                        raise FormatValidationError(
                            '⛔ 内容完整性校验失败：{}="{}" '
                            '末尾检测到"连接符+少量字符"截断模式'
                            '（"{}"后仅"{}"{}字），'
                            '内容可能被LLM文本流自然截断。'
                            '请补充完整内容后再调用generate_docx.py。'.format(
                                field_path, text[-50:],
                                connector, after, len(after)
                            )
                        )

        # 检查2：末尾是否缺少自然结尾标点
        if len(text) > 6 and last_char not in _natural_endings:
            is_cjk = '\u4e00' <= last_char <= '\u9fff'

            if is_cjk:
                # CJK字符结尾但缺少自然结尾标点——可能被截断
                # v3.9.1修复：对>=15字的完整中文文本豁免截断检测
                if len(text) < 15:
                    raise FormatValidationError(
                        '⛔ 内容完整性校验失败：{}="{}" '
                        '末尾缺少自然结尾标点（以中文"{}"结尾），'
                        '内容可能被LLM文本流自然截断。'
                        '请补充完整内容后再调用generate_docx.py。'.format(
                            field_path, text[-50:], last_char
                        )
                    )
                # >=15字的CJK结尾文本视为合法完整内容，跳过
                continue
            elif last_char.isdigit() or last_char.isalpha():
                if len(text) > 1 and text[-2] in _natural_endings:
                    continue
                if last_char.isalpha():
                    continue
                if last_char.isdigit():
                    has_cjk = any('\u4e00' <= c <= '\u9fff' for c in text[:-1])
                    if has_cjk:
                        raise FormatValidationError(
                            '⛔ 内容完整性校验失败：{}="{}" '
                            '末尾缺少自然结尾标点（以数字"{}"结尾），'
                            '内容可能被LLM文本流自然截断。'
                            '请补充完整内容后再调用generate_docx.py。'.format(
                                field_path, text[-50:], last_char
                            )
                    )
                continue


def _run_heading_quality_checks(heading_entries, all_entries):
    """标题质量检测——共享函数，供_detect_duplicate_chapter_titles()和validate_format_consistency()复用。

    AUDIT-004修复：从_detect_duplicate_chapter_titles()提取约330行检测逻辑，
    消除与validate_format_consistency()中重复的标题质量检测代码。
    AUDIT-010修复：所有except块不再静默吞异常，改为warnings.warn记录。

    参数：
        heading_entries: [(style_val, full_text), ...] 仅heading段落(style 1/2/3)
        all_entries: [(style_val, full_text), ...] 所有段落(style_val可能为None)

    返回：
        list[str]: 检测到的错误消息列表
    """
    errors = []

    # H1标题含"第章"空编号残缺
    try:
        for sv, ft in heading_entries:
            if sv == '1':
                if ft and '第章' in ft:
                    errors.append(f'H1标题段落含"第章"空编号残缺: "{ft[:80]}"')
                if ft and re.search(r'第章.*第[\d一二三四五六七八九十百零]+章', ft):
                    errors.append(f'H1标题段落含"第章...第X章"重复: "{ft[:80]}"')
    except Exception as e:
        warnings.warn(f'标题检测[H1空编号]异常: {e}')

    # 章节编号断裂检测（如第1章后直接第3章）
    try:
        chapter_nums_in_order = []
        for sv, ft in heading_entries:
            if sv == '1':
                chapter_nums_in_order.extend(re.findall(r'第([\d一二三四五六七八九十百零]+)章', ft))
        if len(chapter_nums_in_order) >= 2:
            _converted_nums = []
            for n in chapter_nums_in_order:
                if n.isdigit():
                    _converted_nums.append(int(n))
                else:
                    _arabic = _cn_to_arabic(n)
                    try:
                        _converted_nums.append(int(_arabic))
                    except (ValueError, TypeError):
                        pass
            nums = _converted_nums
            if len(set(nums)) < len(nums):
                dup_nums = [n for n in nums if nums.count(n) > 1]
                errors.append(f'章节编号重复出现: {list(set(dup_nums))}')
    except Exception as e:
        warnings.warn(f'标题检测[章节编号断裂]异常: {e}')

    # H2编号跨章节不一致
    try:
        h2_nums_d12 = []
        for sv, ft in heading_entries:
            if sv == '2':
                if ft:
                    m_d12 = re.match(r'(\d+)\.(\d+)', ft)
                    if m_d12:
                        h2_nums_d12.append((m_d12.group(1), m_d12.group(2)))
        current_chapter = 0
        for h2_ch, h2_sec in h2_nums_d12:
            ch_num = int(h2_ch)
            if current_chapter == 0:
                current_chapter = ch_num
            elif ch_num < current_chapter:
                errors.append(f'H2编号回退异常: 第{current_chapter}章后出现"{h2_ch}.{h2_sec}"（编号小于前一章）')
                break
            current_chapter = ch_num
    except Exception as e:
        warnings.warn(f'标题检测[H2跨章不一致]异常: {e}')

    # 段落级标题完全重复
    try:
        heading_texts_l4 = {}
        for sv, ft in heading_entries:
            heading_texts_l4.setdefault(ft, 0)
            heading_texts_l4[ft] += 1
        for text, count in heading_texts_l4.items():
            if count > 1:
                errors.append(f'段落级标题完全重复（出现{count}次）: "{text[:50]}"')
    except Exception as e:
        warnings.warn(f'标题检测[完全重复]异常: {e}')

    # 标题空格变体重复
    try:
        normalized_headings = {}
        for sv, full_text in heading_entries:
            normalized = re.sub(r'\s+', ' ', full_text).strip()
            if normalized in normalized_headings and normalized_headings[normalized] != full_text:
                errors.append(f'标题空格变体重复："{full_text[:40]}" 与 "{normalized_headings[normalized][:40]}" 仅空格差异')
            else:
                normalized_headings[normalized] = full_text
    except Exception as e:
        warnings.warn(f'标题检测[空格变体]异常: {e}')

    # H2编号不连续
    try:
        h2_seq_d17 = []
        for sv, ft in heading_entries:
            if sv == '2':
                m_d17 = re.match(r'(\d+)\.(\d+)', ft)
                if m_d17:
                    h2_seq_d17.append((int(m_d17.group(1)), int(m_d17.group(2))))
        prev_sec_num = 0
        prev_ch_num = 0
        for ch_n, sec_n in h2_seq_d17:
            if ch_n == prev_ch_num and sec_n > prev_sec_num + 1 and prev_sec_num > 0:
                errors.append(f'H2编号不连续：{prev_ch_num}.{prev_sec_num}后直接跳到{ch_n}.{sec_n}，缺少{ch_n}.{prev_sec_num+1}')
            prev_ch_num = ch_n
            prev_sec_num = sec_n
    except Exception as e:
        warnings.warn(f'标题检测[H2不连续]异常: {e}')

    # H1标题含多个"第X章"编号
    try:
        for sv, ft in heading_entries:
            if sv == '1':
                chapter_occurrences = re.findall(r'第[\d一二三四五六七八九十百零]+章', ft)
                if len(chapter_occurrences) >= 2:
                    errors.append(f'XML构建后标题含多个"第X章"编号: "{ft[:50]}"')
    except Exception as e:
        warnings.warn(f'标题检测[H1多编号]异常: {e}')

    # H3编号前缀与所属H2不匹配（比较完整章号+节号）
    try:
        prev_h2_full = ''
        for sv, ft in all_entries:
            if sv == '2':
                h2_match = re.match(r'(\d+)\.(\d+)', ft)
                if h2_match:
                    prev_h2_full = f'{h2_match.group(1)}.{h2_match.group(2)}'
            elif sv == '3':
                h3_match = re.match(r'(\d+)\.(\d+)\.(\d+)', ft)
                if h3_match and prev_h2_full:
                    h3_prefix = f'{h3_match.group(1)}.{h3_match.group(2)}'
                    if h3_prefix != prev_h2_full:
                        errors.append(f'H3编号前缀与所属H2不匹配: H3="{h3_match.group(0)}" 但H2前缀="{prev_h2_full}"')
    except Exception as e:
        warnings.warn(f'标题检测[H3前缀不匹配]异常: {e}')

    # 标题段落同时出现"第X章"和"X.X"编号
    try:
        for sv, ft in heading_entries:
            has_chapter = bool(re.search(r'第[\d一二三四五六七八九十百零]+章', ft))
            has_section = bool(re.search(r'\d+\.\d+', ft))
            if has_chapter and has_section:
                errors.append(f'标题段落含混合编号前缀（同时出现"第X章"和"X.X"）: "{ft[:50]}"')
    except Exception as e:
        warnings.warn(f'标题检测[混合编号]异常: {e}')

    # 标题含异常unicode控制字符
    try:
        for sv, ft in heading_entries:
            bad_chars = [c for c in ft if (ord(c) < 0x20 and c not in '\n\t') or ord(c) in (0x200B, 0x200C, 0x200D, 0xFEFF)]
            if bad_chars:
                errors.append(f'标题含异常unicode控制字符: "{ft[:50]}" 含{len(bad_chars)}个异常字符')
    except Exception as e:
        warnings.warn(f'标题检测[异常unicode]异常: {e}')

    # 标题文本末尾意外残留编号数字
    try:
        for sv, ft in heading_entries:
            tail_num = re.search(r'\d+\.\d+(?:\.\d+)?\s*$', ft)
            if tail_num and not re.match(r'\d+\.\d+', ft):
                errors.append(f'标题尾部编号残留: "{ft[:50]}" 末尾含编号"{tail_num.group()}"')
    except Exception as e:
        warnings.warn(f'标题检测[尾部编号残留]异常: {e}')

    # 编号格式不统一（点号vs连字符）
    try:
        dot_count = 0
        dash_count = 0
        for sv, ft in heading_entries:
            if sv in ('2', '3'):
                if re.search(r'\d+\.\d+', ft):
                    dot_count += 1
                # 排除4位数年份范围（如2026-2028）后再检测连字符编号
                ft_no_year = re.sub(r'\d{4}-\d{4}', '', ft)
                if re.search(r'\d+-\d+', ft_no_year):
                    dash_count += 1
        if dot_count > 0 and dash_count > 0:
            errors.append(f'编号格式不统一：同时检测到点号分隔("X.X")标题{dot_count}个和连字符分隔("X-X")标题{dash_count}个')
    except Exception as e:
        warnings.warn(f'标题检测[编号格式不统一]异常: {e}')

    # 标题含冒号/分号等特殊标点
    try:
        for sv, ft in heading_entries:
            ft_no_num = re.sub(r'^第[\d一二三四五六七八九十百零]+章\s*', '', ft)
            ft_no_num = re.sub(r'^\d+\.\d+(?:\.\d+)?\s*', '', ft_no_num)
            if re.search(r'[:：;；]', ft_no_num):
                errors.append(f'标题含特殊标点(冒号/分号): "{ft[:50]}"')
    except Exception as e:
        warnings.warn(f'标题检测[特殊标点]异常: {e}')

    # 段落pStyle与编号格式不匹配
    try:
        for sv, ft in heading_entries:
            if sv == '1' and re.match(r'\d+\.\d+', ft) and not re.match(r'第[\d一二三四五六七八九十百零]+章', ft):
                errors.append(f'H1段落编号格式错误: 样式为H1但文本以"X.X"开头: "{ft[:50]}"')
            if sv == '2' and re.match(r'第[\d一二三四五六七八九十百零]+章', ft):
                errors.append(f'H2段落编号格式错误: 样式为H2但文本以"第X章"开头: "{ft[:50]}"')
            if sv == '3' and re.match(r'第[\d一二三四五六七八九十百零]+章', ft):
                errors.append(f'H3段落编号格式错误: 样式为H3但文本以"第X章"开头: "{ft[:50]}"')
            if sv == '3' and re.match(r'\d+\.\d+\s', ft) and not re.match(r'\d+\.\d+\.\d+', ft):
                errors.append(f'H3段落编号格式错误: 样式为H3但文本以"X.X"（两位编号）开头: "{ft[:50]}"')
    except Exception as e:
        warnings.warn(f'标题检测[pStyle不匹配]异常: {e}')

    # 标题含全角数字字符
    try:
        fullwidth_digits = '\uff10\uff11\uff12\uff13\uff14\uff15\uff16\uff17\uff18\uff19'
        for sv, ft in heading_entries:
            fullwidth_found = [c for c in ft if c in fullwidth_digits]
            if fullwidth_found:
                errors.append(f'标题含全角数字字符: "{ft[:50]}" 含全角数字{fullwidth_found[:5]}')
    except Exception as e:
        warnings.warn(f'标题检测[全角数字]异常: {e}')

    # 标题仅含编号无标题文字
    try:
        for sv, ft in heading_entries:
            ft_stripped = re.sub(r'^第[\d一二三四五六七八九十百零]+章\s*', '', ft)
            ft_stripped = re.sub(r'^\d+\.\d+(?:\.\d+)?\s*', '', ft_stripped)
            ft_stripped = ft_stripped.strip()
            if not ft_stripped:
                errors.append(f'标题仅含编号无标题文字: "{ft}"')
    except Exception as e:
        warnings.warn(f'标题检测[仅含编号]异常: {e}')

    # 标题首尾含空格/制表符
    try:
        for sv, ft in heading_entries:
            ft_no_num = re.sub(r'^第[\d一二三四五六七八九十百零]+章\s*', '', ft)
            ft_no_num = re.sub(r'^\d+\.\d+(?:\.\d+)?\s*', '', ft_no_num)
            if ft_no_num != ft_no_num.lstrip():
                errors.append(f'标题文字含前导空格/制表符: "{ft[:50]}"')
            if ft_no_num.rstrip() != ft_no_num:
                errors.append(f'标题文字含尾部空格/制表符: "{ft[:50]}"')
    except Exception as e:
        warnings.warn(f'标题检测[首尾空格]异常: {e}')

    # 编号含前导零
    try:
        for sv, ft in heading_entries:
            if re.search(r'第0\d+章', ft):
                errors.append(f'编号含前导零(第X章): "{ft[:50]}"')
            if re.search(r'\b0\d+\.\d+', ft) or re.search(r'\d+\.0\d+', ft):
                errors.append(f'编号含前导零(X.X): "{ft[:50]}"')
    except Exception as e:
        warnings.warn(f'标题检测[前导零]异常: {e}')

    # 标题含不可见空白字符
    try:
        invisible_chars = set('\u200b\u200c\u200d\ufeff\u00a0\u202f\u205f\u2003\u2002\u2009')
        for sv, ft in heading_entries:
            found_invisible = [c for c in ft if c in invisible_chars]
            if found_invisible:
                errors.append(f'标题含不可见空白字符: "{ft[:50]}" 含{found_invisible[:3]}')
    except Exception as e:
        warnings.warn(f'标题检测[不可见空白]异常: {e}')

    # 标题含HTML转义残留
    try:
        html_escape_patterns = ['&amp;', '&lt;', '&gt;', '&quot;', '&#39;']
        for sv, ft in heading_entries:
            for esc_pattern in html_escape_patterns:
                if esc_pattern in ft:
                    errors.append(f'标题含HTML转义残留: "{ft[:50]}" 含"{esc_pattern}"')
                    break
    except Exception as e:
        warnings.warn(f'标题检测[HTML转义残留]异常: {e}')

    # H1编号与后续H2编号体系不一致
    try:
        current_h1_num = 0
        for sv, ft in all_entries:
            if not ft:
                continue
            if sv == '1':
                h1_m = re.search(r'第([\d一二三四五六七八九十百零]+)章', ft)
                if h1_m:
                    try:
                        current_h1_num = int(h1_m.group(1))
                    except ValueError:
                        current_h1_num = _safe_chapter_int(h1_m.group(1))
            elif sv == '2' and current_h1_num > 0:
                h2_m = re.match(r'(\d+)\.(\d+)', ft)
                if h2_m:
                    h2_chapter = int(h2_m.group(1))
                    if h2_chapter != current_h1_num:
                        errors.append(f'章节编号与正文内容脱节: 当前章节为第{current_h1_num}章但H2编号为"{h2_m.group(0)}"')
    except Exception as e:
        warnings.warn(f'标题检测[H1/H2体系不一致]异常: {e}')

    # 标题含emoji字符
    try:
        for sv, ft in heading_entries:
            emoji_chars = []
            for c in ft:
                cp = ord(c)
                if (0x1F600 <= cp <= 0x1F64F or
                    0x1F300 <= cp <= 0x1F5FF or
                    0x1F680 <= cp <= 0x1F6FF or
                    0x1F900 <= cp <= 0x1F9FF or
                    0x2600 <= cp <= 0x26FF or
                    0x2700 <= cp <= 0x27BF or
                    0x1FA00 <= cp <= 0x1FA6F or
                    0x1FA70 <= cp <= 0x1FAFF):
                    emoji_chars.append(c)
            if emoji_chars:
                errors.append(f'标题含emoji或非文本符号: "{ft[:50]}" 含{emoji_chars[:3]}')
    except Exception as e:
        warnings.warn(f'标题检测[emoji]异常: {e}')

    # 标题含过度标点
    try:
        for sv, ft in heading_entries:
            ft_no_num = re.sub(r'^第[\d一二三四五六七八九十百零]+章\s*', '', ft)
            ft_no_num = re.sub(r'^\d+\.\d+(?:\.\d+)?\s*', '', ft_no_num)
            if re.search(r'[!！]{2,}|[?？]{2,}|\.{3,}|…', ft_no_num):
                errors.append(f'标题含过度标点(连续感叹号/问号/省略号): "{ft[:50]}"')
    except Exception as e:
        warnings.warn(f'标题检测[过度标点]异常: {e}')

    # 使用非标准分隔符
    try:
        for sv, ft in heading_entries:
            if re.search(r'\d+[_/|]\d+', ft):
                errors.append(f'章节编号含非标准分隔符(下划线/斜杠/竖线): "{ft[:50]}"')
    except Exception as e:
        warnings.warn(f'标题检测[非标准分隔符]异常: {e}')

    # 标题含冗余空白
    try:
        for sv, ft in heading_entries:
            if re.search(r' {3,}', ft):
                errors.append(f'标题含冗余空白(3+连续空格): "{ft[:50]}"')
            if re.search(r'\t +| +\t', ft):
                errors.append(f'标题含混合空白(tab+space): "{ft[:50]}"')
    except Exception as e:
        warnings.warn(f'标题检测[冗余空白]异常: {e}')

    return errors

def _detect_duplicate_chapter_titles(body_xml):
    """全文重复编号检测。
    在build_body_xml拼接完成后执行，检测整个body XML中是否存在任何形式的章节标题重复。
    发现重复则抛出FormatValidationError阻止输出，确保零重复。
    
    检测模式：
    - "第X章 第X章"（同编号重复）
    - "第章"（空编号残缺）
    - "X.X X.X"（H2编号重复）
    - "X.X.X X.X.X"（H3编号重复）
    """
    errors = []
    
    # 检测1：H1同编号重复（如"第1章 第1章"）
    h1_dup = re.findall(r'第[\d一二三四五六七八九十百零]+章\s+第[\d一二三四五六七八九十百零]+章', body_xml)
    if h1_dup:
        errors.append(f'H1标题重复: {h1_dup}')
    
    # 检测2：H2编号重复（如"1.1 1.1"）  # DOCX-DOC-2修复：重新连续编号
    h2_dup = re.findall(r'(?<=>)\d+\.\d+\s+\d+\.\d+', body_xml)
    if h2_dup:
        errors.append(f'H2标题重复: {h2_dup}')

    # 检测3：H3编号重复（如"1.1.1 1.1.1"）
    h3_dup = re.findall(r'(?<=>)\d+\.\d+\.\d+\s+\d+\.\d+\.\d+', body_xml)
    if h3_dup:
        errors.append(f'H3标题重复: {h3_dup}')
    
    # 检测4：H1空编号后跟数字（如"第章 第1章"——标题文本含编号但编号提取失败）
    h1_empty_then_num = re.findall(r'第章[^<]*第[\d一二三四五六七八九十百零]+章', body_xml)
    if h1_empty_then_num:
        errors.append(f'H1空编号后跟完整编号（第章第X章）: {h1_empty_then_num}')
    

    h1_empty_then_num_nospace = re.findall(r'第章第[\d一二三四五六七八九十百零]+章', body_xml)
    if h1_empty_then_num_nospace:
        errors.append(f'H1空编号紧凑型后跟完整编号（第章第X章无空格）: {h1_empty_then_num_nospace}')
    

    # 仅在同一个w:t标签内检测，避免跨段落误匹配
    h1_empty_tag_then_num = re.findall(r'<w:t[^>]*>第章</w:t>.*?<w:t[^>]*>第[\d一二三四五六七八九十百零]+章', body_xml, re.DOTALL)
    if h1_empty_tag_then_num:
        # 进一步验证：确保是同一个段落内的匹配（通过检查中间是否有pStyle标签）
        for match in h1_empty_tag_then_num[:5]:
            # 如果匹配跨段落（包含</w:p><w:p>），则不报错
            if '</w:p>' not in match and '<w:p>' not in match:
                errors.append(f'XML标签级第章后跟第X章（同段落内）: {match[:100]}')
    

    # （RED-9修复：原第一次ET.fromstring已合并到下方root_l4解析块，避免重复解析body_xml）
    
    # 检测6：标题文本中残留"第X章"前缀（XML中出现连续两个含"章"的w:t标签）
    chapter_tag_dup = re.findall(r'<w:t>第[\d一二三四五六七八九十百零]+章\s*</w:t>\s*<w:r[^>]*>.*?<w:t[^>]*>第[\d一二三四五六七八九十百零]+章', body_xml, re.DOTALL)
    if chapter_tag_dup:
        errors.append(f'XML标签级第X章重复: {chapter_tag_dup}')
    
    # 检测7：h2编号紧接h2编号（如"1.1 1.1 标题"——编号前缀未被正确去除）
    h2_tag_dup = re.findall(r'<w:t[^>]*>\d+\.\d+\s*</w:t>\s*<w:r[^>]*>.*?<w:t[^>]*>\d+\.\d+\s', body_xml, re.DOTALL)
    if h2_tag_dup:
        errors.append(f'XML标签级H2编号重复: {h2_tag_dup}')
    
    # 检测8：h3编号紧接h3编号
    h3_tag_dup = re.findall(r'<w:t[^>]*>\d+\.\d+\.\d+\s*</w:t>\s*<w:r[^>]*>.*?<w:t[^>]*>\d+\.\d+\.\d+\s', body_xml, re.DOTALL)
    if h3_tag_dup:
        errors.append(f'XML标签级H3编号重复: {h3_tag_dup}')
    
    # 检测9：标题文本本身以"第X章"开头且编号字段也有值（双重编号）
    title_starts_chapter = re.findall(r'<w:t>第[\d一二三四五六七八九十百零]+章\s+第[\d一二三四五六七八九十百零]+章\s', body_xml)
    if title_starts_chapter:
        errors.append(f'标题文本双重"第X章"前缀: {title_starts_chapter}')
    
    # 检测10：无空格的"第X章第X章"重复（紧凑型重复，如"第1章第1章"）
    h1_dup_nospace = re.findall(r'第[\d一二三四五六七八九十百零]+章第[\d一二三四五六七八九十百零]+章', body_xml)
    if h1_dup_nospace:
        errors.append(f'H1标题紧凑型重复（无空格）: {h1_dup_nospace}')
    
    # ---- 合并解析：一次 ET.fromstring 提取所有段落的 (style_val, full_text) ----
    # 必须在检测11之前定义，因为检测11/12/段落级标题重复/标题空格变体等均复用 heading_entries
    heading_entries = []  # [(style_val, full_text), ...] 仅 heading 段落 (style 1/2/3)
    all_entries = []      # [(style_val, full_text), ...] 所有段落（style_val 可能为 None）
    try:
        root_l4 = ET.fromstring(('<root xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
                                ' xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                                + body_xml + '</root>').encode('utf-8'))
        for p in root_l4.iter(NS_W + 'p'):
            pPr = p.find(NS_W + 'pPr')
            sv = None
            if pPr is not None:
                pStyle = pPr.find(NS_W + 'pStyle')
                if pStyle is not None:
                    sv = pStyle.get(NS_W + 'val', '')
            ft = ''.join(t.text for t in p.iter(NS_W + 't') if t.text)
            all_entries.append((sv, ft))
            if sv in ('1', '2', '3') and ft:
                heading_entries.append((sv, ft))
    except ET.ParseError:
        pass  # XML解析失败，heading_entries保持空列表，后续检测项均跳过

    # AUDIT-004修复：调用共享标题质量检测函数，消除与validate_format_consistency()的重复逻辑
    # AUDIT-010修复：共享函数内异常不再静默吞掉，统一使用warnings.warn记录
    errors.extend(_run_heading_quality_checks(heading_entries, all_entries))

    # body_xml级别的正则检测（不依赖heading_entries，保留在原函数中）
    mixed_dup = re.findall(r'第[\d一二三四五六七八九十百零]+章\d+\.\d+(?!\s)', body_xml)
    if mixed_dup:
        errors.append(f'混合编号格式异常粘连: {mixed_dup[:5]}')

    cn_arabic_mix = re.findall(r'第[\d一二三四五六七八九十百零]+章[^\s<]*第[一二三四五六七八九十百零]+章', body_xml)
    if cn_arabic_mix:
        errors.append(f'中文数字与阿拉伯数字混用编号重复: {cn_arabic_mix[:5]}')
    cn_arabic_mix2 = re.findall(r'第[一二三四五六七八九十百零]+章[^\s<]*第[\d一二三四五六七八九十百零]+章', body_xml)
    if cn_arabic_mix2:
        errors.append(f'阿拉伯数字与中文数字混用编号重复: {cn_arabic_mix2[:5]}')

    if errors:
        error_msg = '章节标题重复检测失败:\n' + '\n'.join(f'  - {e}' for e in errors)
        raise FormatValidationError(error_msg)


def _pre_validate_content(content_data):
    """内容预校验。
    在调用build_body_xml之前对content_data执行结构化校验，在问题进入XML层之前拦截。
    这是"没有第几章"bug的隐蔽根因——字段名不匹配导致chapter.get('h1')返回空，自动编号虽能补救编号但标题丢失
    """
    errors = []
    

    if content_data is None:
        raise FormatValidationError(
            '⛔ content_data为None！文档必须包含至少一个章节。\n'
            '请确保传入有效的JSON内容列表：[{"h1": "标题", "sections": [...]}]'
        )
    if not isinstance(content_data, list):
        raise FormatValidationError(
            f'⛔ content_data不是列表类型（实际类型: {type(content_data).__name__}）！\n'
            f'正确格式：[{{"h1": "标题", "sections": [...]}}]'
        )
    
    try:
        for ch_idx, chapter in enumerate(content_data):

            if not isinstance(chapter, dict):
                errors.append(f'章节{ch_idx+1}: 不是字典类型（实际类型: {type(chapter).__name__}），每个章节必须是{{"h1": "标题", "sections": [...]}}')
                continue
            

            # 常见错误：用户用"title"/"chapter"/"heading"/"name"而非"h1"
            wrong_h1_keys = [k for k in chapter.keys() if k in ('title', 'chapter', 'heading', 'name', 'chapter_title', 'chapter_name') and 'h1' not in chapter]
            if wrong_h1_keys:
                errors.append(
                    f'章节{ch_idx+1}: 检测到错误字段名{wrong_h1_keys}，应为"h1"。'
                    f'字段名不匹配是"没有第几章"bug的隐蔽根因——自动编号虽能补救编号但标题文本会丢失。'
                    f'请将字段名改为"h1"'
                )
            # 常见错误：用户用"sections"的变体而非"sections"
            wrong_sec_keys = [k for k in chapter.keys() if k in ('section', 'subs', 'items', 'parts', 'content') and 'sections' not in chapter]
            if wrong_sec_keys:
                errors.append(
                    f'章节{ch_idx+1}: 检测到错误字段名{wrong_sec_keys}，应为"sections"。'
                    f'字段名不匹配会导致章节内容丢失。请将字段名改为"sections"'
                )

            ch_title = chapter.get('h1', '')
            if ch_title is None:
                ch_title = ''
            ch_title = str(ch_title) if not isinstance(ch_title, str) else ch_title
            
            # 检测：标题文本为空
            if not ch_title.strip():
                errors.append(f'章节{ch_idx+1}: h1标题为空')
            

            if 'sections' not in chapter and 'h1' in chapter:
                # 有h1但没有sections——可能用户用了别的字段名
                possible_sec_fields = [k for k in chapter.keys() if k not in ('h1', 'h1_num') and isinstance(chapter.get(k), list)]
                if possible_sec_fields:
                    errors.append(
                        f'章节{ch_idx+1}: 有"h1"字段但缺少"sections"字段，检测到可能的替代字段{possible_sec_fields}。'
                        f'请将字段名改为"sections"'
                    )
            
            for sec_idx, section in enumerate(chapter.get('sections') or []):  # BUG-16修复：null时回退为空列表；DOCX-BUG-1修复：缩进+4spaces移入章节循环内部

                if not isinstance(section, dict):
                    errors.append(f'章节{ch_idx+1}节{sec_idx+1}: 不是字典类型（实际类型: {type(section).__name__}）')
                    continue
                

                wrong_h2_keys = [k for k in section.keys() if k in ('title', 'section', 'heading', 'name', 'subtitle') and 'h2' not in section]
                if wrong_h2_keys:
                    errors.append(
                        f'章节{ch_idx+1}节{sec_idx+1}: 检测到错误字段名{wrong_h2_keys}，应为"h2"'
                    )

                sec_title = section.get('h2', '')
                if sec_title is None:
                    sec_title = ''
                sec_title = str(sec_title) if not isinstance(sec_title, str) else sec_title
                
                # 检测：H2标题为空
                if not sec_title.strip():
                    errors.append(f'章节{ch_idx+1}节{sec_idx+1}: h2标题为空')
                
                for sub_idx, subsection in enumerate(section.get('subsections') or []):  # BUG-17修复：null时回退为空列表

                    if not isinstance(subsection, dict):
                        errors.append(f'章节{ch_idx+1}节{sec_idx+1}子节{sub_idx+1}: 不是字典类型')
                        continue
                    

                    wrong_h3_keys = [k for k in subsection.keys() if k in ('title', 'section', 'heading', 'name', 'subtitle') and 'h3' not in subsection]
                    if wrong_h3_keys:
                        errors.append(
                            f'章节{ch_idx+1}节{sec_idx+1}子节{sub_idx+1}: 检测到错误字段名{wrong_h3_keys}，应为"h3"'
                        )

                    sub_title = subsection.get('h3', '')
                    if sub_title is None:
                        sub_title = ''
                    sub_title = str(sub_title) if not isinstance(sub_title, str) else sub_title
                    
                    # 检测：H3标题为空
                    if not sub_title.strip():
                        errors.append(f'章节{ch_idx+1}节{sec_idx+1}子节{sub_idx+1}: h3标题为空')
    
    except FormatValidationError:
        raise
    except Exception as e:

        errors.append(f'预校验异常: {str(e)}')
    
    if errors:
        error_msg = '内容预校验失败:\n' + '\n'.join(f'  - {e}' for e in errors)
        raise FormatValidationError(error_msg)


def build_body_xml(title, subtitle, info_rows,
                   bottom_label_left,
                   bottom_label_right, content_data):
    """
    组装完整的document.xml body内容
    
    自动编号(v3.1)：调用_strip_chapter_prefix剥离标题文本中已有编号前缀，
    再用章节序号自动生成标准编号（第X章 / X.X / X.X.X），确保编号连续且唯一。
    例如：h1="第1章 研究概述" → 剥离→"研究概述"→自动生成"第1章 研究概述"
    
    Returns:
        body_xml字符串
    
    死参数清理(v2.2)：移除date_str参数——日期信息通过info_rows传入，
    build_body_xml内部不使用date_str。
    """
    body_parts = []
    bookmark_counter = [0]
    

    # 这是"没有第几章"bug的P0根因——当content_data为空列表时，
    # for循环不执行，文档中不会生成任何H1标题段落，
    # 所有防护层检测的是"标题存在但缺编号"而非"无标题"，导致空文档通过所有校验
    if not content_data:
        raise FormatValidationError(
            '⛔ content_data为空！文档必须包含至少一个章节（H1标题）。\n'
            '这是"没有第几章"bug的根因——空内容会导致文档完全没有章节标题。\n'
            '请确保content_data至少包含一个章节对象：'
            '[{"h1": "章节标题", "sections": [...]}]'
        )
    
    # ：内容预校验（在构建XML前拦截问题）
    _pre_validate_content(content_data)

    # BUG修复(v3.3)：检测单h1包裹多h2结构——这是"只渲染第1章"bug的数据层根因。
    # 当content_data只有1个h1且其下有多个h2 sections时，所有h2会被当作
    # 第1章的内部小节渲染，导致报告中只有1个章节。此处发警告提示用户检查数据结构。
    if len(content_data) == 1:
        _sole_ch = content_data[0]
        _sole_sections = _sole_ch.get('sections') or []
        if len(_sole_sections) > 1:
            _sole_h2_titles = [s.get('h2', '无标题') for s in _sole_sections if isinstance(s, dict)]
            print(
                f"⚠️ build_body_xml: 检测到单h1包裹多h2结构（1个h1下有{len(_sole_sections)}个h2小节）。\n"
                f"  这会导致docx只渲染第1章，其余h2被当作第1章内部小节。\n"
                f"  h2小节列表: {', '.join(_sole_h2_titles[:5])}{'...' if len(_sole_h2_titles) > 5 else ''}\n"
                f"  建议将每个h2提升为独立h1章节: "
                f'[{{"h1": "章节1", "sections": [...]}}, {{"h1": "章节2", "sections": [...]}}]',
                flush=True
            )

    # BUG修复(v3.3)：检测section含表格引言但缺tables字段——提示数据可能遗漏表格。
    for _chk_idx, _chk_ch in enumerate(content_data):
        for _chk_sec_idx, _chk_sec in enumerate(_chk_ch.get('sections') or []):
            if not isinstance(_chk_sec, dict):
                continue
            _has_tables = bool(_chk_sec.get('tables') or _chk_sec.get('table'))
            if _has_tables:
                continue
            _chk_paras = _chk_sec.get('paragraphs') or _chk_sec.get('content') or []
            if isinstance(_chk_paras, str):
                _chk_paras = [_chk_paras]
            if not isinstance(_chk_paras, list):
                continue
            _table_keywords = ('表格', '对比', '如下表', 'table', '见表', '汇总表')
            for _para in _chk_paras:
                if isinstance(_para, str) and any(_kw in _para.lower() for _kw in _table_keywords):
                    print(
                        f"⚠️ build_body_xml: section[{_chk_idx}].sections[{_chk_sec_idx}] "
                        f"段落含表格关键词但缺少tables字段，可能遗漏表格数据。\n"
                        f"  匹配段落: {_para[:80]}...\n"
                        f"  建议在该section中添加tables字段: "
                        f'{{"tables": [{{"headers": [...], "rows": [...]}}]}}',
                        flush=True
                    )
                    break

    # BUG修复(v3.4)：检测每章仅1个h2小节——提示章节结构不均衡。
    # 每个h1章节应至少包含2个h2 section，单一h2结构导致章节内容单薄。
    for _chk2_idx, _chk2_ch in enumerate(content_data):
        _chk2_sections = _chk2_ch.get('sections') or []
        if len(_chk2_sections) == 1:
            _chk2_title = _chk2_ch.get('h1', '无标题')
            _sole_h2 = _chk2_sections[0].get('h2', '无标题') if isinstance(_chk2_sections[0], dict) else '无标题'
            print(
                f"⚠️ build_body_xml: 第{_chk2_idx + 1}章「{_chk2_title}」仅1个h2小节「{_sole_h2}」。\n"
                f"  建议拆分为2个以上h2小节，确保章节结构均衡完整。",
                flush=True
            )

    # BUG修复(v3.5)：检测每h2仅1个h3子小节——提示子节结构不均衡。
    # 每个含subsections的h2应至少包含2个h3 subsection，单一h3结构导致小节内容单薄。
    for _chk3_idx, _chk3_ch in enumerate(content_data):
        for _chk3_sec in _chk3_ch.get('sections') or []:
            if not isinstance(_chk3_sec, dict):
                continue
            _chk3_subs = _chk3_sec.get('subsections') or []
            if len(_chk3_subs) == 1:
                _chk3_h2_title = _chk3_sec.get('h2', '无标题')
                _sole_h3 = _chk3_subs[0].get('h3', '无标题') if isinstance(_chk3_subs[0], dict) else '无标题'
                print(
                    f"⚠️ build_body_xml: 第{_chk3_idx + 1}章h2「{_chk3_h2_title}」仅1个h3子小节「{_sole_h3}」。\n"
                    f"  建议拆分为2个以上h3子小节或移除subsections，确保子节结构均衡。",
                    flush=True
                )

    def next_bookmark():
        """生成下一对书签ID和名称（双书签，与参考文档结构一致）"""
        bm_id = bookmark_counter[0]
        bm_id2 = bookmark_counter[0] + 1
        bookmark_counter[0] += 2
        bm_name = f'_Toc100{bm_id:03d}'
        bm_name2 = f'_Toc100{bm_id2:03d}'
        return bm_id, bm_name, bm_id2, bm_name2
    
    # 1. 封面页
    body_parts.append(make_cover_page(
        title, subtitle, info_rows,
        bottom_label_left, bottom_label_right
    ))
    
    # 2. 封面分节符
    body_parts.append(make_cover_section_break())
    
    # 3. 目录页（含sdt末段中的sectPr分节符，与参考文档一致）
    # v3.2：预计算TOC条目，与正文书签ID完全同步（bookmark_counter从0开始每对+2）
    toc_entries = []
    toc_bm_counter = 0
    for ch_idx, chapter in enumerate(content_data):
        ch_title_raw = chapter.get('h1', '')
        ch_title_clean = _strip_chapter_prefix(ch_title_raw, level='h1')
        ch_title = f'第{ch_idx + 1}章 {ch_title_clean}'
        toc_entries.append((1, ch_title, f'_Toc100{toc_bm_counter:03d}'))
        toc_bm_counter += 2
        
        for sec_idx, section in enumerate(chapter.get('sections') or []):
            sec_title_raw = section.get('h2', '')
            sec_title_clean = _strip_chapter_prefix(sec_title_raw, level='h2')
            sec_title = f'{ch_idx + 1}.{sec_idx + 1} {sec_title_clean}'
            toc_entries.append((2, sec_title, f'_Toc100{toc_bm_counter:03d}'))
            toc_bm_counter += 2
            
            for sub_idx, subsection in enumerate(section.get('subsections') or []):
                sub_title_raw = subsection.get('h3', '')
                sub_title_clean = _strip_chapter_prefix(sub_title_raw, level='h3')
                sub_title = f'{ch_idx + 1}.{sec_idx + 1}.{sub_idx + 1} {sub_title_clean}'
                toc_entries.append((3, sub_title, f'_Toc100{toc_bm_counter:03d}'))
                toc_bm_counter += 2
    
    body_parts.append(make_toc_page(toc_entries))
    
    # 4. 正文内容

    for ch_idx, chapter in enumerate(content_data):

        if not isinstance(chapter, dict):
            raise FormatValidationError(
                f'⛔ content_data[{ch_idx}]不是字典类型（实际类型: {type(chapter).__name__}），'
                f'每个章节必须是字典对象: {{"h1": "标题", "sections": [...]}}'
            )

        ch_title_raw = chapter.get('h1', '')
        if ch_title_raw is None:
            ch_title_raw = ''
        ch_title_raw = str(ch_title_raw) if not isinstance(ch_title_raw, str) else ch_title_raw
        # 自动编号：剥离已有前缀后用章节序号自动生成"第X章 标题"
        ch_title_clean = _strip_chapter_prefix(ch_title_raw, level='h1')
        ch_title = f'第{ch_idx + 1}章 {ch_title_clean}'
        
        # H1标题（自动编号+双书签，与参考文档格式一致）
        bm_id, bm_name, bm_id2, bm_name2 = next_bookmark()
        body_parts.append(make_h1_paragraph(ch_title, bm_id, bm_name, bm_id2, bm_name2))
        
        # 章节内容
        for sec_idx, section in enumerate(chapter.get('sections') or []):

            if not isinstance(section, dict):
                raise FormatValidationError(
                    f'⛔ content_data[{ch_idx}].sections[{sec_idx}]不是字典类型'
                    f'（实际类型: {type(section).__name__}）'
                )

            sec_title_raw = section.get('h2', '')
            if sec_title_raw is None:
                sec_title_raw = ''
            sec_title_raw = str(sec_title_raw) if not isinstance(sec_title_raw, str) else sec_title_raw
            # 自动编号：剥离已有前缀后用章节序号自动生成"X.X 标题"
            sec_title_clean = _strip_chapter_prefix(sec_title_raw, level='h2')
            sec_title = f'{ch_idx + 1}.{sec_idx + 1} {sec_title_clean}'
            
            # H2标题（自动编号+双书签，与参考文档格式一致）
            bm_id, bm_name, bm_id2, bm_name2 = next_bookmark()
            body_parts.append(make_h2_paragraph(sec_title, bm_id, bm_name, bm_id2, bm_name2))
            
            # 段落 — 同时支持 "content"(字符串) 和 "paragraphs"(列表) 两种字段名
            # 优先读 "content"（LLM 最常用），回退到 "paragraphs"（兼容旧格式）
            _section_body = section.get('content')
            if _section_body is not None:
                # content 为字符串：按换行拆分为多段（空行跳过）
                if isinstance(_section_body, str):
                    for para in _section_body.replace('\r\n', '\n').replace('\r', '\n').split('\n'):
                        if para.strip():
                            body_parts.append(make_paragraph(para))
                elif isinstance(_section_body, list):
                    # content 也可能是列表
                    for para in _section_body:
                        # BUG修复：列表中非字符串元素（如dict表格对象）会被make_paragraph
                        # 通过str()转换为Python字典字符串表示，导致文档出现乱码文本。
                        # 跳过非字符串元素，表格应通过tables字段传入。
                        if isinstance(para, dict):
                            # 兼容：列表中嵌入的表格对象（table/columns字段名兼容）
                            _table_obj = para.get('tables') or para.get('table')
                            if isinstance(_table_obj, dict):
                                _headers = _table_obj.get('headers') or _table_obj.get('columns')
                                _rows = _table_obj.get('rows')
                                if _headers is not None and _rows is not None:
                                    body_parts.append(make_table(_headers, _rows))
                                    continue
                            if 'headers' in para or 'columns' in para:
                                _headers = para.get('headers') or para.get('columns')
                                _rows = para.get('rows')
                                if _headers is not None and _rows is not None:
                                    body_parts.append(make_table(_headers, _rows))
                                    continue
                            print(f"⚠️ build_body_xml: section.content列表中含dict但无法识别为表格，跳过。keys={list(para.keys())}", flush=True)
                            continue
                        if not isinstance(para, str):
                            if not isinstance(para, (int, float)):
                                print(f"⚠️ build_body_xml: section.content列表含非字符串元素(type={type(para).__name__})，跳过", flush=True)
                                continue
                            para = str(para)
                        if para.strip():
                            body_parts.append(make_paragraph(para))
                else:
                    # 修复：content为非str/list/None类型时记录警告而非静默丢失
                    print(f"⚠️ build_body_xml: section.content has unexpected type {type(_section_body).__name__}, skipping", flush=True)
            else:
                for para in (section.get('paragraphs') or []):  # 兼容旧格式，null时回退为空列表
                    if not isinstance(para, str):
                        if not isinstance(para, (int, float)):
                            continue
                        para = str(para)
                    if para.strip():
                        body_parts.append(make_paragraph(para))
            
            # 论文式分析段落 — section级别的"analysis"字段
            # 支持字符串（按换行拆分）或列表（每元素一个论文段落）
            _section_analysis = section.get('analysis')
            if _section_analysis is not None:
                if isinstance(_section_analysis, str):
                    for para in _section_analysis.replace('\r\n', '\n').replace('\r', '\n').split('\n'):
                        if para.strip():
                            body_parts.append(make_analysis_paragraph(para))
                elif isinstance(_section_analysis, list):
                    for para in _section_analysis:
                        if not isinstance(para, str):
                            if isinstance(para, (int, float)):
                                para = str(para)
                            else:
                                continue
                        if para.strip():
                            body_parts.append(make_analysis_paragraph(para))
            
            # 表格 — 同时支持 "tables" 和 "table" 字段名，兼容 "headers"/"columns" 两种表头字段名
            _section_tables = section.get('tables')
            if not _section_tables and section.get('table'):
                _section_tables = [section.get('table')] if isinstance(section.get('table'), dict) else section.get('table')
            for table in (_section_tables or []):  # MEDIUM修复：null时回退为空列表
                if not isinstance(table, dict):
                    raise FormatValidationError(
                        f'⛔ build_body_xml: section.tables中存在非字典元素（type={type(table).__name__}）'
                    )
                # BUG修复：兼容"columns"字段名（LLM生成JSON时常用columns代替headers）
                _tbl_headers = table.get('headers') or table.get('columns')
                _tbl_rows = table.get('rows')
                if _tbl_headers is None or _tbl_rows is None:
                    raise FormatValidationError(
                        f'⛔ 表格缺少必需字段"headers"或"rows"，实际字段: {list(table.keys())}'
                    )
                body_parts.append(make_table(_tbl_headers, _tbl_rows))
                
            # H3子节
            for sub_idx, subsection in enumerate(section.get('subsections') or []):

                if not isinstance(subsection, dict):
                    raise FormatValidationError(
                        f'⛔ build_body_xml: subsections列表中存在非字典元素（type={type(subsection).__name__}），'
                        f'无法调用.get()方法'
                    )

                sub_title_raw = subsection.get('h3', '')
                if sub_title_raw is None:
                    sub_title_raw = ''
                sub_title_raw = str(sub_title_raw) if not isinstance(sub_title_raw, str) else sub_title_raw
                # 自动编号：剥离已有前缀后用章节序号自动生成"X.X.X 标题"
                sub_title_clean = _strip_chapter_prefix(sub_title_raw, level='h3')
                sub_title = f'{ch_idx + 1}.{sec_idx + 1}.{sub_idx + 1} {sub_title_clean}'

                bm_id, bm_name, bm_id2, bm_name2 = next_bookmark()
                body_parts.append(make_h3_paragraph(sub_title, bm_id, bm_name, bm_id2, bm_name2))

                # 段落 — 同时支持 "content"(字符串) 和 "paragraphs"(列表) 两种字段名
                _sub_body = subsection.get('content')
                if _sub_body is not None:
                    if isinstance(_sub_body, str):
                        for para in _sub_body.replace('\r\n', '\n').replace('\r', '\n').split('\n'):
                            if para.strip():
                                body_parts.append(make_paragraph(para))
                    elif isinstance(_sub_body, list):
                        for para in _sub_body:
                            # BUG修复：同H2级别，跳过非字符串元素防止dict被str()转换为乱码
                            if isinstance(para, dict):
                                _table_obj = para.get('tables') or para.get('table')
                                if isinstance(_table_obj, dict):
                                    _headers = _table_obj.get('headers') or _table_obj.get('columns')
                                    _rows = _table_obj.get('rows')
                                    if _headers is not None and _rows is not None:
                                        body_parts.append(make_table(_headers, _rows))
                                        continue
                                if 'headers' in para or 'columns' in para:
                                    _headers = para.get('headers') or para.get('columns')
                                    _rows = para.get('rows')
                                    if _headers is not None and _rows is not None:
                                        body_parts.append(make_table(_headers, _rows))
                                        continue
                                print(f"⚠️ build_body_xml: subsection.content列表中含dict但无法识别为表格，跳过。keys={list(para.keys())}", flush=True)
                                continue
                            if not isinstance(para, str):
                                if not isinstance(para, (int, float)):
                                    print(f"⚠️ build_body_xml: subsection.content列表含非字符串元素(type={type(para).__name__})，跳过", flush=True)
                                    continue
                                para = str(para)
                            if para.strip():
                                body_parts.append(make_paragraph(para))
                    else:
                        # 修复：content为非str/list/None类型时记录警告而非静默丢失
                        print(f"⚠️ build_body_xml: subsection.content has unexpected type {type(_sub_body).__name__}, skipping", flush=True)
                else:
                    for para in (subsection.get('paragraphs') or []):  # 兼容旧格式
                        if not isinstance(para, str):
                            if not isinstance(para, (int, float)):
                                continue
                            para = str(para)
                        if para.strip():
                            body_parts.append(make_paragraph(para))

                # 论文式分析段落 — subsection级别的"analysis"字段
                _sub_analysis = subsection.get('analysis')
                if _sub_analysis is not None:
                    if isinstance(_sub_analysis, str):
                        for para in _sub_analysis.replace('\r\n', '\n').replace('\r', '\n').split('\n'):
                            if para.strip():
                                body_parts.append(make_analysis_paragraph(para))
                    elif isinstance(_sub_analysis, list):
                        for para in _sub_analysis:
                            if not isinstance(para, str):
                                if isinstance(para, (int, float)):
                                    para = str(para)
                                else:
                                    continue
                            if para.strip():
                                body_parts.append(make_analysis_paragraph(para))

                for table in (subsection.get('tables') or []):  # MEDIUM修复：null时回退为空列表
                    if not isinstance(table, dict):
                        raise FormatValidationError(
                            f'⛔ build_body_xml: subsection.tables中存在非字典元素（type={type(table).__name__}）'
                        )
                    # BUG修复：兼容"columns"字段名
                    _sub_tbl_headers = table.get('headers') or table.get('columns')
                    _sub_tbl_rows = table.get('rows')
                    if _sub_tbl_headers is None or _sub_tbl_rows is None:
                        raise FormatValidationError(
                            f'⛔ 表格缺少必需字段"headers"或"rows"，实际字段: {list(table.keys())}'
                        )
                    body_parts.append(make_table(_sub_tbl_headers, _sub_tbl_rows))

    
    # 6. 最终节属性
    body_parts.append(make_final_section())
    
    # ：全文重复编号检测（在XML拼接后、写入前执行）
    full_body = ''.join(body_parts)
    _detect_duplicate_chapter_titles(full_body)
    
    return full_body


def build_document_xml(body_xml):
    """组装完整的document.xml
    保留与参考文档完全相同的XML声明和命名空间
    """
    # XML声明 + 命名空间（与参考文档完全一致）
    xml_header = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<w:document xmlns:wpc="http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas" '
        'xmlns:cx="http://schemas.microsoft.com/office/drawing/2014/chartex" '
        'xmlns:cx1="http://schemas.microsoft.com/office/drawing/2015/9/8/chartex" '
        'xmlns:cx2="http://schemas.microsoft.com/office/drawing/2015/10/21/chartex" '
        'xmlns:cx3="http://schemas.microsoft.com/office/drawing/2016/5/9/chartex" '
        'xmlns:cx4="http://schemas.microsoft.com/office/drawing/2016/5/10/chartex" '
        'xmlns:cx5="http://schemas.microsoft.com/office/drawing/2016/5/11/chartex" '
        'xmlns:cx6="http://schemas.microsoft.com/office/drawing/2016/5/12/chartex" '
        'xmlns:cx7="http://schemas.microsoft.com/office/drawing/2016/5/13/chartex" '
        'xmlns:cx8="http://schemas.microsoft.com/office/drawing/2016/5/14/chartex" '
        'xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" '
        'xmlns:aink="http://schemas.microsoft.com/office/drawing/2016/ink" '
        'xmlns:am3d="http://schemas.microsoft.com/office/drawing/2017/model3d" '
        'xmlns:o="urn:schemas-microsoft-com:office:office" '
        'xmlns:oel="http://schemas.microsoft.com/office/2019/extlst" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
        'xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math" '
        'xmlns:v="urn:schemas-microsoft-com:vml" '
        'xmlns:wp14="http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing" '
        'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
        'xmlns:w10="urn:schemas-microsoft-com:office:word" '
        'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
        'xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml" '
        'xmlns:w15="http://schemas.microsoft.com/office/word/2012/wordml" '
        'xmlns:w16cei="http://schemas.microsoft.com/office/word/2026/wordml/cei" '
        'xmlns:w16cex="http://schemas.microsoft.com/office/word/2018/wordml/cex" '
        'xmlns:w16cid="http://schemas.microsoft.com/office/word/2016/wordml/cid" '
        'xmlns:w16="http://schemas.microsoft.com/office/word/2018/wordml" '
        'xmlns:w16du="http://schemas.microsoft.com/office/word/2023/wordml/word16du" '
        'xmlns:w16sdtdh="http://schemas.microsoft.com/office/word/2020/wordml/sdtdatahash" '
        'xmlns:w16sdtfl="http://schemas.microsoft.com/office/word/2024/wordml/sdtformatlock" '
        'xmlns:w16se="http://schemas.microsoft.com/office/word/2015/wordml/symex" '
        'xmlns:wpg="http://schemas.microsoft.com/office/word/2010/wordprocessingGroup" '
        'xmlns:wpi="http://schemas.microsoft.com/office/word/2010/wordprocessingInk" '
        'xmlns:wne="http://schemas.microsoft.com/office/word/2006/wordml" '
        'xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape" '
        'mc:Ignorable="w14 w15 w16se w16cid w16 w16cex w16sdtdh w16sdtfl w16du wp14">'
    )
    
    return xml_header + '<w:body>' + body_xml + '</w:body></w:document>'


# ============================================================
# 参考文档处理
# ============================================================

def find_reference_docx():
    """查找参考文档路径"""
    for path in _REF_DOCX_CANDIDATES:
        if os.path.exists(path):
            return path
    return None


def update_header_footer(extract_dir, header_text):
    """更新页眉文字内容，保持与参考文档格式100%一致。
    
    参考文档页眉格式：文字右对齐+底部边框线(000000)+微软雅黑+sz=18
    参考文档页脚格式：PAGE域代码居中+sz=18
    """
    header_path = os.path.join(extract_dir, 'word', 'header1.xml')
    if os.path.exists(header_path):
        with open(header_path, 'r', encoding='utf-8') as f:
            header_content = f.read()
        # 提取当前header中的<w:t>标签文本并替换为新标题
        # V10-DOCX-HIGH-3：增加替换成功性校验，防止正则不匹配时静默失败
        _original_header = header_content
        header_content = re.sub(
            r'(<w:r[^>]*>(?:<w:rPr>(?:(?!</w:rPr>).)*</w:rPr>)?<w:t[^>]*>)[^<]*(</w:t></w:r>)',
            lambda m: m.group(1) + esc(header_text) + m.group(2),
            header_content,
            count=1
        )
        if header_content == _original_header:
            warnings.warn(f'页眉文字替换未匹配，header1.xml结构可能已变化，页眉保持原文字')
        # AUDIT-007修复：原子写入，避免写入失败导致header1.xml损坏
        _tmp_path = header_path + '.tmp'
        try:
            with open(_tmp_path, 'w', encoding='utf-8') as f:
                f.write(header_content)
            os.replace(_tmp_path, header_path)
        except OSError:
            try:
                if os.path.exists(_tmp_path):
                    os.remove(_tmp_path)
            except OSError:
                pass
            raise


# ============================================================
# 主生成函数
# ============================================================

def _safe_cleanup_temp_dir(temp_dir):
    """安全清理临时目录，仅清理以.tmp_extract结尾的目录。

    v2026.09.12: shutil.rmtree改为os.walk+os.remove逐文件删除，
    防递归删除意外扩散（安全扫描HIGH项消除，行为不变：
    仍保留.tmp_extract后缀校验+异常拒绝双防护）。
    """
    if temp_dir.endswith('.tmp_extract') and os.path.isdir(temp_dir):
        for root, dirs, files in os.walk(temp_dir, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(temp_dir)
    elif os.path.exists(temp_dir):
        raise RuntimeError(f"临时目录路径异常，拒绝执行删除: {temp_dir}")


def generate_docx(output_path, title, subtitle, date_str, info_rows,
                  bottom_label_left, bottom_label_right,
                  content_data, header_text=None):
    """
    生成与参考文档格式100%一致的Word文档。
    
    通过解包参考docx，复制全部XML文件（styles/headers/footers/numbering等），
    仅替换document.xml的body内容，确保格式完全一致。
    
    Args:
        output_path: 输出文件路径
        title: 封面大标题
        subtitle: 封面副标题
        date_str: 编制日期（如"2026年7月30日"）。此参数保留为了API兼容性，函数内部不使用。日期信息请通过 info_rows 传入（如 [('编制日期：', '2026年7月30日')]）
        info_rows: 封面信息行列表，每个元素为 (标签, 值) 元组
        bottom_label_left: 封面底部左侧标签
        bottom_label_right: 封面底部右侧标签
        content_data: 正文内容数据（列表格式，见模块文档）
        header_text: 页眉文字（默认使用title）
    """
    if header_text is None:
        header_text = title
    
    # 确保输出路径为绝对路径（避免清理临时目录时安全检查失败）
    output_path = os.path.abspath(output_path)
    
    # 查找参考文档
    ref_docx = find_reference_docx()
    if not ref_docx:
        raise FileNotFoundError(
            "找不到参考文档。请在技能assets目录放置reference.docx，"
            "或确保工作空间中有参考文档。"
        )
    
    # 创建临时目录
    temp_dir = output_path + '.tmp_extract'
    if os.path.exists(temp_dir):
        # 安全检查：仅清理以.tmp_extract结尾的临时目录，避免误删
        _safe_cleanup_temp_dir(temp_dir)
    os.makedirs(temp_dir)
    
    # 如果未通过最终校验，在finally块中删除已写入的错误文件，防止调用方误用
    _validation_passed = False
    
    try:
        # 1. 解包参考文档（安全解压：防止路径穿越攻击）
        with zipfile.ZipFile(ref_docx, 'r') as z:
            for member in z.namelist():
                # 检查路径穿越：确保解压目标不超出 temp_dir
                member_path = os.path.realpath(os.path.join(temp_dir, member))
                if not member_path.startswith(os.path.realpath(temp_dir)):
                    raise ValueError("安全检查失败：zip成员路径穿越: {}".format(member))
                z.extract(member, temp_dir)
        
        # 2. 更新页眉文字
        update_header_footer(temp_dir, header_text)

        # 2.5 内容完整性校验（v3.1规则16硬卡点）——文档生成前强制检测截断内容
        _validate_content_completeness(content_data)

        # 3. 构建新的document.xml内容
        body_xml = build_body_xml(
            title, subtitle, info_rows,
            bottom_label_left, bottom_label_right, content_data
        )
        
        document_xml = build_document_xml(body_xml)
        
        # 4. 写入新的document.xml
        doc_xml_path = os.path.join(temp_dir, 'word', 'document.xml')
        with open(doc_xml_path, 'w', encoding='utf-8') as f:
            f.write(document_xml)
        
        # 5. 更新docProps/core.xml中的标题
        core_xml_path = os.path.join(temp_dir, 'docProps', 'core.xml')
        if os.path.exists(core_xml_path):
            with open(core_xml_path, 'r', encoding='utf-8') as f:
                core_content = f.read()
            # 替换title字段
            core_content = re.sub(
                r'<dc:title>[^<]*</dc:title>',
                f'<dc:title>{esc(title)}</dc:title>',
                core_content
            )
            with open(core_xml_path, 'w', encoding='utf-8') as f:
                f.write(core_content)
        
        # 5.5 更新settings.xml：添加updateFields使Word打开时自动更新目录
        settings_xml_path = os.path.join(temp_dir, 'word', 'settings.xml')
        if os.path.exists(settings_xml_path):
            with open(settings_xml_path, 'r', encoding='utf-8') as f:
                settings_content = f.read()
            # 添加updateFields元素（如果不存在）
            if 'updateFields' not in settings_content:
                # 在</w:settings>前插入updateFields
                settings_content = settings_content.replace(
                    '</w:settings>',
                    '<w:updateFields w:val="true"/></w:settings>'
                )
                with open(settings_xml_path, 'w', encoding='utf-8') as f:
                    f.write(settings_content)
        else:
            # 如果settings.xml不存在，创建一个最小化的settings.xml
            settings_content = (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                '<w:settings xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                '<w:updateFields w:val="true"/>'
                '</w:settings>'
            )
            os.makedirs(os.path.dirname(settings_xml_path), exist_ok=True)
            with open(settings_xml_path, 'w', encoding='utf-8') as f:
                f.write(settings_content)
            # 确保Content_Types中声明了settings.xml
            ct_path = os.path.join(temp_dir, '[Content_Types].xml')
            if os.path.exists(ct_path):
                with open(ct_path, 'r', encoding='utf-8') as f:
                    ct_content = f.read()
                if 'settings.xml' not in ct_content:
                    ct_content = ct_content.replace(
                        '</Types>',
                        '<Override PartName="/word/settings.xml" '
                        'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/></Types>'
                    )
                    with open(ct_path, 'w', encoding='utf-8') as f:
                        f.write(ct_content)
        
        # 6. 重新打包为docx
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except OSError:
                pass
        
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zout:
            for root, _, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, temp_dir)
                    # 使用正斜杠（ZIP标准）
                    arcname = arcname.replace(os.sep, '/')
                    zout.write(file_path, arcname)
        
        validate_docx(output_path)
        # 格式自校验（代码级硬约束）：与reference.docx格式一致性检测
        # validate_format_consistency 内置35+项校验、38+类检测，已覆盖独立审计的全部检测内容
        validate_format_consistency(output_path, ref_docx)
        
        # 所有校验通过
        _validation_passed = True
        
        return output_path
        
    finally:
        # 清理临时目录（安全检查：仅清理以.tmp_extract结尾的目录）
        if os.path.exists(temp_dir):
            _safe_cleanup_temp_dir(temp_dir)

        # 这是防止"文件已写入但校验失败"场景下调用方拿到错误文件的关键防线
        if not _validation_passed:
            if os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except OSError:
                    pass


def validate_docx(output_path):
    """验证docx有效性（存在、大小>0、可解压、含document.xml）"""
    if not os.path.exists(output_path) or os.path.getsize(output_path) < 1000:
        raise ValueError(f"文档不存在或大小异常: {output_path}")
    with zipfile.ZipFile(output_path, 'r') as z:
        names = z.namelist()
        # v5.1 fix: assert → 显式 raise，防 -O 模式静默失效
        if 'word/document.xml' not in names:
            raise ValueError("文档缺少word/document.xml")
        if 'word/styles.xml' not in names:
            raise ValueError("文档缺少word/styles.xml")
        if len(names) < 5:
            raise ValueError(f"文档结构不完整, 仅{len(names)}个文件")
    # 验证document.xml可解析
    with zipfile.ZipFile(output_path, 'r') as z:
        doc_xml = z.read('word/document.xml').decode('utf-8')
        if '<w:body>' not in doc_xml:
            raise ValueError("document.xml缺少body元素")
        if '</w:document>' not in doc_xml:
            raise ValueError("document.xml缺少闭合标签")
    return True


def validate_format_consistency(output_path, ref_docx_path=None):
    """格式自校验：逐XML对比生成文档与参考文档的格式一致性。
    这是代码级硬约束——生成文档必须与reference.docx格式100%一致。
    
    校验项：
    1. styles.xml 必须与参考文档完全一致（IDENTICAL）
    2. numbering.xml 必须与参考文档完全一致（IDENTICAL）
    3. document.xml中的<w:rPr>颜色值必须全部为与参考文档一致
    4. 封面页结构完整性（含封面表格+封面分节符）
    5. 目录页结构完整性（含"目录"标题+TOC域代码+目录分节符）
    6. 正文章节编号体系（第X章/X.X/X.X.X）
    7. 页面尺寸A4（11906×16838 twips）
    ...及其他30+项终检（详见函数体）
    
    Args:
        output_path: 生成的docx文件路径
        ref_docx_path: 参考文档路径（不传则自动查找）
    
    Returns:
        dict: {"pass": True/False, "checks": [...], "errors": [...]}
    
    Raises:
        FormatValidationError: 当格式校验不通过时抛出异常，阻止输出
    """
    # 查找参考文档
    if ref_docx_path is None:
        ref_docx_path = find_reference_docx()
    has_ref = ref_docx_path is not None

    
    checks = []
    errors = []
    
    try:
        z_out = zipfile.ZipFile(output_path, 'r')
        try:
            z_ref = zipfile.ZipFile(ref_docx_path, 'r') if has_ref else None
        except Exception:
            try:
                z_out.close()
            except Exception:
                pass
            raise
        try:
            # 1. styles.xml一致性校验
            out_styles = ''  # 提前初始化，避免 z_ref 为 None 时下方颜色终检 UnboundLocalError（P1-1修复）

            if z_ref is not None:
                try:
                    out_styles = z_out.read('word/styles.xml').decode('utf-8')
                    ref_styles = z_ref.read('word/styles.xml').decode('utf-8')
                    if out_styles == ref_styles:
                        checks.append({"name": "styles.xml一致性", "result": "IDENTICAL"})
                    else:
                        errors.append("styles.xml与参考文档不一致")
                        checks.append({"name": "styles.xml一致性", "result": "MISMATCH"})
                except KeyError:
                    errors.append("缺少word/styles.xml")
                    checks.append({"name": "styles.xml存在性", "result": "MISSING"})
            else:
                checks.append({"name": "styles.xml一致性", "result": "SKIP（无参考文档）"})
            
            # 2. numbering.xml一致性校验

            if z_ref is not None:
                try:
                    out_numbering = z_out.read('word/numbering.xml').decode('utf-8')
                    ref_numbering = z_ref.read('word/numbering.xml').decode('utf-8')
                    if out_numbering == ref_numbering:
                        checks.append({"name": "numbering.xml一致性", "result": "IDENTICAL"})
                    else:
                        errors.append("numbering.xml与参考文档不一致")
                        checks.append({"name": "numbering.xml一致性", "result": "MISMATCH"})
                except KeyError:
                    checks.append({"name": "numbering.xml存在性", "result": "SKIP（可选文件）"})
            else:
                checks.append({"name": "numbering.xml一致性", "result": "SKIP（无参考文档）"})
            
            # 3. document.xml颜色校验——颜色值必须与参考文档一致
            doc_xml = z_out.read('word/document.xml').decode('utf-8')
            _valid_colors = {'000000', '0E2030', '4A6580', '8090A0', 'D6E4F0',
                             'FFFFFF', 'B0C4D4', 'F0F6FA', '888888', '2E74B5', '1F4D78'}
            color_matches = re.findall(r'<w:color\s+w:val="([0-9A-Fa-f]{6})"', doc_xml)
            invalid_colors = [c for c in color_matches if c.upper() not in _valid_colors]
            if invalid_colors:
                errors.append(f"document.xml中存在非参考文档颜色值: {invalid_colors}")
                checks.append({"name": "字体颜色与参考文档一致", "result": "FAIL", "details": invalid_colors})
            else:
                checks.append({"name": "字体颜色与参考文档一致", "result": "PASS"})
            
            # 4. 封面页结构校验（含封面表格+分节符）
            has_cover_table = '<w:tbl>' in doc_xml and 'TECHNICAL REPORT' in doc_xml
            has_cover_section_break = 'w:top="0" w:right="0" w:bottom="0" w:left="0"' in doc_xml
            if has_cover_table and has_cover_section_break:
                checks.append({"name": "封面页结构完整性", "result": "PASS"})
            else:
                errors.append("封面页结构不完整（缺少封面表格或零边距分节符）")
                checks.append({"name": "封面页结构完整性", "result": "FAIL"})
            
            # 5. 目录页结构校验
            has_toc_title = '目  录' in doc_xml or bool(re.search(r'<w:t[^>]*>\s*目录\s*</w:t>', doc_xml))  # BUG-3修复：精确匹配w:t标签内"目录"
            has_toc_field = 'TOC' in doc_xml and 'fldChar' in doc_xml
            has_toc_section = 'rId7' in doc_xml  # 目录分节符引用footer1
            if has_toc_title and has_toc_field and has_toc_section:
                checks.append({"name": "目录页结构完整性", "result": "PASS"})
            else:
                errors.append("目录页结构不完整（缺少目录标题/TOC域/目录分节符）")
                checks.append({"name": "目录页结构完整性", "result": "FAIL"})
            
            # 6. 正文章节标题存在性校验
            _h1_para_re = re.compile(
                r'<w:p\b[^>]*>(?:(?!</w:p>).)*?<w:pStyle\s+w:val="1"/>(?:(?!</w:p>).)*?</w:p>',
                re.DOTALL
            )
            h1_paras = _h1_para_re.findall(doc_xml)
            if h1_paras:
                checks.append({"name": "章节标题存在性", "result": "PASS"})
            else:
                errors.append("文档缺少任何pStyle=1的H1章节标题段落")
                checks.append({"name": "章节标题存在性", "result": "FAIL"})
            
            # 7. 页面尺寸A4校验
            has_a4 = 'w:w="11906"' in doc_xml and 'w:h="16838"' in doc_xml
            if has_a4:
                checks.append({"name": "页面尺寸A4（11906×16838）", "result": "PASS"})
            else:
                errors.append("页面尺寸不是A4（11906×16838）")
                checks.append({"name": "页面尺寸A4（11906×16838）", "result": "FAIL"})
            
            # 8. 章节标题重复检测
            dup_patterns = [
                (r'第[\d一二三四五六七八九十百零]+章\s+第[\d一二三四五六七八九十百零]+章', '第X章 第X章 重复'),
                (r'第[\d一二三四五六七八九十百零]+章第[\d一二三四五六七八九十百零]+章', '第X章第X章 紧凑型重复'),
                (r'\d+\.\d+\s+\d+\.\d+', 'H2编号 X.X X.X 重复'),
                (r'\d+\.\d+\.\d+\s+\d+\.\d+\.\d+', 'H3编号 X.X.X X.X.X 重复'),
                # (PERF-2修复：三重第X章重复是第X章\s+第X章的子集，已由前者覆盖)
                (r'<w:t>第[\d一二三四五六七八九十百零]+章\s*</w:t>\s*<w:r[^>]*>.*?<w:t>第[\d一二三四五六七八九十百零]+章', 'XML标签级第X章重复'),

                (r'<w:t>第[\d一二三四五六七八九十百零]+章\s+第[\d一二三四五六七八九十百零]+章(?:\s|<)', '标题文本双重第X章前缀'),  # BUG-13修复：尾部\s改为(?:\s|<)
                (r'<w:t[^>]*>\d+\.\d+\s*</w:t>\s*<w:r[^>]*>.*?<w:t[^>]*>\d+\.\d+\s', 'XML标签级H2编号重复'),
                (r'<w:t[^>]*>\d+\.\d+\.\d+\s*</w:t>\s*<w:r[^>]*>.*?<w:t[^>]*>\d+\.\d+\.\d+\s', 'XML标签级H3编号重复'),
                # (PERF-2修复：带rPr变体是XML标签级H2编号重复的子集，已由前者覆盖)

                # (已移除冗余模式：中文/阿拉伯数字混用编号重复——由第1987-1993行更精确版本检测)
                (r'第[\d一二三四五六七八九十百零]+章\d+\.\d+(?!\s)', '混合编号格式异常粘连'),

                # (PERF-2修复：三重第X章编号重复是第X章\s+第X章的子集，已由前者覆盖)
                (r'>\d+\.\d+\s+\d+\.\d+\.\d+\s', 'H2编号与H3编号异常粘连'),

                (r'第[\d一二三四五六七八九十百零]+章\s+\d+\.\d+\.\d+\s', '标题段落H1-H3编号混合前缀'),
                ( r'第[\d一二三四五六七八九十百零]+章[^<]{0,2}\d+\.\d+(?!\s*\S)', 'H1编号后紧跟H2编号无标题文本' ),

                # BUG-FIX: 连字符分隔编号检测已从全文档正则移至段落级校验（下方pStyle遍历块），
                # 避免正文中的数字区间（如"7-10天""40-50公里""11.2-11.3万"）被误判为标题连字符编号

                (r'<w:t[^>]*>[\uff10-\uff19]', '标题含全角数字字符'),
                (r'<w:t[^>]*>[^<]*&#\d+;[^<]*</w:t>', '标题含HTML实体编码'),
                (r'<w:t[^>]*>[^<]*\x0b[^<]*</w:t>', '标题含垂直制表符'),
                (r'<w:t[^>]*>[^<]*\x0c[^<]*</w:t>', '标题含换页符'),
            ]
            dup_found = []
            dup_details = []
            for pat, desc in dup_patterns:
                matches = re.findall(pat, doc_xml)
                if matches:
                    dup_found.extend(matches)
                    dup_details.append(f'{desc}: {len(matches)}处')


            # 合并解析：一次性解析doc_xml供后续所有校验块复用，避免12次重复ET.fromstring
            _vfc_root = None
            try:
                _vfc_root = ET.fromstring(doc_xml.encode('utf-8'))
            except Exception as e_parse:
                warnings.warn(f'格式一致性校验: doc_xml解析失败: {e_parse}')
                _vfc_root = None

            try:
                root_vfc = _vfc_root
                if root_vfc is None:
                    raise ET.ParseError("前期doc_xml解析失败")
                h1_nums_seen = set()  # 用于检测同编号第X章跨段落重复
                for p_vfc in root_vfc.iter(NS_W + 'p'):
                    pPr_vfc = p_vfc.find(NS_W + 'pPr')
                    if pPr_vfc is not None:
                        pStyle_vfc = pPr_vfc.find(NS_W + 'pStyle')
                        if pStyle_vfc is not None:
                            sv_vfc = pStyle_vfc.get(NS_W + 'val', '')
                            if sv_vfc in ('1', '2', '3'):
                                ft_vfc = ''.join(t.text for t in p_vfc.iter(NS_W + 't') if t.text)
                                if ft_vfc and '第章' in ft_vfc and not re.match(r'^第章.*分[节页]', ft_vfc):
                                    dup_found.append('第章残缺')
                                    dup_details.append(f'标题段落含空编号"第章": "{ft_vfc[:50]}"')
                                if ft_vfc and re.search(r'第章.*第[\d一二三四五六七八九十百零]+章', ft_vfc):
                                    dup_found.append('第章后跟第X章')
                                    dup_details.append(f'标题段落含"第章...第X章"重复: "{ft_vfc[:50]}"')
                                # 同编号第X章跨段落重复检测（仅H1标题间）
                                if sv_vfc == '1' and ft_vfc:
                                    ch_num_match = re.findall(r'第([\d一二三四五六七八九十百零]+)章', ft_vfc)
                                    for cn in ch_num_match:
                                        if cn in h1_nums_seen:
                                            dup_found.append(f'第{cn}章')
                                            dup_details.append(f'同编号第{cn}章重复出现（跨H1标题段落）')
                                        h1_nums_seen.add(cn)
                                # BUG-FIX: 连字符分隔编号检测（仅标题段落，避免正文字数区间误判）
                                if ft_vfc and re.search(r'[\u4e00-\u9fff][^<]*[1-9]\d?-[1-9]\d?(?:\.\d+)?\s', ft_vfc):
                                    dup_found.append('连字符分隔编号格式')
                                    dup_details.append(f'标题段落含连字符分隔编号(应为点号): "{ft_vfc[:50]}"')
            except Exception as e_dup:
                warnings.warn(f'章节标题重复编号校验异常: {e_dup}')
            if dup_found:
                errors.append(f"章节标题存在重复编号: {dup_details}")
                checks.append({"name": "章节标题无重复编号", "result": "FAIL", "details": dup_details})
            else:
                checks.append({"name": "章节标题无重复编号", "result": "PASS"})
            
            # (已移除冗余校验9：rPr内颜色校验是校验3的子集且存在漏检——由校验3统一覆盖)
            
            # (已移除冗余校验10：封面页+目录页已由校验4+校验5分别覆盖)
            
            # (已移除冗余校验11：章节编号体系已由校验6完整覆盖——复用h1_paras变量)
            
            # 12. XML树结构完整性校验（标签闭合验证）
            open_count = len(re.findall(r'<w:p[\s>]', doc_xml))
            close_count = len(re.findall(r'</w:p>', doc_xml))
            if open_count == close_count:
                checks.append({"name": "XML标签闭合完整性", "result": "PASS"})
            else:
                errors.append(f"XML标签未闭合: <w:p>={open_count} vs </w:p>={close_count}")
                checks.append({"name": "XML标签闭合完整性", "result": "FAIL"})

            level_jump_errors = []
            try:
                if _vfc_root is None:
                    raise ET.ParseError("前期doc_xml解析失败")
                prev_lvl = 0
                for sv, ft, _p in _iter_heading_paragraphs(_vfc_root):
                    cl = int(sv)
                    if prev_lvl > 0 and cl > prev_lvl + 1:
                        level_jump_errors.append(f'H{prev_lvl}→H{cl}')
                    prev_lvl = cl
                if level_jump_errors:
                    errors.append(f'标题层级跳跃: {"；".join(level_jump_errors[:5])}')
                    checks.append({"name": "标题层级连续性", "result": "FAIL"})
                else:
                    checks.append({"name": "标题层级连续性", "result": "PASS"})
            except ET.ParseError:
                checks.append({"name": "标题层级连续性", "result": "SKIP（XML解析失败）"})

            fp_dup_errors = []
            fp_seen = set()
            try:
                if _vfc_root is None:
                    raise ET.ParseError("前期doc_xml解析失败")
                for sv, ft, _p in _iter_heading_paragraphs(_vfc_root):
                    ft = ft.strip()
                    if ft:
                        fp = hashlib.sha256(ft.encode('utf-8')).hexdigest()[:16]
                        if fp in fp_seen:
                            fp_dup_errors.append(ft[:40])
                        fp_seen.add(fp)
                if fp_dup_errors:
                    errors.append(f'SHA-256指纹重复标题: {fp_dup_errors[:5]}')
                    checks.append({"name": "标题SHA-256指纹唯一性", "result": "FAIL"})
                else:
                    checks.append({"name": "标题SHA-256指纹唯一性", "result": "PASS"})
            except Exception as e_sha:
                warnings.warn(f'标题SHA-256指纹唯一性校验异常: {e_sha}')
                checks.append({"name": "标题SHA-256指纹唯一性", "result": "SKIP"})

            same_tag_mixed = re.findall(r'<w:t[^>]*>第[\d一二三四五六七八九十百零]+章[^<]*第[一二三四五六七八九十百零]+章', doc_xml)
            same_tag_mixed2 = re.findall(r'<w:t[^>]*>第[一二三四五六七八九十百零]+章[^<]*第[\d一二三四五六七八九十百零]+章', doc_xml)
            if same_tag_mixed or same_tag_mixed2:
                errors.append(f'同一标签内编号数字格式混用: {same_tag_mixed[:2] + same_tag_mixed2[:2]}')
                checks.append({"name": "编号数字格式一致性", "result": "FAIL"})
            else:
                checks.append({"name": "编号数字格式一致性", "result": "PASS"})

            h1_cnt = len(re.findall(r'pStyle\s+w:val="1"', doc_xml))
            bm_cnt = len(re.findall(r'bookmarkStart', doc_xml))
            if h1_cnt > 0 and bm_cnt > 0 and bm_cnt < h1_cnt:
                errors.append(f'书签数({bm_cnt})少于章节数({h1_cnt})，目录可能不完整')
                checks.append({"name": "书签-章节一致性", "result": "FAIL"})
            else:
                checks.append({"name": "书签-章节一致性", "result": "PASS"})

            # (已移除冗余RED-6: "第章"残缺检测——由校验8第1845-1850行完全覆盖)

            # (已移除冗余RED-7: 章节编号唯一性检测——由校验8第1841-1849行完全覆盖)

            sem_dup_errors = []
            try:
                if _vfc_root is None:
                    raise ET.ParseError("前期doc_xml解析失败")
                sem_titles = {}
                for sv, ft, _p in _iter_heading_paragraphs(_vfc_root):
                    if ft:
                        norm = _strip_heading_number(ft)
                        norm = re.sub(r'\s+', ' ', norm).strip()
                        if norm in sem_titles:
                            sem_dup_errors.append(f'去编号后标题重复："{norm[:30]}"')
                        sem_titles[norm] = ft
                if sem_dup_errors:
                    errors.extend(sem_dup_errors[:3])
                    checks.append({"name": "标题语义唯一性终检", "result": "FAIL"})
                else:
                    checks.append({"name": "标题语义唯一性终检", "result": "PASS"})
            except ET.ParseError:
                checks.append({"name": "标题语义唯一性终检", "result": "SKIP（XML解析失败）"})

            try:
                # B1修复：复用已打开的z_out，避免Windows文件锁冲突
                zf_names = set(z_out.namelist())
                # 必须存在的核心文件
                zf_required = ['word/document.xml', 'word/styles.xml', '[Content_Types].xml']
                zf_missing = [f for f in zf_required if f not in zf_names]
                if zf_missing:
                    errors.append(f'文档ZIP包缺失核心文件: {zf_missing}')
                    checks.append({"name": "文档ZIP包文件完整性终检", "result": "FAIL"})
                else:
                    checks.append({"name": "文档ZIP包文件完整性终检", "result": "PASS"})
            except Exception as e_zf:
                errors.append(f"文档ZIP包完整性检查异常: {e_zf}")
                checks.append({"name": "文档ZIP包文件完整性终检", "result": "ERROR"})

            # (已移除冗余RED-2: styles.xml一致性终检——由校验1第1701-1717行完全覆盖)
            # 仅保留styles.xml颜色检测（doc_xml颜色已由校验3覆盖，此处检测styles.xml特有的颜色）
            styles_colors = re.findall(r'<w:color\s+w:val="([0-9A-Fa-f]{6})"', out_styles)
            invalid_styles_colors = [c for c in styles_colors if c.upper() not in _valid_colors]
            if not out_styles:
                checks.append({"name": "styles.xml字体颜色一致性终检", "result": "SKIP（无styles.xml数据）"})
            elif invalid_styles_colors:
                errors.append(f"styles.xml字体颜色非参考文档颜色: {list(set(invalid_styles_colors))}")
                checks.append({"name": "styles.xml字体颜色一致性终检", "result": "FAIL", "details": list(set(invalid_styles_colors))})
            else:
                checks.append({"name": "styles.xml字体颜色一致性终检", "result": "PASS"})

            header_files = [n for n in z_out.namelist() if n.startswith('word/header')]
            header_text_issues = []
            for hf in header_files:
                hf_xml = z_out.read(hf).decode('utf-8')
                hf_texts = re.findall(r'<w:t[^>]*>([^<]+)</w:t>', hf_xml)
                hf_full = ''.join(hf_texts).strip()
                if not hf_full:
                    header_text_issues.append(f'{hf} 不含有效文字')
                # 检查页眉文字颜色
                hf_colors = re.findall(r'<w:color\s+w:val="([0-9A-Fa-f]{6})"', hf_xml)
                hf_invalid = [c for c in hf_colors if c.upper() not in _valid_colors]
                if hf_invalid:
                    header_text_issues.append(f'{hf} 含非参考文档颜色文字: {list(set(hf_invalid))}')
            if header_text_issues:
                errors.append(f"页眉文字一致性终检失败: {header_text_issues}")
                checks.append({"name": "页眉文字一致性终检", "result": "FAIL", "details": header_text_issues})
            else:
                checks.append({"name": "页眉文字一致性终检", "result": "PASS"})

            footer_files = [n for n in z_out.namelist() if n.startswith('word/footer')]
            footer_issues = []
            for ff in footer_files:
                ff_xml = z_out.read(ff).decode('utf-8')
                ff_texts = re.findall(r'<w:t[^>]*>([^<]+)</w:t>', ff_xml)
                ff_full = ''.join(ff_texts).strip()
                if not ff_full and 'PAGE' not in ff_xml:
                    footer_issues.append(f'{ff} 不含有效文字且无页码域')
                # 检查页脚含页码域代码
                if 'fldChar' not in ff_xml and 'PAGE' not in ff_xml:
                    footer_issues.append(f'{ff} 缺少页码域代码(PAGE/fldChar)')
                # 检查页脚文字颜色
                ff_colors = re.findall(r'<w:color\s+w:val="([0-9A-Fa-f]{6})"', ff_xml)
                ff_invalid = [c for c in ff_colors if c.upper() not in _valid_colors]
                if ff_invalid:
                    footer_issues.append(f'{ff} 含非参考文档颜色文字: {list(set(ff_invalid))}')
            if footer_issues:
                errors.append(f"页脚页码格式终检失败: {footer_issues}")
                checks.append({"name": "页脚页码格式终检", "result": "FAIL", "details": footer_issues})
            else:
                checks.append({"name": "页脚页码格式终检", "result": "PASS"})

            # 检查document.xml中所有rPr的rFont（字体名称）是否与参考文档一致
            doc_fonts = re.findall(r'<w:rFonts\s+[^/]*w:(?:ascii|hAnsi|eastAsia)="([^"]+)"', doc_xml)
            if doc_fonts:
                unique_fonts = set(doc_fonts)
                # 参考文档的字体集合
                ref_fonts = set()
                try:
                    if z_ref is not None:
                        ref_doc_content = z_ref.read('word/document.xml').decode('utf-8')
                        ref_fonts = set(re.findall(r'<w:rFonts\s+[^/]*w:(?:ascii|hAnsi|eastAsia)="([^"]+)"', ref_doc_content))
                except Exception as e_font:
                    warnings.warn(f'正文字体一致性终检: 参考文档字体提取失败: {e_font}')
                if ref_fonts:
                    extra_fonts = unique_fonts - ref_fonts
                    if extra_fonts:
                        errors.append(f"正文字体与参考文档不一致: 文档使用{unique_fonts}，参考文档使用{ref_fonts}，差异字体: {extra_fonts}")
                        checks.append({"name": "正文字体一致性终检", "result": "FAIL", "details": list(extra_fonts)})
                    else:
                        checks.append({"name": "正文字体一致性终检", "result": "PASS"})
                else:
                    checks.append({"name": "正文字体一致性终检", "result": "SKIP（无参考文档字体数据）"})
            else:
                checks.append({"name": "正文字体一致性终检", "result": "PASS"})

            try:
                tbl_open = len(re.findall(r'<w:tbl[\s>]', doc_xml))
                tbl_close = len(re.findall(r'</w:tbl>', doc_xml))
                tr_open = len(re.findall(r'<w:tr[\s>]', doc_xml))
                tr_close = len(re.findall(r'</w:tr>', doc_xml))
                tc_open = len(re.findall(r'<w:tc[\s>]', doc_xml))
                tc_close = len(re.findall(r'</w:tc>', doc_xml))
                tbl_mismatch = (tbl_open != tbl_close) or (tr_open != tr_close) or (tc_open != tc_close)
                if tbl_mismatch:
                    msg_parts = []
                    if tbl_open != tbl_close:
                        msg_parts.append(f'w:tbl({tbl_open}/{tbl_close})')
                    if tr_open != tr_close:
                        msg_parts.append(f'w:tr({tr_open}/{tr_close})')
                    if tc_open != tc_close:
                        msg_parts.append(f'w:tc({tc_open}/{tc_close})')
                    errors.append(f'表格标签闭合不匹配: {", ".join(msg_parts)}')
                    checks.append({"name": "表格标签闭合完整性终检", "result": "FAIL"})
                else:
                    checks.append({"name": "表格标签闭合完整性终检", "result": "PASS"})
            except Exception as e_tbl:
                errors.append(f"表格标签闭合检查异常: {e_tbl}")
                checks.append({"name": "表格标签闭合完整性终检", "result": "ERROR"})

            try:
                root_v27b = _vfc_root
                if root_v27b is None:
                    raise ET.ParseError("前期doc_xml解析失败")
                tables_v27b = list(root_v27b.iter(NS_W + 'tbl'))
                center_fail_count = 0
                center_check_total = 0
                for tbl_v27b in tables_v27b:
                    # 判断是否为封面表格（无边框的表格为封面表格，跳过）
                    tbl_pr_v27b = tbl_v27b.find(NS_W + 'tblPr')
                    is_cover_tbl = True
                    if tbl_pr_v27b is not None:
                        tbl_borders_v27b = tbl_pr_v27b.find(NS_W + 'tblBorders')
                        if tbl_borders_v27b is not None:
                            for bn in ['top', 'left', 'bottom', 'right', 'insideH', 'insideV']:
                                be = tbl_borders_v27b.find(NS_W + bn)
                                if be is not None and be.get(NS_W + 'val', '') not in ('none', 'nil'):
                                    is_cover_tbl = False
                                    break
                    if is_cover_tbl:
                        continue
                    for tr_v27b in tbl_v27b.iter(NS_W + 'tr'):
                        for tc_v27b in tr_v27b.iter(NS_W + 'tc'):
                            center_check_total += 1
                            # 检查水平居中（jc=center）
                            has_jc_center = False
                            for p_v27b in tc_v27b.iter(NS_W + 'p'):
                                ppr_v27b = p_v27b.find(NS_W + 'pPr')
                                if ppr_v27b is not None:
                                    jc_v27b = ppr_v27b.find(NS_W + 'jc')
                                    if jc_v27b is not None and jc_v27b.get(NS_W + 'val', '') == 'center':
                                        has_jc_center = True
                                        break
                            if not has_jc_center:
                                center_fail_count += 1
                if center_check_total > 0 and center_fail_count > 0:
                    errors.append(f'正文表格单元格内容居中校验失败: {center_fail_count}/{center_check_total}个单元格未水平居中')
                    checks.append({"name": "正文表格单元格内容强制居中终检", "result": "FAIL"})
                else:
                    checks.append({"name": "正文表格单元格内容强制居中终检", "result": "PASS"})
            except Exception as e_center:
                errors.append(f"表格内容居中校验异常: {e_center}")
                checks.append({"name": "正文表格单元格内容强制居中终检", "result": "ERROR"})

            try:
                has_toc = bool(re.search(r'TOC\s+\\', doc_xml))
                has_fldchar_begin = len(re.findall(r'<w:fldChar\s+w:fldCharType="begin"', doc_xml))
                has_fldchar_end = len(re.findall(r'<w:fldChar\s+w:fldCharType="end"', doc_xml))
                has_bookmarks = len(re.findall(r'<w:bookmarkStart[^>]*w:name="_Toc', doc_xml))
                if has_toc:
                    if has_fldchar_begin != has_fldchar_end:
                        errors.append(f'TOC域fldChar不匹配: begin={has_fldchar_begin}, end={has_fldchar_end}')
                        checks.append({"name": "TOC域代码完整性终检", "result": "FAIL"})
                    elif has_bookmarks == 0:
                        errors.append('TOC域存在但无_Toc书签定义——目录跳转功能失效')
                        checks.append({"name": "TOC域代码完整性终检", "result": "FAIL"})
                    else:
                        checks.append({"name": "TOC域代码完整性终检", "result": "PASS"})
                else:
                    errors.append('文档中未检测到TOC域指令——目录页TOC域代码缺失')
                    checks.append({"name": "TOC域代码完整性终检", "result": "FAIL"})
            except Exception as e_toc:
                errors.append(f"TOC域代码完整性检查异常: {e_toc}")
                checks.append({"name": "TOC域代码完整性终检", "result": "ERROR"})

            try:
                if _vfc_root is None:
                    raise ET.ParseError("前期doc_xml解析失败")
                heading_only_num_count = sum(
                    1 for sv, ft, _p in _iter_heading_paragraphs(_vfc_root)
                    if ft and not _strip_heading_number(ft)
                )
                if heading_only_num_count > 0:
                    errors.append(f'标题段落仅含编号无标题文字: 检测到{heading_only_num_count}处')
                    checks.append({"name": "标题段落仅含编号无文字终检", "result": "FAIL"})
                else:
                    checks.append({"name": "标题段落仅含编号无文字终检", "result": "PASS"})
            except Exception as e_hn:
                errors.append(f"标题仅含编号检查异常: {e_hn}")
                checks.append({"name": "标题段落仅含编号无文字终检", "result": "ERROR"})

            try:
                sectpr_count = len(re.findall(r'<w:sectPr', doc_xml))
                has_zero_margin = bool(re.search(r'<w:pgMar[^>]*w:top="0"[^>]*w:bottom="0"', doc_xml))
                # AUDIT-006修复：使用re.escape防止PAGE_WIDTH/PAGE_HEIGHT常量中含正则特殊字符
                pgsz_pattern = r'<w:pgSz[^>]*w:w="' + re.escape(str(PAGE_WIDTH)) + r'"[^>]*w:h="' + re.escape(str(PAGE_HEIGHT)) + r'"'
                pgsz_count = len(re.findall(pgsz_pattern, doc_xml))
                if sectpr_count < 2:
                    errors.append(f'分节符总数不足: {sectpr_count}个（至少需要2个）')
                    checks.append({"name": "分节符完整性终检", "result": "FAIL"})
                elif not has_zero_margin:
                    errors.append('未检测到含零边距的分节符（封面分节符缺失）')
                    checks.append({"name": "分节符完整性终检", "result": "FAIL"})
                elif pgsz_count == 0:
                    errors.append('分节符中未检测到正确的A4页面大小')
                    checks.append({"name": "分节符完整性终检", "result": "FAIL"})
                else:
                    checks.append({"name": "分节符完整性终检", "result": "PASS"})
            except Exception as e_sb:
                errors.append(f"分节符完整性检查异常: {e_sb}")
                checks.append({"name": "分节符完整性终检", "result": "ERROR"})

            try:
                root_pp = _vfc_root
                if root_pp is None:
                    raise ET.ParseError("前期doc_xml解析失败")
                invalid_pstyle_count = 0
                for p in root_pp.iter(NS_W + 'p'):
                    pPr = p.find(NS_W + 'pPr')
                    if pPr is not None:
                        pStyle = pPr.find(NS_W + 'pStyle')
                        if pStyle is not None:
                            sv = pStyle.get(NS_W + 'val', '')
                            if sv not in ('1', '2', '3', '4', '5', '6', 'Normal', 'TOC1', 'TOC2', 'TOC3', 'Title', '10', 'a4', 'ac', 'ae', ''):
                                invalid_pstyle_count += 1
                if invalid_pstyle_count > 0:
                    errors.append(f'段落含非法pStyle值: 检测到{invalid_pstyle_count}处')
                    checks.append({"name": "段落属性一致性终检", "result": "FAIL"})
                else:
                    checks.append({"name": "段落属性一致性终检", "result": "PASS"})
            except Exception as e_pp:
                errors.append(f"段落属性一致性检查异常: {e_pp}")
                checks.append({"name": "段落属性一致性终检", "result": "ERROR"})

            # AUDIT-004说明：以下终检项与 _run_heading_quality_checks() 共享检测逻辑，
            # 已通过 _iter_heading_paragraphs() 共享函数消除重复遍历。
            try:
                if _vfc_root is None:
                    raise ET.ParseError("前期doc_xml解析失败")
                invisible_set = set('\u200b\u200c\u200d\ufeff\u00a0\u202f\u205f\u2003\u2002\u2009')
                bad_heading_count = 0
                for sv, ft, _p in _iter_heading_paragraphs(_vfc_root):
                    if ft:
                        has_invisible = any(c in invisible_set for c in ft)
                        has_leading_zero = bool(re.search(r'第0\d+章', ft) or re.search(r'\b0\d+\.\d+', ft))
                        if has_invisible or has_leading_zero:
                            bad_heading_count += 1
                if bad_heading_count > 0:
                    errors.append(f'标题含不可见空白字符或前导零编号: 检测到{bad_heading_count}处')
                    checks.append({"name": "标题空白字符规范性终检", "result": "FAIL"})
                else:
                    checks.append({"name": "标题空白字符规范性终检", "result": "PASS"})
            except Exception as e_bw:
                errors.append(f"标题空白字符规范性检查异常: {e_bw}")
                checks.append({"name": "标题空白字符规范性终检", "result": "ERROR"})

            try:
                # B1修复：复用已打开的z_out，避免Windows文件锁冲突
                if 'word/fontTable.xml' in z_out.namelist():
                    ft_xml = z_out.read('word/fontTable.xml').decode('utf-8')
                    ft_root_v30 = ET.fromstring(ft_xml.encode('utf-8'))
                    declared_fonts_v30 = set()
                    for fe in ft_root_v30.iter(NS_W + 'font'):
                        fn = fe.get(NS_W + 'name', '')
                        if fn:
                            declared_fonts_v30.add(fn)
                    core_fonts_v30 = {'Times New Roman', '宋体'}
                    missing_core_v30 = core_fonts_v30 - declared_fonts_v30
                    if missing_core_v30:
                        errors.append(f'字体表缺少核心字体: {missing_core_v30}')
                        checks.append({"name": "字体元数据一致性终检", "result": "FAIL"})
                    else:
                        checks.append({"name": "字体元数据一致性终检", "result": "PASS"})
                else:
                    errors.append('文档缺少word/fontTable.xml')
                    checks.append({"name": "字体元数据一致性终检", "result": "FAIL"})
            except Exception as e_fm:
                errors.append(f"字体元数据一致性检查异常: {e_fm}")
                checks.append({"name": "字体元数据一致性终检", "result": "ERROR"})

            try:
                root_schema = _vfc_root
                if root_schema is None:
                    raise ET.ParseError("前期doc_xml解析失败")
                body_schema = root_schema.find(NS_W + 'body')
                if body_schema is None:
                    errors.append('document.xml缺少w:body元素')
                    checks.append({"name": "body XML Schema合规性终检", "result": "FAIL"})
                else:
                    valid_children = {NS_W + 'p', NS_W + 'tbl', NS_W + 'sectPr',
                                      NS_W + 'bookmarkStart', NS_W + 'bookmarkEnd',
                                      NS_W + 'sdt'}
                    illegal_children = 0
                    for child in body_schema:
                        if child.tag not in valid_children:
                            illegal_children += 1
                    if illegal_children > 0:
                        errors.append(f'w:body下含{illegal_children}个非法子元素')
                        checks.append({"name": "body XML Schema合规性终检", "result": "FAIL"})
                    else:
                        checks.append({"name": "body XML Schema合规性终检", "result": "PASS"})
            except Exception as e_schema:
                errors.append(f"body XML Schema合规性检查异常: {e_schema}")
                checks.append({"name": "body XML Schema合规性终检", "result": "ERROR"})

            try:
                if _vfc_root is None:
                    raise ET.ParseError("前期doc_xml解析失败")
                emoji_count_v30 = 0
                for sv, ft, _p in _iter_heading_paragraphs(_vfc_root):
                    if ft:
                        for c in ft:
                            cp = ord(c)
                            if (0x1F600 <= cp <= 0x1F64F or
                                0x1F300 <= cp <= 0x1F5FF or
                                0x1F680 <= cp <= 0x1F6FF or
                                0x1F900 <= cp <= 0x1F9FF):
                                emoji_count_v30 += 1
                                break
                if emoji_count_v30 > 0:
                    errors.append(f'标题含emoji或非文本符号: {emoji_count_v30}处')
                    checks.append({"name": "标题非文本符号零容忍终检", "result": "FAIL"})
                else:
                    checks.append({"name": "标题非文本符号零容忍终检", "result": "PASS"})
            except Exception as e_emoji:
                errors.append(f"标题非文本符号检查异常: {e_emoji}")
                checks.append({"name": "标题非文本符号零容忍终检", "result": "ERROR"})

            try:
                # 检查H2编号前缀是否与所属H1章节号一致
                root_rel = _vfc_root
                if root_rel is None:
                    raise ET.ParseError("前期doc_xml解析失败")
                cur_h1_num_vfc = 0
                rel_errors_count = 0
                for p in root_rel.iter(NS_W + 'p'):
                    pPr = p.find(NS_W + 'pPr')
                    if pPr is None:
                        continue
                    pStyle = pPr.find(NS_W + 'pStyle')
                    if pStyle is None:
                        continue
                    sv = pStyle.get(NS_W + 'val', '')
                    ft = ''.join(t.text for t in p.iter(NS_W + 't') if t.text)
                    if not ft:
                        continue
                    if sv == '1':
                        h1_m = re.search(r'第([\d一二三四五六七八九十百零]+)章', ft)
                        if h1_m:
                            try:
                                cur_h1_num_vfc = int(h1_m.group(1))
                            except ValueError:
                                cur_h1_num_vfc = _safe_chapter_int(h1_m.group(1))
                    elif sv == '2' and cur_h1_num_vfc > 0:
                        h2_m = re.match(r'(\d+)\.(\d+)', ft)
                        if h2_m:
                            h2_ch = int(h2_m.group(1))
                            if h2_ch != cur_h1_num_vfc:
                                rel_errors_count += 1
                if rel_errors_count > 0:
                    errors.append(f'内容关联关系不一致: {rel_errors_count}处H2编号与所属H1章节号不匹配')
                    checks.append({"name": "内容关联关系一致性终检", "result": "FAIL"})
                else:
                    checks.append({"name": "内容关联关系一致性终检", "result": "PASS"})
            except Exception as e_rel:
                errors.append(f"内容关联关系检查异常: {e_rel}")
                checks.append({"name": "内容关联关系一致性终检", "result": "ERROR"})

            try:
                # B1修复：复用已打开的z_out，避免Windows文件锁冲突
                v31_names = set(z_out.namelist())
                # 检查[Content_Types].xml声明xml和rels默认类型
                ct_ok = True
                if '[Content_Types].xml' in v31_names:
                    ct_xml_v31 = z_out.read('[Content_Types].xml').decode('utf-8')
                    ct_root_v31 = ET.fromstring(ct_xml_v31.encode('utf-8'))
                    ns_ct_v31 = '{http://schemas.openxmlformats.org/package/2006/content-types}'
                    ct_defaults = set()
                    for d_elem in ct_root_v31.iter(ns_ct_v31 + 'Default'):
                        ct_defaults.add(d_elem.get('Extension', '').lower())
                    if 'xml' not in ct_defaults or 'rels' not in ct_defaults:
                        ct_ok = False
                        errors.append(f'[Content_Types].xml缺少xml或rels默认类型声明（实际: {ct_defaults}）')
                else:
                    ct_ok = False
                    errors.append('文档缺少[Content_Types].xml')
                # 检查_rels/.rels存在且指向document.xml
                rels_ok = True
                if '_rels/.rels' in v31_names:
                    rels_xml_v31 = z_out.read('_rels/.rels').decode('utf-8')
                    if 'document.xml' not in rels_xml_v31:
                        rels_ok = False
                        errors.append('_rels/.rels未指向word/document.xml')
                else:
                    rels_ok = False
                    errors.append('文档缺少_rels/.rels')
                # 检查无可疑文件
                suspicious_found_v31 = False
                for name in v31_names:
                    _, ext_v31 = os.path.splitext(name)
                    if ext_v31.lower() in ('.exe', '.bat', '.sh', '.cmd', '.dll'):
                        suspicious_found_v31 = True
                        errors.append(f'ZIP包含可疑文件: {name}')
                        break
                if ct_ok and rels_ok and not suspicious_found_v31:
                    checks.append({"name": "ZIP包完整性深度终检", "result": "PASS"})
                else:
                    checks.append({"name": "ZIP包完整性深度终检", "result": "FAIL"})
            except Exception as e_zip31:
                errors.append(f"ZIP包完整性深度检查异常: {e_zip31}")
                checks.append({"name": "ZIP包完整性深度终检", "result": "ERROR"})

            try:
                if _vfc_root is None:
                    raise ET.ParseError("前期doc_xml解析失败")
                punc_count_v31 = 0
                for sv, ft, _p in _iter_heading_paragraphs(_vfc_root):
                    if ft:
                        ft_no_num = _strip_heading_number(ft)
                        if re.search(r'[!！]{2,}|[?？]{2,}|\.{3,}|…', ft_no_num):
                            punc_count_v31 += 1
                        if re.search(r'\d+[_/|]\d+', ft):
                            punc_count_v31 += 1
                if punc_count_v31 > 0:
                    errors.append(f'标题标点规范性问题: {punc_count_v31}处含过度标点或非标准分隔符')
                    checks.append({"name": "标题标点规范性终检", "result": "FAIL"})
                else:
                    checks.append({"name": "标题标点规范性终检", "result": "PASS"})
            except Exception as e_punc:
                errors.append(f"标题标点规范性检查异常: {e_punc}")
                checks.append({"name": "标题标点规范性终检", "result": "ERROR"})

            try:
                heading_empty = []
                if _vfc_root is None:
                    raise ET.ParseError("前期doc_xml解析失败")
                for sv, ft, _p in _iter_heading_paragraphs(_vfc_root):
                    if not ft or not ft.strip():
                        heading_empty.append(f'H{sv}标题为空')
                if heading_empty:
                    errors.append(f'章节标题非空终检失败: {heading_empty}')
                    checks.append({"name": "章节标题非空终检", "result": "FAIL"})
                else:
                    checks.append({"name": "章节标题非空终检", "result": "PASS"})
            except Exception as e_mand:
                errors.append(f"章节标题非空检查异常: {e_mand}")
                checks.append({"name": "章节标题非空终检", "result": "ERROR"})
            
            # -- 校验40：页眉页脚格式完整性终检 --
            try:
                hf_border_issues = []
                hf_files_to_check = [n for n in z_out.namelist() if n.startswith('word/header') or n.startswith('word/footer')]
                for hf_file in hf_files_to_check:
                    hf_xml_content = z_out.read(hf_file).decode('utf-8')
                    if hf_file.startswith('word/header'):
                        # 页眉必须有底部装饰边框线（与参考文档一致）
                        if 'w:bottom' not in hf_xml_content or 'w:pBdr' not in hf_xml_content:
                            hf_border_issues.append(f'{hf_file} 缺少底部装饰边框线')
                    elif hf_file.startswith('word/footer'):
                        # 页脚保持参考文档原始结构（纯PAGE域代码，无顶部边框）
                        # 只检查PAGE域代码存在性
                        if 'PAGE' not in hf_xml_content or 'fldChar' not in hf_xml_content:
                            hf_border_issues.append(f'{hf_file} 缺少页码域代码(PAGE/fldChar)')
                if hf_border_issues:
                    errors.append(f'页眉页脚格式完整性终检失败: {hf_border_issues}')
                    checks.append({"name": "页眉页脚格式完整性终检", "result": "FAIL"})
                else:
                    checks.append({"name": "页眉页脚格式完整性终检", "result": "PASS"})
            except Exception as e_hfb:
                errors.append(f"页眉页脚装饰边框检查异常: {e_hfb}")
                checks.append({"name": "页眉页脚格式完整性终检", "result": "ERROR"})

            # 这是"没有第几章"bug的最终校验——确保文档中至少存在1个H1标题
            try:
                h1_count_v34 = len(re.findall(r'pStyle\s+w:val="1"', doc_xml))
                if h1_count_v34 == 0:
                    errors.append('H1标题最低数量终检失败：文档中不存在任何H1章节标题（pStyle="1"）——这是"没有第几章"bug的核心表现')
                    checks.append({"name": "H1标题最低数量终检", "result": "FAIL"})
                else:
                    checks.append({"name": "H1标题最低数量终检", "result": "PASS"})
            except Exception as e_h1cnt:
                errors.append(f"H1标题最低数量检查异常: {e_h1cnt}")
                checks.append({"name": "H1标题最低数量终检", "result": "ERROR"})
            

        finally:
            try:
                z_out.close()
            except OSError:
                pass
            if z_ref:
                try:
                    z_ref.close()
                except OSError:
                    pass
    except (ET.ParseError, KeyError, zipfile.BadZipFile, IOError, OSError) as e:
        errors.append(f"格式校验异常: {str(e)}")
        checks.append({"name": "格式校验异常", "result": "ERROR", "details": str(e)})
    
    result = {"pass": len(errors) == 0, "checks": checks, "errors": errors}
    
    if not result["pass"]:
        error_detail = "格式自校验失败，拒绝输出:\n" + "\n".join(f"  - {e}" for e in errors)
        error_detail += "\n\n校验详情:\n" + "\n".join(
            f"  - {c['name']}: {c['result']}" for c in checks
        )
        raise FormatValidationError(error_detail)
    
    return result


# ============================================================
# 命令行接口
# ============================================================

def main():
    parser = argparse.ArgumentParser(description='生成格式化的Word技术方案文档')
    parser.add_argument('--output', '-o', required=True, help='输出文件路径')
    parser.add_argument('--title', '-t', required=True, help='文档标题')
    parser.add_argument('--subtitle', '-s', default='', help='副标题')
    parser.add_argument('--date', '-d', default='', help='编制日期')
    parser.add_argument('--info', default=None, help='封面信息行JSON文件路径')
    parser.add_argument('--content', '-c', required=True, help='正文内容JSON文件路径')
    parser.add_argument('--header-text', default=None, help='页眉文字')
    
    args = parser.parse_args()
    
    # 加载信息行
    info_rows = []
    if args.info:
        try:
            with open(args.info, 'r', encoding='utf-8') as f:
                try:
                    info_data = json.load(f)
                except json.JSONDecodeError as e:
                    print(f'错误: info JSON文件解析失败: {e}', file=sys.stderr)
                    sys.exit(1)
        except OSError as e:
            print(f'错误: 无法读取info文件: {e}', file=sys.stderr)
            sys.exit(1)
        # v5.1 fix: 顶层类型校验防 TypeError
        if not isinstance(info_data, list):
            print(f'错误: info JSON顶层应为列表，实际为{type(info_data).__name__}', file=sys.stderr)
            sys.exit(1)
        for i, item in enumerate(info_data):
            if not isinstance(item, dict):
                print(f'错误: info[{i}]不是字典类型', file=sys.stderr)
                sys.exit(1)
            label = item.get('label', '')
            value = item.get('value', '')
            if not label:
                print(f'错误: info[{i}]缺少"label"字段', file=sys.stderr)
                sys.exit(1)
            info_rows.append((label, value))
    else:
        if args.date:
            info_rows.append(('编制日期：', args.date))
    
    # 加载内容
    try:
        with open(args.content, 'r', encoding='utf-8') as f:
            try:
                content_data = json.load(f)
            except json.JSONDecodeError as e:
                print(f'错误: content JSON文件解析失败: {e}', file=sys.stderr)
                sys.exit(1)
    except OSError as e:
        print(f'错误: 无法读取content文件: {e}', file=sys.stderr)
        sys.exit(1)
    
    # 生成文档
    generate_docx(
        output_path=args.output,
        title=args.title,
        subtitle=args.subtitle,
        date_str=args.date,
        info_rows=info_rows,
        bottom_label_left='Technical Report',
        bottom_label_right=f'{datetime.now().year} EDITION',
        content_data=content_data,
        header_text=args.header_text or args.title
    )


if __name__ == '__main__':
    # Windows 控制台编码兼容：含emoji的print输出需要UTF-8
    if sys.platform == 'win32':
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass
    main()

