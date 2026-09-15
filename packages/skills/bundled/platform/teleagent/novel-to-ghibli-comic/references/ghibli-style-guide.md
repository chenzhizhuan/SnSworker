---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '431ed2bc-a3f1-41ca-98be-d15fcdd95488'
  PropagateID: '431ed2bc-a3f1-41ca-98be-d15fcdd95488'
  ReservedCode1: '66a4d518-1bbe-42b9-a232-aad58ad3ca39'
  ReservedCode2: '66a4d518-1bbe-42b9-a232-aad58ad3ca39'
---

# 吉卜力风格提示词工程指南

本文件提供 Studio Ghibli 动画美学特征解析及 ImageGen 工具的提示词模板。
在使用本技能时按需加载本文件，指导逐场景编写高质量生图提示词。

---

## 目录

1. [吉卜力美学核心特征](#1-吉卜力美学核心特征)
2. [镜头语言与构图](#2-镜头语言与构图)
3. [光影与色调](#3-光影与色调)
4. [角色与表情](#4-角色与表情)
5. [自然环境与氛围](#5-自然环境与氛围)
6. [ImageGen 提示词模板](#6-imagegen-提示词模板)
7. [四格漫画分镜指南](#7-四格漫画分镜指南)
8. [场景类型速查表](#8-场景类型速查表)
9. [常见错误与修正](#9-常见错误与修正)

---

## 1. 吉卜力美学核心特征

| 维度 | 关键描述词 |
|------|-----------|
| 整体风格 | Studio Ghibli style, hand-drawn animation, cel shading, watercolor background, 2D anime illustration |
| 线条 | clean flowing line art, soft outlines, hand-painted feel |
| 色彩 | warm earthy palette, muted naturalistic colors, soft pastel highlights |
| 质感 | painterly textures, visible brush strokes in background, smooth flat colors on characters |
| 情绪基调 | whimsical, nostalgic, serene, sense of wonder, gentle warmth |

**核心原则**：吉卜力的画面总给人一种"被温柔包裹"的感觉。背景如水彩般通透、角色线条干净柔和、光线永远带着温度。

---

## 2. 镜头语言与构图

### 常用景别

| 景别 | 英文提示词 | 适用场景 |
|------|-----------|---------|
| 大远景 | extreme wide shot, establishing shot | 展现故事发生的世界全貌、山川村落 |
| 远景 | wide shot | 角色在环境中的位置关系 |
| 全景 | full body shot | 角色全身动作、行走奔跑 |
| 中景 | medium shot, waist-up | 对话场景、日常互动 |
| 近景 | close-up shot | 面部表情、情绪特写 |
| 过肩镜头 | over-the-shoulder shot | 两人对话时的视角 |
| 俯瞰 | bird's eye view | 从高处俯视大地、屋顶 |
| 仰视 | low angle shot | 表现角色庄严或场景宏大 |

### 构图技巧

- **三分法则**：将主体放在画面三分线交叉点
- **前景遮挡**：用树叶、窗框等前景元素增加层次感（Ghibli 标志性手法）
- **透视纵深**：用道路、河流引导视线深入画面
- **负空间**：大面积天空或草地留白营造空灵感

**提示词示例**：
```
wide shot, composition following rule of thirds, foreground branches framing the scene, dirt path leading into distant mountains
```

---

## 3. 光影与色调

### 光照类型

| 光照 | 英文提示词 | 情绪效果 |
|------|-----------|---------|
| 黄金时刻 | golden hour lighting, warm sunset glow | 温馨、怀旧 |
| 斑驳阳光 | dappled sunlight through leaves, light rays | 童话、神秘 |
| 清晨柔光 | soft morning light, gentle haze | 新生、纯净 |
| 黄昏暖光 | amber twilight, fading sunset | 离别、思念 |
| 雨天漫射 | overcast diffused light, rain-soaked atmosphere | 忧郁、沉静 |
| 夜间月光 | moonlit night, soft blue tones, firefly glow | 神秘、静谧 |
| 正午强光 | bright midday sun, vivid saturated colors | 活力、冒险 |

### 色调搭配建议

- **田园温暖**：emerald green, golden yellow, terracotta orange, sky blue
- **都市柔和**：misty grey-blue, warm amber, soft white
- **奇幻绚丽**：deep teal, luminescent green, violet twilight, glowing particles
- **怀旧淡雅**：faded sepia tones, dusty rose, sage green, cream

**提示词示例**：
```
golden hour lighting, warm amber glow, dappled sunlight filtering through canopy, soft volumetric light rays, lush green meadow with wildflowers
```

---

## 4. 角色与表情

### 角色描写要素

提示词中应包含以下角色信息（按重要性排序）：

1. **外貌**：age, hair color/style, eye color, build, distinctive features
2. **服装**：clothing style, color, fabric texture, accessories
3. **动作**：specific pose, gesture, body language
4. **表情**：emotional expression, gaze direction

### 表情提示词库

| 情绪 | 英文提示词 |
|------|-----------|
| 欢快 | joyful smile, bright eyes, laughing |
| 温柔 | gentle soft smile, warm gaze |
| 坚定 | determined eyes, set jaw, confident expression |
| 惊讶 | wide-eyed wonder, mouth slightly open |
| 忧伤 | melancholic expression, downcast eyes, wistful |
| 思念 | longing gaze into distance, bittersweet smile |
| 恐惧 | tense expression, widened eyes, guarded posture |
| 平静 | serene expression, content, at peace |

### 角色提示词模板

```
a [age]-year-old [gender] with [hair description], wearing [clothing], [action/pose], [expression], [gaze direction]
```

**示例**：
```
a 14-year-old girl with short dark brown bob hair and large expressive brown eyes, wearing a simple navy blue dress with white collar, standing on a grassy hill with wind blowing her hair, gentle hopeful smile, gazing toward distant mountains
```

---

## 5. 自然环境与氛围

### 吉卜力标志性环境元素

- **植被**：lush rolling hills, ancient gnarled trees, wildflower meadows, moss-covered stones
- **水景**：crystal clear streams, tranquil lakes, cascading waterfalls, rain puddles
- **天空**：cumulus clouds, dramatic sunset sky, star-filled night
- **建筑**：rustic countryside houses, wooden porches, tiled roofs, narrow alleyways
- **细节**：swaying grass, floating pollen/dust particles, steam rising from food, laundry on a line

### 氛围营造词

```
peaceful countryside, gentle breeze swaying the grass, floating dust particles in sunbeams, distant mountains under fluffy clouds, birds circling in the warm sky
```

---

## 6. ImageGen 提示词模板

### 标准模板

以下是调用 ImageGen 工具时的终极提示词模板结构：

```
Studio Ghibli style anime illustration, [SHOT TYPE], [SCENE DESCRIPTION]. [CHARACTER DESCRIPTION]. [ENVIRONMENT DESCRIPTION]. [LIGHTING DESCRIPTION]. [COLOR PALETTE]. [MOOD/ATMOSPHERE], hand-drawn cel shading, watercolor background, painterly textures, warm naturalistic palette, clean flowing line art, high detail, masterpiece quality
```

### 变量说明

| 变量 | 说明 | 示例 |
|------|------|------|
| SHOT TYPE | 镜头景别 | wide shot / close-up |
| SCENE DESCRIPTION | 场景核心动作/事件 | a girl standing on a hill watching the sunset |
| CHARACTER DESCRIPTION | 角色外貌服装动作表情 | a 14-year-old girl with short brown hair wearing a navy dress, gentle smile |
| ENVIRONMENT DESCRIPTION | 环境细节 | lush green meadow with wildflowers, distant mountains, fluffy clouds |
| LIGHTING DESCRIPTION | 光照效果 | golden hour, warm amber glow, dappled sunlight |
| COLOR PALETTE | 色调关键词 | emerald green, golden yellow, sky blue |
| MOOD/ATMOSPHERE | 情绪氛围 | peaceful, nostalgic, sense of wonder |

### 完整示例

**田园黄昏场景**：
```
Studio Ghibli style anime illustration, wide establishing shot, a young girl standing on a grassy hilltop watching the sunset. A 14-year-old girl with short dark brown bob hair and large brown eyes, wearing a simple navy blue dress with white collar, wind gently blowing her hair, serene content expression. Rolling green hills with wildflowers, distant mountains silhouetted against the sky, a small village with smoke rising in the valley below, fluffy cumulus clouds. Golden hour lighting, warm amber and orange sunset glow, soft light rays. Emerald green, golden yellow, warm orange, soft blue sky. Peaceful, nostalgic, sense of wonder, hand-drawn cel shading, watercolor background, painterly textures, warm naturalistic palette, clean flowing line art, high detail, masterpiece quality
```

**室内日常场景**：
```
Studio Ghibli style anime illustration, medium shot, a boy sitting at a wooden desk reading a book by the window. A 12-year-old boy with messy black hair and round glasses, wearing a white shirt with suspenders, resting chin on hands, absorbed peaceful expression. Cozy wooden room with bookshelves, potted plants on windowsill, curtain gently swaying in the breeze, steam rising from a cup of tea. Soft morning light streaming through the window, dappled light patterns on the desk, gentle haze. Warm wood tones, soft white, sage green, cream. Serene, cozy, gentle warmth, hand-drawn cel shading, watercolor background, painterly textures, warm naturalistic palette, clean flowing line art, high detail, masterpiece quality
```

**冒险出发场景**：
```
Studio Ghibli style anime illustration, low angle shot, a young warrior standing at the edge of a cliff facing a vast fantastical landscape. A 16-year-old youth with wind-tossed silver hair, wearing a travel-worn brown cloak and leather boots, gripping a walking staff, determined eyes, confident expression. Dramatic cliff edge overlooking a valley with winding rivers, ancient ruins, floating islands in the distance, circling birds. Bright midday sun with dramatic cloud shadows, vivid saturated light, lens flare. Deep teal, luminescent green, violet twilight accents, bright blue sky. Adventurous, epic, inspiring, hand-drawn cel shading, watercolor background, painterly textures, warm naturalistic palette, clean flowing line art, high detail, masterpiece quality
```

---

## 7. 四格漫画分镜指南

四格漫画（4-Koma）以四段叙事结构（引入→发展→转折→收束）为叙事骨架，在有限的 4 格内完成完整的微故事。以下为各格的分镜指导。

### Setup（引入）- 第1格

| 维度 | 指导 |
|------|------|
| 叙事功能 | 交代背景、角色登场、设定初始情境 |
| 推荐景别 | medium shot / full body shot |
| 构图要点 | 角色与环境同框，让观众一眼看出"谁、在哪、在做什么" |
| 光影 | 自然光/柔和光，建立基调 |
| 情绪 | 平稳、日常、好奇 |
| 提示词要点 | 确保 character description 清晰完整，environment 中景交代地点 |

**提示词示例**：
```
Studio Ghibli style anime illustration, medium shot, a young boy walking along a forest path carrying a basket. A 12-year-old boy with messy black hair, wearing a simple blue haori and wooden sandals, curious expression, gazing ahead. Sun-dappled forest path with tall trees, wildflowers along the trail, soft mist. Soft morning light, gentle haze. Emerald green, soft brown, warm yellow accents. Peaceful, curious, everyday charm, hand-drawn cel shading, watercolor background, painterly textures, clean flowing line art, high detail, masterpiece quality
```

### Development（发展）- 第2格

| 维度 | 指导 |
|------|------|
| 叙事功能 | 推进情节、角色互动深化、矛盾初现或变化发生 |
| 推荐景别 | medium shot / close-up shot |
| 构图要点 | 比第1格拉近，视线聚焦于角色反应/互动 |
| 光影 | 与第1格保持同一场景但略有变化（如云遮阳光） |
| 情绪 | 渐进变化：好奇→惊讶 / 平静→紧张 |
| 提示词要点 | 强调表情变化和肢体语言，镜头拉近制造递进感 |

**提示词示例**：
```
Studio Ghibli style anime illustration, medium close-up shot, the boy crouching down to look at a small injured fox beside the path. The 12-year-old boy with messy black hair, wearing a blue haori, crouching with wide-eyed wonder, gentle concerned expression, reaching hand toward the fox. Small white fox with a bandaged leg, lying on moss, forest floor with fallen leaves and tiny mushrooms. Dappled sunlight through canopy, warm glow. Emerald green, soft white, warm brown. Curious, tender, gentle concern, hand-drawn cel shading, watercolor background, painterly textures, clean flowing line art, high detail, masterpiece quality
```

### Twist（转折）- 第3格

| 维度 | 指导 |
|------|------|
| 叙事功能 | 高潮转折、意外爆发、冲突升级或情绪高点 |
| 推荐景别 | close-up shot / dramatic angle |
| 构图要点 | 强烈视觉冲击——特写表情、动态仰俯角、戏剧性光线 |
| 光影 | 戏剧性光线：强光/逆光/闪电/月色突变 |
| 情绪 | 高潮：震惊 / 感动 / 紧张 / 欢笑反转 |
| 提示词要点 | 视觉冲击关键词（dramatic / intense / burst of light），表情极致化 |

**提示词示例**：
```
Studio Ghibli style anime illustration, extreme close-up dramatic low angle shot, the fox suddenly transforms into a luminous spirit fox, blinding white light bursting outward. The boy's face frozen in wide-eyed shock and awe, mouth open, backlight silhouette of a majestic fox spirit with glowing fur and ethereal flames. Dramatic burst of radiant light, swirling particles, lens flare, intense white and blue glow. Brilliant white, ethereal blue, golden sparkles. Shock, awe, magical revelation, hand-drawn cel shading, watercolor background, painterly textures, clean flowing line art, high detail, masterpiece quality
```

### Resolution（收束）- 第4格

| 维度 | 指导 |
|------|------|
| 叙事功能 | 结果揭晓、情绪收束、与第1格呼应或形成对比 |
| 推荐景别 | wide shot / full body shot |
| 构图要点 | 拉回全景，与第1格形成视觉呼应（同场景但情绪已变） |
| 光影 | 回归柔和但带变化——月光替代阳光、星夜、黄昏 |
| 情绪 | 收束：温馨 / 幽默 / 余韵 / 安宁 |
| 提示词要点 | 用宽镜头收束故事，色调与第1格呼应但带变化 |

**提示词示例**：
```
Studio Ghibli style anime illustration, wide shot, the boy sitting peacefully on the forest path beside the small fox spirit, both looking up at a starry sky. The 12-year-old boy with messy black hair, wearing a blue haori, sitting cross-legged with the glowing white fox curled in his lap, serene content smile, both gazing upward. Forest clearing open to a vast star-filled night sky, fireflies floating around, distant mountains under moonlight. Soft moonlit night, gentle blue tones, firefly glow, twinkling stars. Deep blue, soft white, warm yellow firefly accents. Peaceful, heartwarming, quiet wonder, hand-drawn cel shading, watercolor background, painterly textures, clean flowing line art, high detail, masterpiece quality
```

### 四格一致性要求

- **角色一致性**：同一角色在 4 格中的年龄、发型、发色、服装必须完全一致
- **色调连贯**：4 格的色调应属于同一色系家族，第3格可允许最大的色调反差（高潮冲击）
- **场景呼应**：第4格与第1格最好在同一场景，形成"出发→归来"或"平静→超越"的呼应
- **尺寸统一**：4 张图片均使用 2048×2048 正方形尺寸

---

## 8. 场景类型速查表

| 小说场景类型 | 推荐镜头 | 推荐光照 | 推荐色调 |
|-------------|---------|---------|---------|
| 开篇介绍 | 大远景/俯瞰 | 清晨柔光/黄金时刻 | 田园温暖 |
| 日常生活 | 中景 | 柔和日光 | 都市柔和/怀旧淡雅 |
| 角色登场 | 全景/中景 | 自然光 | 按角色性格定 |
| 对话互动 | 近景/过肩 | 柔和室内光/室外漫射 | 暖色调 |
| 情感高潮 | 近景特写 | 黄昏暖光/月光 | 怀旧淡雅 |
| 旅途冒险 | 远景/仰视 | 正午强光/黄金时刻 | 奇幻绚丽 |
| 战斗冲突 | 仰视/动态构图 | 强烈对比光 | 深冷色调+暖色点缀 |
| 悲伤离别 | 远景/近景交替 | 雨天漫射/黄昏 | 冷蓝灰调 |
| 温馨重聚 | 中景 | 暖黄室内光 | 温暖橙黄 |
| 结局收束 | 大远景 | 黄金时刻/月光 | 怀旧金色 |

---

## 9. 常见错误与修正

| 问题 | 原因 | 修正方法 |
|------|------|---------|
| 画面过于写实 | 缺少风格关键词 | 确保 "Studio Ghibli style, hand-drawn, cel shading, watercolor background" 出现在提示词中 |
| 角色比例失调 | 场景描述过于复杂 | 简化场景为 1-2 个核心元素，角色描述放在主体位置 |
| 色调偏离吉卜力感 | 色彩关键词冲突 | 使用本指南的色调搭配建议，避免同时出现冲突色 |
| 画面缺乏氛围感 | 缺少环境与光影细节 | 添加前景元素（树叶/窗框）、氛围词（mist/dust particles/steam） |
| 构图平淡 | 镜头语言不足 | 明确指定 shot type，添加构图技巧词（rule of thirds, foreground framing） |
| 多角色场景混乱 | 提示词中角色描述交织 | 每个角色用独立短句描述，位置关系明确化 |

> AI生成