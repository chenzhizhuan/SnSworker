---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '5e854205-a89c-4536-84e5-7e2f9a33e582'
  PropagateID: '5e854205-a89c-4536-84e5-7e2f9a33e582'
  ReservedCode1: 'ce4421fb-cb00-429e-98f1-24b172553182'
  ReservedCode2: 'ce4421fb-cb00-429e-98f1-24b172553182'
---

# 素材清单与生成指令

本文件记录党建PPT素材库的全部素材描述和AI生图指令。调用时按指令生成对应素材，确保风格一致。

---

## 模板

### 模板1：党课红金风格

- **配置文件**：`references/template-config-1.json`
- **页数**：20
- **适用场景**：支部党课、党建汇报、政治学习
- **配色**：中国红(#C00000) + 金色(#D4AF37)
- **页面结构**：封面 -> 目录 -> 4章节（各含过渡页+内容页） -> 结尾页
- **生成方式**：读取配置文件中的配色、字体、布局参数，用PptxGenJS生成
- **示例脚本**：`references/template-1-example.js`（20页完整 PptxGenJS 编译脚本，可直接 `node` 执行生成PPTX）
- **实际案例**：深学笃行习近平党建思想 — 学习贯彻2026年全国党建工作座谈会精神（2026年8月，20页，含5张AI配图）

### 模板2：电信改革汇报风格

- **配置文件**：`references/template-config-2.json`
- **页数**：24
- **适用场景**：改革汇报、经营分析、战略部署、年度总结
- **配色**：深蓝(#004488) + 品牌辅色
- **页面结构**：目录(3栏编号) -> 章节过渡页 -> 数据页(图表) -> 流程图页 -> 总结页
- **生成方式**：读取配置文件中的配色、字体、布局参数，用PptxGenJS生成
- **logo**：右上角放置中国电信+5G标识，需用户提供或从内部品牌库获取

### 模板3：电信品牌红风格（PDF还原式）

- **配置文件**：`references/template-config-3.json`
- **页数**：53（可按需裁剪）
- **适用场景**：产品介绍、技术分享、业务推广、燎原课件
- **配色**：电信品牌红(#C8102E) + 暖色渐变(橙#F29400/黄#FFCC00) + 品牌蓝(#005AAA)辅助
- **页面结构**：封面 -> 目录 -> 4大模块(各含过渡页+内容页) -> 核心价值对比 -> 安全APN -> 综合方案 -> 谢谢页
- **生成方式**：读取配置文件，用PptxGenJS逐页还原PDF布局
- **logo**：右上角中国电信+5G标识
- **设计特色**：
  - 标题左侧双红色方块错位装饰 + 标题下方红-橙-黄三色渐变条
  - 白底卡片+浅灰边框，标题栏彩色填充
  - 圆角矩形流程节点+向右箭头连接
  - 表格：红底白字表头+粉白交替行
  - 底部全宽红色细线+右下角页码
  - 结尾页72pt红色"谢谢!"+底部三色装饰条
- **辅助函数**：addBrand, addTitleBar, addBottomLine, addCard, addFlowNode, addArrowRight, makeTable, addBackLink
- **实际案例**：多网融合服务产品与案例分享（53页，3.29MB，源PDF 1:1还原）

### 模板4：复杂ICT项目自主交付模板

- **配置文件**：`references/template-config-4.json`
- **页数**：7
- **适用场景**：ICT项目自主交付、售前方案、CRM下单操作、全国派单统计、交付规划时间线
- **配色**：电信品牌红(#C81000) + 红橙黄渐变(橙#F29400/黄#FFCC00) + 品牌蓝(#005AAA)辅助
- **页面结构**：封面 -> 任务背景及目标 -> 自主交付优势(2×2网格) -> 泳道流程图 -> CRM下单操作 -> 全国派单统计(表格) -> 规划时间线
- **生成方式**：读取配置文件，用PptxGenJS逐页还原截图布局
- **logo**：封面左上中国电信logo，右上角5G标识（蓝5+红G+3个橙色信号点）
- **设计特色**：
  - 封面底部装饰：S形飘逸绸带（从源截图裁剪，4-5层半透明红橙黄渐变，覆盖左下角约48%宽/30%高，右端自然淡入白底）
  - 封面左上角：从源截图裁剪的真实中国电信logo（蓝e标识+中英文文字）
  - 半闭合边框：四角留缺口(gap=0.3)，线粗0.014，色#A82800
  - 红色虚线卡片：模拟截图/表单区域，虚线边框
  - 泳道流程图：5条泳道+流程节点框+菱形判断框+红/橙/绿/蓝多色箭头
  - 表格：表头/总计行淡蓝#DCE9F5填充
  - 时间线：横轴9节点(红/灰节点)+说明文字+橙色DICT块+分叉路径+卡片
  - 底部全宽红色细线+右下角灰色页码
- **辅助函数**：addBrand, addTitleBar, addHalfBorder, addRedDashCard, addSwimlane, addTimeline, addTable, addBottomLine
- **示例脚本**：`references/template-4-example.js`（7页完整 PptxGenJS 编译脚本，可直接 `node` 执行生成PPTX）
- **实际案例**：复杂ICT项目自主交付（7页，源截图还原度98%，封面绸带从源图裁剪）

### 模板5：AI+文旅商业模式PPT

- **配置文件**：`references/template-config-5.json`
- **页数**：9
- **适用场景**：AI+行业融合方案、文旅数字化、智能体平台介绍、数据集能力展示、行业大模型推广
- **配色**：电信品牌红(#C8102E) + 马卡龙色系(蓝#0066CC/绿#4CAF50/紫#9C27B0/黄#FFC107/青#00BCD4) + 深灰标题栏(#2C2C2C)
- **页面结构**：政策东风(2页) → 技术机遇(3页) → 价值重构(1页) → 核心燃料(1页) → 平台赋能(1页) → 标注服务(1页)
- **生成方式**：读取配置文件，用PptxGenJS逐页还原截图布局
- **设计特色**：
  - 白底为主，正红色(#C8102E)作为统一顶部装饰条+居中标题
  - 深灰色标题栏(#2C2C2C)用于政策解读类页面，白字标题
  - 蓝色标题栏(#005AAA)+白字用于8模块卡片标题区域
  - 马卡龙色系(蓝/绿/紫/黄)做模块区分和等级区分
  - 圆角矩形卡片(rectRadius=0.06)+浅灰/红/彩色细边框
  - 红色高亮关键词+标题下红色短线(宽0.35英寸)
  - 半闭合暗红边框(#A82820)用于数据集/要点模块框
  - 底部红色弧形块(圆角矩形模拟)+白色总结文字
  - S曲线图使用pptxgenjs原生line chart（4条sigmoid曲线+图例+公式）
  - 3级阶梯示意图(浅蓝→青蓝→淡紫+AI图标)表达技术演进
  - 5等级卡片(L1黄~L5紫+NOW标签)表达AGI阶段
  - 三栏G/B/C端配色(蓝/青绿/紫)+过去/现在对比
- **辅助函数**：addPageNum, addBrokenBorder, addRedBarTitle
- **示例脚本**：`references/template-5-example.js`（9页完整 PptxGenJS 编译脚本，可直接 `node` 执行生成PPTX）
- **实际案例**：AI+文旅商业模式PPT（9页，413KB，源截图逐页还原，QA检查通过）

### 模板6：教育产品解决方案风格

- **配置文件**：`references/template-config-6.json`
- **页数**：29
- **适用场景**：教育产品培训、教育解决方案宣贯、高校/教育局产品推介、教育AI平台介绍、AI实训方案汇报
- **配色**：电信深红(#C00000) + 深蓝信息底(#1F2A44) + 金色强调(#F2C14E) + 5色多类别标签
- **页面结构**：封面 -> 目录 -> 章节过渡(全屏图) -> 6格痛点卡片 -> 产品矩阵 -> 全屏截图系列(13页) -> 矩阵网格 -> MCP穿透 -> MaaS平台 -> AI实训系列 -> 目录 -> 3个案例 -> 目录 -> 三列市场对比 -> 商业模式 -> 决策链条 -> FAQ四列 -> 尾页
- **生成方式**：读取配置文件中的配色、字体、布局参数，用PptxGenJS生成
- **设计特色**：
  - 编号卡片2×3网格：浅蓝灰底(#F7F8FA)+顶部装饰条(红/深蓝交替)+编号+图标容器+标签+标题+说明，四层信息层级
  - 全屏截图模式(45%页面)：1张大图(12.25in宽)占页面90%+面积，仅配标题栏，产品展示最高频版式
  - 深蓝结论栏：#1F2A44全幅底+金色(#F2C14E)标签+白色居中粗体文字，用于核心判断汇总
  - FAQ卡片：4列并排，左侧垂直红色色条(0.083in宽)+Q&A问答式
  - 三列市场对比：编号+产品组合+切入方式，配水平/垂直装饰线
  - 多维矩阵网格：70+AUTO_SHAPE构成维度矩阵(如7维权限治理)，配水平线分行
  - 5色标签体系：绿#22C55E/橙#F59E0B/蓝#3B82F6/紫#8B5CF6/粉#EC4899，用于多类别区分
  - 双字体体系：微软雅黑(标题/正文)+MiSans(卡片/编号/说明)，信息层级丰富
  - 右下角Noto Serif SC水印统一所有页面
- **辅助函数**：addTitle, addWatermark, addNumberedCard, addConclusionBar, addFullScreenshot, addFAQCard, addThreeColumnCompare, addMatrixGrid, addContentsPage, addDividerLine
- **实际案例**：教育产品及解决方案培训（中电信人工智能科技有限公司，2026年8月，29页，525个shape）

---

## 插图生成指令

所有插图均使用AI生图，以下为经过验证的prompt（已规避政治符号触发安全策略）。

### 党课红金系列 - 章节配图（4:3）

| 名称 | 用途 | prompt |
|------|------|--------|
| 封面-红金丝绸主视觉 | 封面页全幅背景 | `A red and gold silk fabric background, Chinese red (#C00000) silk with golden (#D4AF37) embroidery patterns, elegant drapery, 16:9 aspect ratio, vector illustration style, flat design, no text, no flags, no political symbols, decorative background for presentation slide` |
| 理论-金光书卷 | 理论学习章节 | `An ancient Chinese book scroll glowing with golden light, traditional bamboo scroll unfurled with golden (#D4AF37) rays emanating, Chinese red (#C00000) silk backing, 4:3 aspect ratio, vector illustration style, flat design, no text, no flags, no political symbols, pure white background` |
| 初心-金色红心 | 初心使命章节 | `A golden heart symbol with red glow, metallic gold (#D4AF37) heart shape with Chinese red (#C00000) aura, warm and solemn atmosphere, 4:3 aspect ratio, vector illustration style, flat design, no text, no flags, no political symbols, pure white background` |
| 治党-金色盾牌 | 从严治党章节 | `A golden shield emblem, metallic gold (#D4AF37) shield with Chinese red (#C00000) accents, protective and authoritative feel, 4:3 aspect ratio, vector illustration style, flat design, no text, no flags, no political symbols, pure white background` |
| 担当-红绸日出 | 党员担当章节 | `Red silk ribbon flowing against a golden sunrise, Chinese red (#C00000) silk draping with golden (#D4AF37) sun rising behind, hopeful and dynamic atmosphere, 4:3 aspect ratio, vector illustration style, flat design, no text, no flags, no political symbols, pure white background` |

### 党课红金系列 - 装饰矢量素材（1:1）

| 名称 | 用途 | prompt |
|------|------|--------|
| 红色飘带 | 页面装饰、分隔线、角落点缀 | `A red silk ribbon flowing gracefully, Chinese red color (#C00000) with gold (#D4AF37) edge trim, elegant curved drapery, vector illustration style, flat design, clean lines, no text, no flags, no political symbols, pure white background, decorative element for presentation slide` |
| 金色五角星 | 标题旁装饰、列表标记 | `A golden five-pointed star, metallic gold (#D4AF37) with subtle red (#C00000) glow outline, clean geometric shape, vector illustration style, flat design, no text, no flags, no political symbols, pure white background, decorative element for presentation slide` |
| 华表剪影 | 封面/结尾装饰 | `A Chinese Huabiao ornamental column silhouette, traditional stone monument pillar with cloud pattern capital, golden (#D4AF37) silhouette on pure white background, vector illustration style, flat design, clean lines, no text, no flags, no political symbols, decorative element for presentation slide` |
| 祥云纹饰 | 边角装饰、过渡页点缀 | `Traditional Chinese auspicious cloud patterns (Xiangyun), elegant swirling cloud motifs in Chinese red (#C00000) and gold (#D4AF37) colors, vector illustration style, flat design, clean decorative lines, no text, no flags, no political symbols, pure white background, decorative element for presentation slide` |
| 长城剪影 | 奋斗/使命主题 | `The Great Wall of China silhouette winding over mountains, golden (#D4AF37) outline with Chinese red (#C00000) accent, vector illustration style, flat design, clean lines, no text, no flags, no political symbols, pure white background, decorative element for presentation slide` |
| 书卷卷轴 | 理论学习/文件学习 | `A traditional Chinese scroll book unfurled, ancient bamboo scroll with golden (#D4AF37) rollers and Chinese red (#C00000) silk backing, vector illustration style, flat design, clean lines, no text, no flags, no political symbols, pure white background, decorative element for presentation slide` |
| 麦穗装饰 | 边框装饰、成果主题 | `Wheat ears decorative border element, golden (#D4AF37) wheat stalks with grains, symmetric arrangement, vector illustration style, flat design, clean lines, no text, no flags, no political symbols, pure white background, decorative element for presentation slide` |
| 山峰日出 | 奋斗/攀登/新征程 | `Mountain peaks with rising sun, layered silhouettes of mountain ranges in Chinese red (#C00000) with golden (#D4AF37) sun rays emanating from behind, vector illustration style, flat design, clean lines, no text, no flags, no political symbols, pure white background, decorative element for presentation slide` |

### 电信品牌

| 名称 | 用途 | 来源 |
|------|------|------|
| 中国电信+5G logo | 右上角品牌标识 | 需用户提供或从中国电信内部品牌库获取 |

---

## 生图参数建议

- **guidance_scale**: 7（平衡创意与指令遵循）
- **尺寸**：章节配图用4:3(2048x1536)或16:9(2048x1152)；装饰素材用1:1(2048x2048)
- **风格后缀**：所有prompt统一追加 `vector illustration style, flat design, no text, no flags, no political symbols, pure white background`
- **安全限制**：prompt中不得出现"党旗""党徽""党标"等政治符号词汇，否则会被安全策略拦截（400 OutputImageSensitiveContentDetected）

---

## 配色方案速查

### C2 党政红金

| 角色 | 色值 | 用途 |
|------|------|------|
| 主色 | #C00000 | 标题、强调 |
| 深红 | #8B0000 | 深色背景、过渡页 |
| 金色 | #D4AF37 | 装饰线、图标 |
| 浅金 | #F5DC8A | 浅金高亮 |
| 白色 | #FFFFFF | 主背景 |
| 暖白 | #FFF8F0 | 暖色区域背景 |
| 浅灰 | #F5F5F5 | 卡片背景 |
| 深灰 | #2C2C2C | 正文文字 |
| 中灰 | #666666 | 次要文字 |
| 浅灰边框 | #E0E0E0 | 卡片/分隔线 |

### C3 电信品牌蓝

| 角色 | 色值 | 用途 |
|------|------|------|
| 主色 | #004488 | 标题、章节标题 |
| 中蓝 | #4472C4 | 图表主色、链接 |
| 橙色 | #ED7D31 | 数据高亮 |
| 浅蓝 | #5B9BD5 | 图表辅色 |
| 绿色 | #70AD47 | 正面指标 |
| 金色 | #FFC000 | 突出指标 |
| 白色 | #FFFFFF | 主背景 |
| 浅灰 | #E7E6E6 | 卡片背景 |
| 深灰 | #2C2C2C | 正文文字 |
| 中灰蓝 | #44546A | 次要文字 |

### C4 电信品牌红+暖色渐变

| 角色 | 色值 | 用途 |
|------|------|------|
| 主色 | #C8102E | 标题、强调、表头填充 |
| 深红 | #8B0000 | 双方块装饰第二层 |
| 品牌蓝 | #005AAA | 辅助强调、流程节点 |
| 蓝 | #0066CC | 链接、流程节点 |
| 浅蓝 | #E3F2FD | 蓝色卡片背景 |
| 橙色 | #F29400 | 渐变条中段、数据高亮 |
| 黄色 | #FFCC00 | 渐变条尾段、装饰 |
| 绿色 | #009688 | 正向指标、流程节点 |
| 浅绿 | #E8F5E9 | 绿色卡片背景 |
| 青色 | #008080 | 辅助图表色 |
| 浅紫 | #F3E8FF | 紫色卡片背景 |
| 浅粉 | #FFF5F5 | 表格交替行背景 |
| 浅橙 | #FFF0E5 | 橙色卡片背景 |
| 白色 | #FFFFFF | 主背景、卡片底 |
| 深灰 | #333333 | 正文文字 |
| 中灰 | #666666 | 次要文字、副标题 |
| 浅灰 | #999999 | 页码、辅助文字 |
| 边框灰 | #E5E5E5 | 卡片/表格边框 |
| 卡片灰 | #F5F5F5 | 卡片背景 |
| 浅灰 | #F0F0F0 | 灰色卡片背景 |

### C5 电信品牌红+红橙黄渐变+品牌蓝（模板4专用）

| 角色 | 色值 | 用途 |
|------|------|------|
| 主色 | #C81000 | 标题、强调、渐变条首段 |
| 深红棕 | #A82820 | 半闭合边框 |
| 深红 | #8B0000 | 强调装饰 |
| 品牌蓝 | #005AAA | 辅助强调、流程节点 |
| 蓝色 | #0066CC | 流程节点 |
| 浅蓝 | #DCE9F5 | 表格表头/总计行填充 |
| 橙色 | #F29400 | 渐变条中段、DICT块、数据高亮 |
| 黄色 | #FFCC00 | 渐变条尾段、装饰 |
| 绿色 | #009688 | 流程节点 |
| 浅绿 | #E8F5E9 | 绿色卡片背景 |
| 浅粉 | #FFF5F5 | 表格交替行背景 |
| 白色 | #FFFFFF | 主背景、卡片底 |
| 深灰 | #333333 | 正文文字 |
| 中灰 | #666666 | 次要文字 |
| 浅灰 | #999999 | 页码、辅助文字 |
| 边框灰 | #C8C8C8 | 卡片/表格边框 |
| 卡片灰 | #F5F5F5 | 卡片背景 |

> AI生成

### C6 电信品牌红+马卡龙色系（模板5专用）

| 角色 | 色值 | 用途 |
|------|------|------|
| 主色 | #C8102E | 顶部装饰条、强调、标题栏 |
| 亮红 | #E60012 | 红色弧形块 |
| 深红 | #8B0000 | 深色强调 |
| 深灰标题 | #2C2C2C | 政策解读页标题栏背景 |
| 品牌蓝 | #005AAA | 卡片标题栏填充、辅助强调 |
| 蓝色 | #0066CC | G端配色、流程节点 |
| 浅蓝背景 | #E8F0FE | 浅蓝模块背景 |
| 浅蓝卡片 | #EDF4FD | G端卡片背景 |
| 绿色 | #4CAF50 | 正向指标 |
| 浅绿背景 | #E8F5E9 | 绿色卡片背景 |
| 青绿 | #009688 | B端配色 |
| 浅青绿背景 | #E0F2F1 | B端卡片背景 |
| 黄色 | #FFC107 | L1等级卡片 |
| 浅黄背景 | #FFF8E1 | 黄色卡片背景 |
| 紫色 | #9C27B0 | C端配色 |
| 浅紫背景 | #F3E5F5 | C端卡片背景 |
| 青色 | #00BCD4 | 辅助图表色 |
| 橙色 | #F29400 | 数据高亮、橙红标签 |
| 浅粉 | #FFF0F3 | 粉色标签背景 |
| 红棕 | #A82820 | 半闭合边框 |
| 橙红标签 | #E64A19 | 标注服务页圆角标签 |
| 白色 | #FFFFFF | 主背景、卡片底 |
| 深灰 | #333333 | 正文文字 |
| 中灰 | #666666 | 次要文字 |
| 浅灰 | #999999 | 页码、辅助文字 |
| 边框灰 | #CCCCCC | 卡片边框 |
| 卡片灰 | #F5F5F5 | 卡片背景 |

> AI生成

### C7 教育产品深红+深蓝信息底（模板6专用）

| 角色 | 色值 | 用途 |
|------|------|------|
| 主色 | #C00000 | 标题、编号、卡片标签强调 |
| 浅红底 | #FDECEC | 图标容器背景 |
| 深蓝底 | #1F2A44 | 结论栏背景、卡片装饰条交替色 |
| 金色强调 | #F2C14E | 结论栏标签、核心判断高亮 |
| 卡片底色 | #F7F8FA | 编号卡片背景(浅蓝灰) |
| 卡片底色2 | #F7F7F7 | 次要卡片背景 |
| 分隔灰 | #E5E5E5 | 卡片行间分隔线 |
| 正文深色 | #222222 | 卡片标题文字 |
| 正文色 | #3A3A3A | 主体内容文字 |
| 说明灰 | #5F6673 | 卡片说明文字、引导语 |
| 中灰 | #808080 | 副标题、水印 |
| 标签绿 | #22C55E | 多类别标签色1 |
| 标签橙 | #F59E0B | 多类别标签色2 |
| 标签蓝 | #3B82F6 | 多类别标签色3 |
| 标签紫 | #8B5CF6 | 多类别标签色4 |
| 标签粉 | #EC4899 | 多类别标签色5 |
| 白色 | #FFFFFF | 主背景、卡片底、结论栏文字 |
| 红色变体 | #C53030 | 品牌色块(矩阵图) |
| 暗红 | #8E0000 | 深色强调 |

> AI生成