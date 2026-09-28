# Lessons learned for tender-analysis


## 2026-08-06 15:25  (conversation: conv_1785998605943_tspava)
【首稿即达标】生成投标文件框架/分析报告的 .docx 时，绝不能用 renderDocx/renderDocxFromFile 等通用 Markdown 渲染器交付最终文档——它们不会生成 Word 内置 Heading 样式、大纲级别和目录页，交付出去就是"无目录、标题全是正文样式"的残缺版，只能靠用户自查后返工。正确做法：用 python-docx 直接写 OOXML（标题用 style=f"Heading {level}" + w:outlineLvl，目录用普通段落真实渲染进正文，正文宋体+TNR 小四 12pt、1.5 倍行距、首行缩进 2 字符），生成后必须回读自检（Heading 数量、章节齐全、顺序递增、目录存在、outlineLvl），全部通过才给用户下载链接。skill v1.1 已把此规则固化为"首稿达标闸门"并用 scripts/verify_docx.py 强制校验。

## 2026-08-12 08:48
制度/管理办法类 docx 生成自检补充：① Heading 样式的大纲级别定义在 styles.xml 的样式层（w:styleId="Heading1" 内含 w:outlineLvl），不在段落 pPr 里，回读自检要查 styles.element.xml 而不是段落 XML，否则误报"无大纲级别"；② 页脚 PAGE/NUMPAGES 域在 section.footer._element.xml 里，不在 doc.paragraphs 中，自检页脚需单独读 footer 的 XML；③ 封面无页码+正文从1起：用 doc.add_section(WD_SECTION.NEW_PAGE) 分节，在第二节 sectPr 加 <w:pgNumType w:start="1"/>，并把 footer.is_linked_to_previous=False；④ 目录用 TOC \o "1-1" \h \z \u 域，separate 与 end 之间放章节名静态占位文本，用户打开后 Ctrl+A→F9 自动生成带页码目录；⑤ 附件表格第一列连续相同值用 cell.merge 纵向合并，美化评分表。
