---
name: 免费图像视频生成
description: 免配置apiKey生成高质量图像和视频。通过 自研MCP 服务实现文生图、图生图、文生视频、图生视频、长视频分段生成与合并、提示词智能扩写、旁白配音与字幕合成。免费模型服务端自动路由、额度耗尽自动切换供应商。触发词：生成图片、文生图、图生视频、AI画图、AI视频、画一张、生成视频、文生视频、图生视频、做一张图、做个视频、长视频、分段视频、提示词优化、配音、字幕、旁白、加声音
create_source: super-agent-skill-creator
description_cn: 免配置apiKey生成高质量图像和视频。通过MCP 服务实现文生图、图生图、文生视频、图生视频、长视频分段生成与合并、提示词智能扩写、旁白配音与字幕合成。免费模型服务端自动路由、额度耗尽自动切换供应商。触发词：生成图片、文生图、图生视频、AI画图、AI视频、画一张、生成视频、文生视频、图生视频、做一张图、做个视频、长视频、分段视频、提示词优化、配音、字幕、旁白、加声音
---
# 免费图像视频生成

## 概述

本技能通过 自研MCP 服务生成高质量图像和视频，支持：
- 文生图（文本 → 图片）
- 图生图（图片 + 文本 → 新图片）
- 文生视频（文本 → 视频）
- 图生视频（图片 + 文本 → 视频）
- **长视频分段生成与合并**（服务端 `long_video=true` 原生多段拼接，或本地脚本逐段不同提示词拼接）
- **提示词智能扩写**（服务端 `generate_prompt` / `auto_prompt=true`，基于百炼 qwen-plus）
- **旁白配音与字幕合成**（本地 TTS + ffmpeg 后处理，不依赖 MCP）

免费模型由**服务端自动路由**，额度耗尽自动切换供应商，智能体无需指定 provider、无需做故障转移。

## 接入方式（TeleAgent 透明鉴权）

使用 `scripts/mcp_media_client.py` 通过标准库 urllib 直连 MCP 端点，脚本内部自动完成三步鉴权：

```
鉴权流程（脚本自动完成，无需手动干预）：
  步骤1 → POST initialize，请求头带 x-from-teleAgent: true
  步骤2 → 从响应头提取 X-Mcp-Token 和 Mcp-Session-Id
  步骤3 → 后续 tools/call 请求带 Authorization: Bearer <token> + Mcp-Session-Id
```

```
# 文生图
python scripts/mcp_media_client.py text_to_image \
  --intent "赛博朋克城市夜景" --size 1920x1080

# 文生视频
python scripts/mcp_media_client.py text_to_video \
  --intent "日落海滩" --duration 5 --size 1280x720

# 提示词扩写
python scripts/mcp_media_client.py generate_prompt \
  --intent "城市夜景" --modality image --style cyberpunk
```

脚本支持 `--out` 指定下载路径、`--no-download` 只输出 URL 不下载、`--mcp-url` 覆盖端点。依赖仅 Python 标准库，无第三方依赖。

> ⚠️ 不需要手写任何密钥——token 由服务端动态分配，脚本握手时自动获取并在会话内使用，不持久化、不外泄。

## 可用工具（mcp-media-hub MCP，直接调用）

1. **generate_prompt**(intent, modality, style?)
   - 把一句简短中文想法扩写成高质量英文生成提示词（图像或视频）。只返回提示词文本，不生成媒体。
   - 返回：`{"prompt": "...", "negative_prompt": "..."}` 之类文本。

2. **text_to_image**(intent?, prompt?, auto_prompt?, size?, style?, negative_prompt?)
   - 文生图。默认 `auto_prompt=true` 会先自动扩写英文提示词再出图。
   - `intent`：中文意图（推荐主传这个）；或传 `prompt` 直达英文提示词。
   - `size`：如 `"1024x1024"`（默认）、`"1920x1080"`、`"1080x1920"`。
   - 返回：`{"ok": true, "url": "...", "local_path": "..."}`。

