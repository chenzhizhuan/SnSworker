---
name: novel-to-ghibli-comic
description: 'Convert any text or image into Studio Ghibli style illustrated comics. Read novel content, split into key scenes, write Ghibli aesthetic image prompts, generate illustrations via ImageGen, and assemble into a comic page using an HTML template. Use when the user wants to: (1) Turn novel/story text into manga/comic panels, (2) Create Ghibli-style illustrations from fiction, (3) Generate a visual comic from any narrative text, (4) Convert a book chapter or story passage into illustrated scenes, (5) Convert a screenshot, diagram, or chart image into a Ghibli-style comic. Triggers: "小说转漫画", "把这段故事画出来", "生成吉卜力风格漫画", "novel to comic", "小说变插画", "故事画成漫画", "文字转漫画", "吉卜力风格插图", "四格漫画", "做成四格漫画", "截图转漫画", "图片转漫画", "图片做成漫画", "万物皆可吉卜力".'
name_cn: 万物皆可吉卜力
description_cn: 阅读小说文字或分析图片内容，拆分场景后以吉卜力动画风格生成插画，并编排成漫画页面。
create_source: super-agent-skill-creator
AIGC:
  ContentProducer: 001191110102MAD55U9H0F10002
  ContentPropagator: 001191110102MAD55U9H0F10002
  Label: '1'
  ProduceID: 57aea7a1-6a54-4eda-8397-f34ba0bf8e63
  PropagateID: 57aea7a1-6a54-4eda-8397-f34ba0bf8e63
  ReservedCode1: 6aa22f07-ebf9-4ee4-a920-3a68d418824e
  ReservedCode2: 6aa22f07-ebf9-4ee4-a920-3a68d418824e
---
# 万物皆可吉卜力

## 概述

本技能将小说/故事文字或图片内容转化为 Studio Ghibli（吉卜力工作室）动画风格的**四格漫画**。
工作流程：阅读输入文本或分析图片内容 → 拆分为 4 格分镜 → 编写吉卜力风格提示词 → 调用 ImageGen 生成 4 张方形插画 → 用 HTML 模板编排成 2×2 网格四格漫画页面 → 渲染验证无遮挡。

## 工作流程

按以下 6 个步骤顺序执行。固定生成 4 格漫画，用户可额外指定主题或风格偏好。

### Step 1: 阅读与解析输入内容

根据用户提供的输入类型，选择对应分支：

**输入类型 A — 文本输入**：
1. 读取用户提供的小说文本（直接粘贴的文本、本地文件路径、或 .txt/.md 文件）。
2. 理解故事主线、核心角色、时代背景、情感基调。
3. 提取以下信息：
   - **角色清单**：每个角色的外貌、年龄、服装、性格特征
   - **场景清单**：故事发生的地点与时间段
   - **情节分段**：将文本划分为可独立成画的叙事单元

**输入类型 B — 图片输入**：
1. 读取用户提供的图片文件（截图、图表、流程图、平面图等）。
2. 调用 `image_understanding` 工具分析图片内容：提取图中文字、人物、场景、主题。
3. 将图片内容改编为四格故事。改编策略参考：
   - **CMD 截图 / 报错截图** → 运维小剧场（角色在终端前操作 → 遇到报错 → 情绪爆发 → 解决或释然）
   - **建筑/施工平面图** → 施工排障故事（角色拿图纸 → 现场对照 → 发现冲突 → 收工）
   - **流程图/信息图** → 将流程步骤拟人化为角色冒险或日常故事
4. 提取与类型 A 相同的信息（角色清单、场景清单、情节分段），改编为四格叙事。

**无论哪种输入类型，最终都要产出统一的分镜信息（角色、场景、情节）进入 Step 2。**

### Step 2: 拆分四格分镜

将故事精炼为 **4 个关键场景**，严格遵循四格漫画经典的四段叙事结构：

| 格 | 叙事功能 | 英文 | 镜头景别 | 作用 |
|----|---------|------|---------|------|
| 第1格 | 引入 | Setup | 中景/全景 | 交代背景、角色登场、设定初始情境 |
| 第2格 | 发展 | Development | 中景/近景 | 推进情节、展示角色互动或矛盾初现 |
| 第3格 | 转折 | Twist | 近景/特写 | 高潮或意外转折、情绪爆点、冲突升级 |
| 第4格 | 收束 | Resolution | 全景/远景 | 结果揭晓、情绪收束、点睛结尾（可带反转或幽默） |

每个场景记录：

