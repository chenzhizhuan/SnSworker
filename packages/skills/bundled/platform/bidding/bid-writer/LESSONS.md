# Lessons learned for bid-writer


## 2026-08-11 16:27
商务材料自动填充的 5 个关键坑（已固化进 references/business-materials-filling.md）：① 图片归属必须按 word/document.xml 的 r:embed 文档流顺序分组，不能靠文件名猜（一个段落可含多张图）；② 透明 PNG 转 JPG 必须先转 RGB 铺白底，否则变黑；③ 扫描件 PNG 必须压缩（Pillow 最长边1600px quality=82，27张20MB→3MB），否则 docx 超平台上传限制；④ 验证图片是否真的进 docx 要按正文 Heading 样式定位章节区间（跳过目录区）数 <w:drawing>，只看 word/media 文件数不可靠；⑤ 渲染大 md（30万+字符）用 subprocess + timeout 280s，importlib 内联会 30s 超时；文件写回原路径不刷新下载链接，需写新文件名或工作区根目录。