3. **image_to_image**(image_url, intent?, prompt?, auto_prompt?, size?, style?)
   - 图生图。必填 `image_url`（可公网访问的源图 URL）。其余同 `text_to_image`。

4. **text_to_video**(intent?, prompt?, auto_prompt?, duration?, size?, long_video?, segments?)
   - 文生视频。异步任务但服务端内部轮询、阻塞返回最终 URL。
   - `duration`：默认 5，单次上限约 18；`long_video=true` + `segments=N` 服务端原生拼接长视频。
   - `size`：如 `"1280x720"`、`"1920x1080"`，默认横版。

5. **image_to_video**(image_url, intent?, prompt?, auto_prompt?, duration?, size?, long_video?, segments?)
   - 图生视频。必填 `image_url`（首帧图 URL）。其余同 `text_to_video`。

6. **query_video**(video_id)
   - 查询视频任务状态/取回下载地址。正常 `text_to_video` 已返回 URL，无需手动调用。

7. **list_models**(capability?)
   - 列出已启用免费模型及能力（按 `capability` 过滤）。

> ⚠️ 没有 `provider` 参数、没有 `list_providers` / `check_provider_status` / `get_auth` 工具。旧文档里这些概念已废弃。免费模型由服务端自动路由，额度耗尽自动切换。

## 意图引导（低摩擦交互）

按「最小必要信息」原则处理——只问缺的东西，其余一律用默认值。

### 必须确认的信息（缺了才补问，且一次问清）
1. **模态**：要图片还是视频？
2. **创意方向 / 主体**：想生成什么内容？

### 有默认值、不主动追问，仅在用户明确提到时才采用
| 参数 | 图片默认值 | 视频默认值 | 说明 |
|---|---|---|---|
| 风格 / 画风 | 并入 intent | 并入 intent | 用户说"水彩风/赛博朋克/写实/3D"等时写进 intent |
| 尺寸 size | `1024x1024` | `1280x720`（横版） | 用户提了"竖图/横图/具体分辨率"才改 |
| 数量 | 单次 1 张 | 单次 1 段 | 用户要"几张/一组"才改 |
| 时长 duration | —— | `5`（秒） | 用户提了"10秒/30秒"才改 |
| 长视频 long_video | —— | 关 | 用户要超过约 18 秒才开，配 `segments` |

### 交互原则
1. 用户一句话已说清 → **不要追问**，直接生成，结果里说明本次用的模态 / 尺寸 / 风格。
2. 用户给出模糊描述 → 补问 1-2 句（图片还是视频？大概什么主题？），别列清单。
3. 生成后主动补一句"想调整尺寸/风格/时长，告诉我就行"。
4. 不要手动指定 provider、不要调 `list_models` 去挑供应商——`auto_prompt=true` + 服务端自动路由即可。
5. **提示词过简时主动增强**（详见下方「提示词增强决策流」）。

## 提示词增强决策流

当用户的创意描述过于简单时，**先通过分步交互收集创意要素，再用 generate_prompt 最终扩写，最后生成媒体**。

### 什么样的提示词算"过简"？

满足以下**任意一条**即视为过简，应触发增强：
- 描述少于 8 个汉字或 3 个英文单词（如"画个猫""城市夜景""a robot"）
- 只有主体，缺少风格、光影、构图、色调中至少一项（如"做一个科技海报"）
- 用户自己也说不太清楚想要什么（如"随便画个好看的"）

### 决策流程