| 字段 | 说明 | 示例 |
|------|------|------|
| scene_id | 格编号 | S1, S2, S3, S4 |
| role | 叙事功能（内部结构，不在页面上显示） | 引入 / 发展 / 转折 / 收束 |
| summary | 一句话概括 | 少年在山脚下遇到受伤的白狐 |
| shot_type | 镜头景别 | medium shot / close-up / wide shot |
| characters | 出场角色 | 少年阿明、白狐 |
| setting | 环境设定 | 山脚溪边、黄昏 |
| mood | 情绪基调 | 好奇、温柔 |
| narration | 旁白文字（漫画中显示） | 少年从未想过，这个黄昏会改变他的一生。 |
| dialogue | 对话文字（显示在画面下方文字区） | 别怕，我不会伤害你。 |

**注意**：漫画默认不生成对话气泡（speech bubble），旁白与对话文字统一放置在每格图片下方的文字说明区（caption）内展示，避免气泡遮挡画面。

**注意**：页面不显示四段叙事结构的标签文字（引入 / 发展 / 转折 / 收束），这些仅作为内部叙事结构（scene_id 的 role 字段）用于指导分镜设计与版面顺序，不渲染到最终 HTML 页面中。

**四格分镜设计原则**：
- 第1格（引入）：用中景或全景交代角色和背景，让观众快速进入故事
- 第2格（发展）：用中景或近景推进互动，画面比第1格拉近，制造递进感
- 第3格（转折）：用近景或特写呈现高潮/转折，强化视觉冲击和情绪爆发
- 第4格（收束）：用全景或远景收束，可与第1格形成呼应或对比
- 4 格之间应有清晰的情节因果链：引入→发展→转折→收束，缺一不可
- 第3格是四格漫画的灵魂，必须制造足够的转折感——意外、冲突、反转或情绪爆发
- 第4格应有明确的收束感，可带轻幽默或余韵，但不宜再开新悬念
- 如原文较长（超过 1500 字），先提炼核心情节再浓缩为 4 格
- 如原文情节不足以撑满 4 格，可适当扩充细节、补充角色反应来丰富叙事
- 角色在 4 格中的外貌必须保持一致

### Step 3: 编写吉卜力风格提示词

为每个场景编写 ImageGen 生图提示词。

1. 读取 [references/ghibli-style-guide.md](references/ghibli-style-guide.md) 获取详细的风格关键词与提示词模板。
2. 对每个场景，套用以下提示词结构：

```
Studio Ghibli style anime illustration, [SHOT TYPE], [SCENE DESCRIPTION].
[CHARACTER DESCRIPTION].
[ENVIRONMENT DESCRIPTION].
[LIGHTING DESCRIPTION].
[COLOR PALETTE].
[MOOD/ATMOSPHERE],
hand-drawn cel shading, watercolor background, painterly textures,
warm naturalistic palette, clean flowing line art, high detail, masterpiece quality
```

3. 提示词全部使用**英文**编写（ImageGen 对英文提示词效果最佳）。
4. 确保每个提示词包含以下必备关键词：`Studio Ghibli style`, `hand-drawn`, `cel shading`, `watercolor background`。
5. 角色描述需包含：年龄、发型发色、服装、动作、表情、视线方向。
6. 环境描述应加入前景元素（树叶/窗框等）增加画面层次感。

### Step 4: 调用 ImageGen 生成 4 张方形插画

1. 对 4 个场景的提示词，调用 `ImageGen` 工具生成插画。
2. 推荐参数：
   - `size`: `"2048x2048"`（正方形，四格漫画标准比例）
   - `n`: 1（每格生成 1 张；用户可要求生成多张选优）
   - `guidance_scale`: 7-8（平衡提示词遵循度与创作自由度）
3. 生成后记录每张图片的本地文件路径。
4. 如某张图效果不理想，可微调提示词后重新生成。

**并行生成**：将 4 个场景的 ImageGen 调用放在同一个消息中并行执行以提高效率。

**统一尺寸要求**：4 张图片必须使用相同尺寸（2048×2048），确保 2×2 网格排版整齐。

### Step 5: 编排四格漫画页面

1. 读取 [assets/comic-template.html](assets/comic-template.html) 模板文件内容。
2. 使用模板中的 **`layout-four-panel`**（2×2 网格）布局，将 4 张方形插画按顺序排列：
   - 左上 → 第1格（引入）
   - 右上 → 第2格（发展）
   - 左下 → 第3格（转折）
   - 右下 → 第4格（收束）
   （四段叙事结构仅用于确定排列顺序与叙事逻辑，不在页面上显示标签文字）
