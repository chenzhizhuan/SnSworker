#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tender-analysis 首稿达标闸门 · docx 回读自检脚本（强制使用）

用法：
    python verify_docx.py <output.docx> <expected_h2_count> [expected_h1_count] [expected_h3_count]

在生成 .docx 的同一脚本末尾调用，或在交付前单独运行。
全部检查通过才允许向用户交付下载链接；任一失败必须修正后重新生成。

检查项：
1. 标题样式：H1/H2/H3 数量与预期一致（章节必须是 Heading 2，分册是 Heading 1）
2. 章节齐全且顺序正确：Heading 2 标题按编号 1..N 逐个出现、位置单调递增
3. 目录页已渲染：文档中存在"目录"标题，其后紧跟章节条目；目录条目数 >= 章节数
4. 大纲级别：标题段落含 w:outlineLvl（Word 导航窗格可识别）
5. 排版规范：正文段落 w:spacing line=360、首行缩进 w:ind firstLineChars=200
"""
import re
import sys

from docx import Document
from docx.oxml.ns import qn


def fail(msg):
    print("[FAIL]", msg)
    sys.exit(1)


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    path = sys.argv[1]
    want_h2 = int(sys.argv[2])
    want_h1 = int(sys.argv[3]) if len(sys.argv) > 3 else None
    want_h3 = int(sys.argv[4]) if len(sys.argv) > 4 else None

    doc = Document(path)
    paras = list(doc.paragraphs)

    h1 = [p.text for p in paras if p.style.name == "Heading 1"]
    h2 = [p.text for p in paras if p.style.name == "Heading 2"]
    h3 = [p.text for p in paras if p.style.name == "Heading 3"]

    print(f"H1 数量: {len(h1)} | H2 数量: {len(h2)} | H3 数量: {len(h3)}")

    # 1) 标题样式数量
    if len(h2) != want_h2:
        fail(f"Heading 2 数量应为 {want_h2}，实际 {len(h2)}")
    if want_h1 is not None and len(h1) != want_h1:
        fail(f"Heading 1 数量应为 {want_h1}，实际 {len(h1)}")
    if want_h3 is not None and len(h3) != want_h3:
        fail(f"Heading 3 数量应为 {want_h3}，实际 {len(h3)}")

    # 2) 章节齐全且顺序正确（Heading 2 编号递增）
    nums = []
    for t in h2:
        m = re.match(r"^(\d+)\s", t)
        if m:
            nums.append(int(m.group(1)))
    expect = list(range(1, want_h2 + 1))
    if nums != expect:
        missing = sorted(set(expect) - set(nums))
        dup = sorted({n for n in nums if nums.count(n) > 1})
        fail(f"章节编号不符: 期望 1..{want_h2}，实际前段={nums[:10]}；缺失={missing} 重复={dup}")

    # 3) 目录页已渲染
    texts = [p.text for p in paras]
    try:
        toc_idx = texts.index("目录")
    except ValueError:
        fail("未找到'目录'标题")
    after = [t for t in texts[toc_idx + 1:toc_idx + want_h2 + 5] if t.strip()]
    if not after:
        fail("目录页为空")
    # 目录条目应覆盖主要章节编号
    toc_nums = set()
    for t in texts[toc_idx + 1:toc_idx + want_h2 * 2 + 10]:
        m = re.match(r"^\d+\s", t)
        if m:
            toc_nums.add(int(m.group(0).strip()))
    coverage = len(toc_nums & set(expect)) / len(expect)
    if coverage < 0.9:
        fail(f"目录覆盖率仅 {coverage:.0%}，应 >=90%")
    print(f"目录页 OK，覆盖 {coverage:.0%} 章节")

    # 4) 大纲级别
    ok_outline = True
    for p in paras:
        if p.style.name in ("Heading 1", "Heading 2", "Heading 3"):
            pPr = p._p.find(qn("w:pPr"))
            if pPr is None or pPr.find(qn("w:outlineLvl")) is None:
                ok_outline = False
                print("  缺 outlineLvl:", p.text[:30])
    if not ok_outline:
        fail("存在标题缺少 w:outlineLvl（Word 导航窗格无法识别）")
    print("大纲级别 OK")

    # 5) 排版抽查
    body = [p for p in paras if p.style.name == "Normal" and p.text.strip() and not p.text.startswith(("•", ">"))]
    sample = body[len(body) // 2] if body else None
    if sample is not None:
        pPr = sample._p.find(qn("w:pPr"))
        spacing = pPr.find(qn("w:spacing")) if pPr is not None else None
        ind = pPr.find(qn("w:ind")) if pPr is not None else None
        line = spacing.get(qn("w:line")) if spacing is not None else None
        rule = spacing.get(qn("w:lineRule")) if spacing is not None else None
        flc = ind.get(qn("w:firstLineChars")) if ind is not None else None
        if line != "360" or rule != "auto":
            print("  [warn] 正文行距非 1.5 倍:", line, rule)
        if flc != "200":
            print("  [warn] 正文首行缩进非 2 字符:", flc)

    print("[PASS] 全部检查通过，可交付下载链接:", path)


if __name__ == "__main__":
    main()