```
用户给出创意描述
    │
    ├─ 描述足够丰富（含主体+风格/光影/构图等）
    │     └─ 直接生成（auto_prompt=true 自动扩写即可）
    │
    └─ 描述过简 ──→ 触发分步交互式提示词扩写
          │
          ├─ 第1步：用 question 工具分步给出单选/多选选项，收集创意要素
          │     ├─ 风格选择（单选）：给出5-6个最匹配的风格选项
          │     ├─ 画面氛围/色调（多选）：给出4-5个氛围选项
          │     ├─ 视角/构图（单选）：给出4-5个构图选项
          │     ├─ 视频追加：运镜方式（单选）+ 时长（单选）——仅视频
          │     └─ 用户每步可选"自定义"自行输入
          │
          ├─ 第2步：将原始描述 + 用户选择拼合成丰富中文 intent
          │     └─ 示例："美女跳舞" + 电影感/暖色/近景/推镜头/5秒
          │           → "美女在暖色聚光灯下跳舞，电影感画面，近景特写，缓慢推镜头，5秒"
          │
          ├─ 第3步：调用 generate_prompt 做最终英文扩写
          │     ├─ 调用 generate_prompt(intent=拼合后的丰富描述, modality=image/video, style=用户选择的风格)
          │     ├─ 拿到返回的 {prompt, negative_prompt}
          │     └─ 如有 negative_prompt，一并用于生成
          │
          ├─ 第4步：用扩写后的 prompt + auto_prompt=false 生成媒体
          │     └─ text_to_image / text_to_video (prompt=扩写结果, auto_prompt=false, negative_prompt=...)
          │
          └─ MCP generate_prompt 不可用时降级
                ├─ 降级A：本机脚本 prompt_builder.py（本地风格预设+中英映射+运镜模板）
                │     ├─ 推断风格 ID → 运行 prompt_builder.py 生成英文提示词
                │     └─ 用脚本直连 mcp_media_client.py 出图（auto_prompt=false）
                └─ 降级B：auto_prompt=true 兜底（拼合后的中文 intent 直接传入，服务端自动扩写）
```

### 分步交互选项模板

当判断提示词过简时，用 TeleAgent 的 **question 工具**向用户展示选项。根据用户原始描述智能匹配选项，每步给出 4-6 个选项（含"自定义"由 question 工具自动追加）。以下是各维度的选项池，智能体根据用户描述**动态选择最匹配的 4-6 项**，不限于此模板：

#### 风格选择（单选）

根据用户描述推断最可能的风格方向，给出 4-6 个选项：

| 风格方向 | 选项文案 | style 参数值 |
|---|---|---|
| 电影感 | 电影感，写实电影画面 | cinematic |
| 写实摄影 | 写实摄影，高清照片风格 | realistic |
| 赛博朋克 | 赛博朋克，霓虹科幻 | cyberpunk |
| 中国水墨 | 中国水墨画，国风写意 | chinese_ink |
| 动漫风格 | 日系动漫，二次元 | anime_style |
| 3D渲染 | 3D渲染，立体卡通 | 3d_render |
| 水彩画 | 水彩手绘，柔和色调 | watercolor |
| 极简主义 | 极简主义，大面积留白 | minimalist |
| 油画质感 | 油画质感，厚重笔触 | oil_painting |
| 复古胶片 | 复古胶片，怀旧色调 | vintage_film |
| 奇幻史诗 | 奇幻史诗，壮观宏大 | fantasy_epic |
| 扁平插画 | 扁平插画，矢量风格 | flat_illustration |

> **匹配规则**：用户提到"科技/未来"→优先赛博朋克、3D渲染；"古风/传统"→优先水墨；"可爱/少女"→优先动漫、水彩；"高级/商务"→优先电影感、极简；无法判断时默认给电影感、写实、赛博朋克、动漫、3D、水彩六项。

#### 画面氛围/色调（多选）

根据用户描述推断最匹配的 4-5 个氛围方向：

| 氛围方向 | 选项文案 |
|---|---|
| 暖色调 | 暖色调，金色暖光 |
| 冷色调 | 冷色调，蓝色清冷 |
| 高对比度 | 高对比度，明暗交错 |
| 柔和梦幻 | 柔和梦幻，薄雾弥漫 |
| 鲜艳活泼 | 鲜艳活泼，色彩饱和 |
| 低饱和莫兰迪 | 低饱和莫兰迪色系 |
| 黑白 | 黑白单色 |
| 霓虹光效 | 霓虹光效，光影斑驳 |

> **匹配规则**：用户提到"夜景/城市"→优先霓虹光效、高对比度；"温柔/治愈"→优先柔和梦幻、暖色调；"高级"→优先低饱和莫兰迪；无法判断时给暖色、冷色、高对比、柔和、鲜艳五项。