3. 将占位符替换为实际内容：
   - `{{TITLE}}` → 漫画标题（从故事内容提炼，或用户指定）
   - `{{SUBTITLE}}` → 副标题（如"——吉卜力四格漫画"）
   - `{{IMAGE_N}}` → 第 N 格的插画文件路径（N=1~4，使用相对路径或 base64 编码）
   - `{{NARRATION_N}}` → 第 N 格旁白文字
   - `{{DIALOGUE_N}}` → 第 N 格对话文字（可选，无对话则留空）
4. 将填充后的 HTML 保存为最终交付文件，文件名格式：`{标题}_四格漫画.html`。
5. 在浏览器中可预览效果。

**注意**：模板不再包含 `{{SPEECH_N}}` 气泡占位符——漫画默认无对话气泡，所有文字（旁白/对话）都显示在每格下方的文字说明区，保证画面干净不被遮挡。

### Step 6: 渲染验证

生成漫画页面后，必须验证渲染效果，确保图片完整加载、无遮挡、排版规整。

1. **启动本地 HTTP 服务器**：Playwright 不支持 `file://` 协议，需先在漫画文件所在目录启动 Python HTTP 服务器（如 `python -m http.server 8901 --directory <漫画目录>`），后台运行。
2. **浏览器导航**：用 Playwright 访问 `http://127.0.0.1:<端口>/<HTML文件名>`。
3. **整页截图**：使用 `playwright_browser_take_screenshot` 进行 `fullPage: true` 截图。
4. **视觉检查**：将截图传入 `image_understanding`，检查以下要点：
   - 4 张图片是否完整加载（无空白/裂图）
   - 是否有元素遮挡人物脸部、屏幕、关键文字（漫画默认无对话气泡，正常不会出现遮挡）
   - 2×2 网格排版是否规整，有无重叠错乱
5. **可选：桌面尺寸复核**：调整浏览器窗口为 1440×1200，再次截图检查不同分辨率下的显示效果。
6. **关闭服务器**：验证完成后关闭 Python HTTP 服务器进程。

**常见问题排查**：
- 图片加载失败：检查 HTML 中 `src` 路径与实际图片文件名是否一致，注意中文文件名编码问题。
- 中文目录名在 PowerShell/Python 控制台显示乱码：使用 `glob` 工具确认真实路径，不要依赖控制台输出。

## 输入与输出

### 输入

- 小说/故事文本（纯文本、.txt、.md 文件，或直接粘贴的文字）
- 可选：用户指定的场景数量、角色设定、风格偏好

### 输出

- 一个 HTML 四格漫画页面文件，包含 4 张方形插画（2×2 网格布局）与旁白/对话文字（位于每格下方文字区，无气泡遮挡）
- 4 张吉卜力风格方形插画图片文件

## 资源文件

| 文件 | 用途 |
|------|------|
| `references/ghibli-style-guide.md` | 吉卜力美学风格指南、提示词模板、场景速查表。编写提示词时加载。 |
| `assets/comic-template.html` | 漫画排版 HTML 模板，含四格漫画 2×2 网格布局。编排最终页面时加载。 |

## 注意事项

- 提示词必须使用英文，旁白和对话使用中文原文。
- 漫画默认**不带对话气泡**：不要在图面上叠加 speech bubble，旁白与对话一律放到每格下方的文字说明区，保持画面干净、无遮挡。（如用户明确要求气泡，才额外添加）
- ImageGen 生成的图片会自动保存到工作区，直接使用返回的文件路径即可。
- 如用户提供的文本很长（超过 3000 字），先提取核心情节再分镜，不要逐句转换。
- 漫画 HTML 文件应保存为最终交付物（放在工作目录根目录），图片文件由 ImageGen 自动管理。
- 角色在 4 格中的外貌描述必须保持一致（同一角色的发型、服装在所有格中统一）。
- 4 张图片必须使用相同尺寸（2048×2048），确保 2×2 网格排版整齐美观。
- 四格漫画的叙事灵魂在第3格（转折），必须制造足够的转折感和戏剧张力。
- **目录命名一致性**：创建漫画目录时，目录名应与最终 HTML 文件名前缀保持一致（如目录"深夜的8810端口_四格漫画"对应文件"深夜的8810端口_四格漫画.html"）。若不一致会导致写入失败。注意：中文目录名在 PowerShell/Python 控制台会显示乱码，写入前务必用 `glob` 工具确认真实路径。