#### 视角/构图（单选）

| 构图方向 | 选项文案 |
|---|---|
| 近景特写 | 近景特写，主体占满画面 |
| 中景 | 中景，主体居中，环境可见 |
| 远景全景 | 远景全景，大气广阔 |
| 俯视鸟瞰 | 俯视鸟瞰 |
| 仰视 | 仰视，强调气势 |
| 平视 | 平视，自然视角 |

> **匹配规则**：用户提到"全景/大气"→优先远景；"特写/细节"→优先近景；"宏大/壮观"→优先仰视；无法判断时给近景、中景、远景、俯视、仰视五项。

#### 视频追加：运镜方式（单选，仅视频模态）

| 运镜方向 | 选项文案 |
|---|---|
| 静态镜头 | 静态固定镜头 |
| 缓慢推镜头 | 缓慢推镜头（zoom in） |
| 缓慢拉镜头 | 缓慢拉镜头（zoom out） |
| 水平摇镜头 | 水平摇镜头（pan） |
| 环绕拍摄 | 环绕主体拍摄 |
| 跟随移动 | 跟随主体移动 |

> **匹配规则**：用户提到"展示/介绍"→优先缓慢推镜头；"全景"→优先缓慢拉镜头或水平摇；"人物行动"→优先跟随移动；无法判断时给全部六项。

#### 视频追加：时长（单选，仅视频模态）

| 时长选项 | 选项文案 |
|---|---|
| 5秒 | 5秒（默认） |
| 10秒 | 10秒 |
| 15秒 | 15秒 |
| 30秒 | 30秒（长视频分段拼接） |

### 交互执行规则

1. **一次问一个维度**：每个维度用一次 question 工具调用，用户选完再进入下一步。
2. **问题简洁**：header 控制在 8 字以内，question 用一句话说明。
3. **选项动态生成**：上述模板是选项池，智能体根据用户原始描述智能挑选 4-6 个最匹配的选项，不要每次都给全部选项。
4. **"跳过"选项**：每个维度最后一个选项固定为"跳过此步，用默认值"，用户不想选就直接跳过。
5. **视频模态追加步骤**：如果是视频，在风格/氛围/构图三步后追加运镜和时长两步；图片只需前三步。
6. **拼合 intent**：所有步骤完成后，将用户原始描述 + 所有选择拼成一句丰富的中文 intent，再送 generate_prompt 做最终扩写。
7. **用户说"你来定"**：如果用户在某步选了"跳过"或说"你看着办"，智能体根据上下文自行推断最匹配的值。

### 分步交互完整示例

用户说："画个猫"

**第1步 · 风格选择**（question 工具，单选）
```
header: "风格选择"
question: "画什么风格的猫？"
options:
  - 写实摄影，高清照片风格
  - 日系动漫，二次元
  - 水彩手绘，柔和色调
  - 3D渲染，立体卡通
  - 油画质感，厚重笔触
  - 跳过此步，用默认值
```
用户选：水彩手绘，柔和色调

**第2步 · 画面氛围**（question 工具，多选）
```
header: "画面氛围"
question: "想要什么氛围色调？可多选"
multiple: true
options:
  - 暖色调，金色暖光
  - 柔和梦幻，薄雾弥漫
  - 鲜艳活泼，色彩饱和
  - 低饱和莫兰迪色系
  - 跳过此步，用默认值
```
用户选：暖色调 + 柔和梦幻

**第3步 · 视角构图**（question 工具，单选）
```
header: "视角构图"
question: "用什么视角拍这只猫？"
options:
  - 近景特写，主体占满画面
  - 中景，主体居中，环境可见
  - 远景全景，大气广阔
  - 俯视鸟瞰
  - 跳过此步，用默认值
```
用户选：近景特写

**拼合 intent**："水彩手绘风格的猫，近景特写，暖色调金色暖光，柔和梦幻薄雾弥漫"

**调用 generate_prompt**：
```
mcp_media_client.py generate_prompt \
  --intent "水彩手绘风格的猫，近景特写，暖色调金色暖光，柔和梦幻薄雾弥漫" \
  --modality image --style watercolor
```

**用返回的 prompt 生成图片**：
```
mcp_media_client.py text_to_image \
  --prompt "[generate_prompt返回的英文prompt]" --auto_prompt false --size 1024x1024
```

### 视频模态分步交互示例

用户说："美女跳舞"

**第1步 · 风格选择**（单选）
```
header: "风格选择"
question: "什么风格的美女跳舞视频？"
options:
  - 电影感，写实电影画面
  - 写实摄影，高清照片风格
  - 赛博朋克，霓虹科幻
  - 日系动漫，二次元
  - 3D渲染，立体卡通
  - 跳过此步，用默认值
```

**第2步 · 画面氛围**（多选）
```
header: "画面氛围"
question: "想要什么氛围色调？可多选"
multiple: true
options:
  - 暖色调，金色暖光
  - 霓虹光效，光影斑驳
  - 高对比度，明暗交错
  - 柔和梦幻，薄雾弥漫
  - 跳过此步，用默认值
```

**第3步 · 视角构图**（单选）
```
header: "视角构图"
question: "用什么视角拍？"
options:
  - 近景特写，主体占满画面
  - 中景，主体居中，环境可见
  - 远景全景，大气广阔
  - 仰视，强调气势
  - 跳过此步，用默认值
```

**第4步 · 运镜方式**（单选，仅视频）
```
header: "运镜方式"
question: "镜头怎么动？"
options:
  - 缓慢推镜头（zoom in）
  - 环绕主体拍摄
  - 跟随主体移动
  - 静态固定镜头
  - 跳过此步，用默认值
```

**第5步 · 时长**（单选，仅视频）
```
header: "视频时长"
question: "视频多长？"
options:
  - 5秒（默认）
  - 10秒
  - 15秒
  - 30秒（长视频分段拼接）
```

**拼合 intent**（假设用户选了电影感+霓虹光效+近景+缓慢推镜头+5秒）：
"美女跳舞，电影感写实电影画面，近景特写，霓虹光效光影斑驳，缓慢推镜头，5秒"

**调用 generate_prompt** → **text_to_video(prompt=扩写结果, auto_prompt=false)** 生成视频。

### 风格推断对照（generate_prompt style 参数 / prompt_builder.py 降级时用）

| 用户描述关键词 | style 参数值 | 说明 |
|---|---|---|
| 科技/AI/未来/赛博/数据/网络 | `cyberpunk` 或 `tech_promo` | 科技类首选 |
| 电影/大片/质感 | `cinematic` | 电影感 |
| 真实/照片/写实 | `realistic` | 写实摄影 |
| 水墨/国风/禅意 | `chinese_ink` | 中国水墨 |
| 简约/极简/留白 | `minimalist` | 极简主义 |
| 动漫/二次元 | `anime_style` | 动漫风格 |
| 3D/渲染/立体 | `3d_render` | 3D渲染 |
| 水彩/手绘 | `watercolor` | 水彩画 |
| 自然/风景/山水 | `nature_landscape` | 自然风光 |
| 城市/夜景/霓虹 | `urban_night` | 城市夜景 |
| 复古/怀旧/胶片 | `vintage_film` | 复古胶片 |
| 油画/笔触 | `oil_painting` | 油画质感 |
| 奇幻/史诗/壮观 | `fantasy_epic` | 奇幻史诗 |
| 扁平/矢量/插画 | `flat_illustration` | 扁平插画 |

> 推断不确定时默认用 `cinematic`（通用性最强）。

> ⚠️ 增强产出提示词后，出图时必须设 `auto_prompt=false`，避免服务端二次扩写覆盖已优化内容。

## 风格预设

完整风格列表见 [references/style_presets.md](references/style_presets.md)，常用风格：

**图像风格**：电影感、写实摄影、赛博朋克、中国水墨、扁平插画、3D渲染、油画质感、极简主义、动漫风格、复古胶片、奇幻史诗、水彩画、像素艺术、等距视角。

**视频风格**：科技宣传、产品展示、自然风光、城市夜景、抽象艺术、人物动态。

## 分辨率与版式

**图像版式**：
| 版式 | 比例 | 推荐尺寸 | 适用场景 |
|------|------|---------|---------|
| 正方形 | 1:1 | 1024x1024 | 头像、社交媒体、商品图 |
| 横版 | 16:9 | 1920x1080 | 封面图、横幅、壁纸 |
| 竖版 | 9:16 | 1080x1920 | 手机壁纸、短视频封面、朋友圈海报 |
| 宽幅 | 21:9 | 2560x1080 | 电影感宽屏、网页头图 |

**视频版式**（用 `size` 参数）：
| 版式 | size | 适用场景 |
|------|------|---------|
| 横版标准 | 1280x720 | 标准视频、宣传片段 |
| 竖版标准 | 720x1280 | 短视频平台、手机观看 |
| 横版高清 | 1920x1080 | 全高清横版 |
| 竖版高清 | 1080x1920 | 全高清竖版 |

> 视频像素总数需在 [3,686,400, 16,777,216] 之间，宽高比范围 [1/16, 16]。

## 工作流

### 1. 文生图（文本 → 图片）

调用 `text_to_image`：
- `intent`：用户的文本描述（必填，建议中文，可口语化）
- `auto_prompt`：默认 `true`（服务端用百炼 qwen-plus 扩写）；传 `prompt` 并设 `auto_prompt=false` 时手动控提示词
- `size`：可选；默认 `"1024x1024"`

```
text_to_image(
  intent="日式禅意枯山水庭院，樱花飘落，清晨柔光，写实摄影",
  size="1024x1024"
)
```

### 2. 图生图（图片 + 文本 → 新图片）

调用 `image_to_image`：
- `image_url`：源图片可公网访问 URL（必填）
- `intent`：描述如何修改（必填）

### 3. 文生视频（文本 → 视频）

调用 `text_to_video`：
- `intent`：视频内容描述（必填，建议加入运镜/氛围描述）
- `duration`：可选；默认 5，单次上限约 18
- `size`：可选；默认横版 `"1280x720"`
- `long_video=true` + `segments=N`：服务端原生拼接长视频

### 4. 图生视频（图片 + 文本 → 视频）

调用 `image_to_video`：
- `image_url`：起始图片可公网访问 URL（必填）
- 其余参数同文生视频。

### 5. 长视频分段生成与合并

**方式一（推荐，服务端原生拼接）**：

```
text_to_video(
  intent="专业舞者在聚光灯舞台表演现代舞，电影感，慢镜头",
  duration=30, long_video=true, segments=6, size="1280x720"
)
```

**方式二（本地脚本逐段不同提示词）**：

```bash
python scripts/generate_long_video.py --storyboard storyboard.json --output "D:\Desktop\output.mp4"
```

分镜 JSON 格式：

```json
{
  "size": "1280x720",
  "segments": [
    {"intent": "镜头1：星空开场，粒子汇聚成AI核心球体", "duration": 5},
    {"intent": "镜头2：转场到现代办公室，AI界面操作演示", "duration": 5},
    {"intent": "镜头3：数据安全盾牌激活", "duration": 5},
    {"intent": "镜头4：镜头拉远，多AI节点连网", "duration": 5}
  ]
}
```

> 方式二每段约 5 秒，总时长 = 段数 × 5 秒；建议 3–6 段（15–30 秒）。

### 6. 旁白配音与字幕合成

使用 `scripts/add_voice_subtitle.py`（本地 TTS + ffmpeg，不依赖 MCP）：

```bash
python scripts/add_voice_subtitle.py \
  --video "D:\Desktop\input.mp4" \
  --narration narration.txt \
  --output "D:\Desktop\output_配音.mp4"
```

**字幕模式**（`--subtitle-mode`）：`burn`（默认，硬字幕）/ `both`（硬字幕+SRT）/ `subtitle`（软字幕轨）/ `none`（仅配音）。

详见 [references/api_reference.md](references/api_reference.md) 的配音字幕参数表。

### 7. 提示词智能构建

内置三套提示词增强机制，按"用户描述丰富度"自动选择路径（详见上方「提示词增强决策流」）：

| 机制 | 触发条件 | 实现方式 | 质量 |
|---|---|---|---|
| auto_prompt 自动扩写 | 描述已较丰富 | 服务端 qwen-plus 自动扩写，默认开启 | 高 |
| generate_prompt 主动增强 | 描述过简 | 服务端 qwen-plus 返回 prompt+negative_prompt | 高 |
| prompt_builder.py 本地增强 | 描述过简 + MCP 不可用 | 本地风格预设库+中英映射+运镜模板，离线运行 | 中 |

```bash
# 方式A：服务端 generate_prompt（首选）
python scripts/mcp_media_client.py generate_prompt \
  --intent "科技海报" --modality image --style cyberpunk

# 方式B：本地 prompt_builder.py（MCP 不可用时降级）
python scripts/prompt_builder.py --content "科技海报" --style cyberpunk --type image --lang en

# 方式C：交互式构建
python scripts/prompt_builder.py --interactive
```

## 下载与保存生成结果

```bash
python scripts/download_media.py <url> [--out 输出路径] [--base64] [--timeout 秒数]
```

保存完成后，向用户报告：文件完整路径、文件大小（MB）；视频还需附分辨率和时长。

## 最佳实践

### 提示词建议
- 图像：具体主体 + 风格 + 光影 + 构图
- 视频：在图像提示词基础上加运镜和动态描述
- 中文 `intent` 配合 `auto_prompt=true` 即可；追求极致可控时用 `generate_prompt` / `prompt_builder.py`

### 风格一致性
- 多张图保持同一风格时，在 `intent` 中重复核心风格词
- 长视频各段保持色调和氛围一致

### 输出策略
- 单次生成 1 张图 / 1 段视频；长视频用 `long_video` 或本地脚本分段

## 错误处理

- **MCP 工具不可用**：
  1. 确认 `.mcp.json` 中 `media-hub` 的 `url` 为 `https://mcp.bbdict.com/hub/mcp`，`type` 为 `streamable-http`，**无 headers 字段**。
  2. 如配置正确仍不可用，重启 TeleAgent 使配置生效。
  3. **降级路径**：用 `scripts/mcp_media_client.py` 脚本直连 MCP 端点（脚本内部自动完成三步鉴权），无需等待重启。
- **list_models 参数错误**：`capability` 只接受 `text2image`/`text2video`/`image2image`/`image2video`/`prompt`，不接受旧的 `"image"`/`"video"`。
- **生成失败/返回空**：服务自动路由+故障转移，一般无需手动换 provider；仍失败如实告知原因。
- **视频长时间未返回**：免费队列较慢；若拿到 `video_id` 但没 URL，用 `query_video(video_id)` 续查。
- **网络超时**：再试一次；服务端临时不可用则告知用户稍后再试。
- **长视频部分段失败（方式二脚本）**：脚本跳过失败段、用已成功段合并。
- **ffmpeg 合并失败**：确认 `imageio-ffmpeg` 已装（`pip install imageio-ffmpeg`）。
- **edge-tts 不可用**：`add_voice_subtitle.py` 自动回退 Windows SAPI。
- **字幕烧录失败**：确认 ffmpeg 启用 libass，或改用 `--subtitle-mode subtitle` 软字幕规避。

## 参考资源

- 详细 API 参数表和调用示例：见 [references/api_reference.md](references/api_reference.md)
- 风格预设完整列表：见 [references/style_presets.md](references/style_presets.md)
- **通用 MCP 客户端（脚本直连，自动三步鉴权）**：`scripts/mcp_media_client.py`
- 下载保存脚本：`scripts/download_media.py`
- 提示词智能构建（本地）：`scripts/prompt_builder.py`
- 长视频分段生成（本地）：`scripts/generate_long_video.py`
- 旁白配音与字幕合成（本地）：`scripts/add_voice_subtitle.py`
