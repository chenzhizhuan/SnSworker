---
name: animation-video-gen
description: 'Generate real animated videos from text, images, prompts, or video scripts. Powered by 即梦 Seedream/Seedance with 7 modes: text2img, text2video, img2video (first+last frame), ref2video (≤9 ref images), vivid2video (motion replication), multimodal, video_extend. v2.4: storyboard refinement (action/shot_type/camera/ambient/emotion/duration_seconds), slash-archetype voice mapping fix, royalty-free BGM library index (BGM_LIBRARY_DIR two-tier match returning real file paths) + 10 synth SFX, real xfade transitions (no black frames), animate_video fix (--preview default off), platform specs (platform_specs.md) + free asset list (free_resources.md), 6-tier TTS fallback (火山→edge→gTTS→pyttsx3→SAPI5→静音). Supports both vertical (9:16) and horizontal (16:9/4:3) 1080P MP4 output via --ratio parameter across all scripts. Trigger: 动画视频, 短剧动画, 竖屏动画, 横屏动画, 抖音短剧, 快手短剧, 生成动画, 文字转动画, 图片转动画, 提示词生成短剧, 脚本转短剧, animation video, short drama.'
name_cn: 动画视频生成V4
description_cn: |-
  动画视频生成 V4，即梦 Seedream/Seedance 驱动的短剧动画生成器。
  7 种生成模式：文生图、文生视频、首尾帧图生视频、参考图（≤9）、参考视频复刻、多模态融合、视频续写。
  5 种画风：适配抖音/快手/B站/YouTube。
  支持竖屏（9:16）与横屏（16:9/4:3）双模式 1080P MP4 输出，通过 --ratio 参数自由切换。
  本次更新：修正一些BUG，稳定输出
create_source: super-agent-skill-creator
AIGC:
  ContentProducer: 001191110102MAD55U9H0F10002
  ContentPropagator: 001191110102MAD55U9H0F10002
  Label: '1'
  ProduceID: ed301bd9-7865-4a55-9201-48b4f2f0739b
  PropagateID: ed301bd9-7865-4a55-9201-48b4f2f0739b
  ReservedCode1: 5b1a3d50-0e2f-4f90-90f9-979003b6a8f3
  ReservedCode2: 5b1a3d50-0e2f-4f90-90f9-979003b6a8f3
---
# 动画视频生成

从提示词、视频脚本或小说文本，一键生成**真正的短剧动画视频**——角色能动、能转、能互动，不是图片配音拼贴。

支持**竖屏（9:16）和横屏（16:9/4:3）双模式输出**，通过 `--ratio` 参数自由切换，全链路打通（剧本生成→AI视频→渲染合成）。

## 前提条件

### 必需
- FFmpeg (或 imageio-ffmpeg)
- Python 3.10+
- Pillow

### AI视频模式（推荐）
- 即梦 API Key（火山方舟）：环境变量 `ARK_API_KEY`
- 获取地址：https://console.volcengine.com/ark
- httpx（推荐）或 requests
- 在 `scripts/video_api_config.json` 中已预配即梦端点和模型 ID，只需设置环境变量即可

### 回退模式（无API Key时自动启用）
- 无需 API Key，但生成的是静态图+Ken Burns缩放效果（非真正动画）

设置 API Key：
```bash
set ARK_API_KEY=your-api-key-here
```

---

## 即梦 Seedream/Seedance 模型矩阵

### 视频生成模型 (Seedance)

| 模型 | model_id | 最长时长 | 分辨率 | 核心特性 |
|------|----------|---------|--------|---------|
| Seedance 2.0 | doubao-seedance-2.0 | 15秒 | 720p | 多模态参考+音频同步+视频续写+联网搜索 |
| Seedance 2.0 Fast | doubao-seedance-2.0-fast | 15秒 | 720p | 快速生成，支持多模态参考 |
| Seedance 2.0 Mini | doubao-seedance-2.0-mini | 10秒 | 720p | 高性价比，基础文生视频/图生视频 |
| Seedance 1.5 Pro | doubao-seedance-1.5-pro | 12秒 | 1080p | Draft样片模式，1080p |

### 图片生成模型 (Seedream)

| 模型 | model_id | 最大分辨率 | 核心特性 |
|------|----------|-----------|---------|
| Seedream 5.0 Pro | doubao-seedream-5.0-pro | 4K | 联网检索+精准编辑+组图 |
| Seedream 5.0 | doubao-seedream-5.0 | 4K | 联网检索+组图 |
| Seedream 5.0 Lite | doubao-seedream-5.0-lite | 2K | 高性价比图片生成 |

---

## 7 种生成模式

### 1. text2img — 文生图（Seedream）
文字描述 → 高质量图片，支持 4K 分辨率和联网检索。

```bash
python scripts/ai_video_generator.py text2img --prompt "夜晚城市天台, 赛博朋克风格" --model seedream-5.0-lite --size 2048x2048
```

### 2. text2video — 文生视频（Seedance）
纯文字描述 → 视频片段，角色能动能说话。

```bash
python scripts/ai_video_generator.py text2video --prompt "年轻女子在城堡广场上缓缓转身, anime style" --model seedance-2.0 --duration 5 --ratio 9:16
```

### 3. img2video — 图生视频（首帧±尾帧）
首帧图片（+可选尾帧）→ 视频。首帧定开头，尾帧定结尾，AI生成中间过渡。

```bash
# 仅首帧
python scripts/ai_video_generator.py img2video --prompt "女子转身, 头发飘动" --image first.png --model seedance-2.0

# 首尾帧模式
python scripts/ai_video_generator.py img2video --prompt "从站立到坐下" --image first.png --last-frame last.png
```

### 4. ref2video — 参考图生视频（≤9张参考图）
参考图提供风格/角色/构图参考 → 生成视频。在 prompt 中用 `[图1]...[图2]...` 指定各图作用。

```bash
python scripts/ai_video_generator.py ref2video --prompt "[图1]角色造型 [图2]场景背景, 角色在场景中行走" --ref char.png,bg.png --model seedance-2.0
```

### 5. vivid2video — 参考视频复刻（≤3段参考视频）
提取参考视频的运动轨迹/运镜/节奏，应用到新内容上。

```bash
python scripts/ai_video_generator.py vivid2video --prompt "赛博朋克城市街道, 相同运镜" --ref-video ref_motion.mp4 --model seedance-2.0
```

### 6. multimodal — 多模态参考融合
图片(≤9张)+视频(≤3段,总≤15s)+音频(≤3段,总≤15s)+文本，全能参考融合。

```bash
python scripts/ai_video_generator.py multimodal --prompt "[图1]角色 [图2]场景 [视频1]运动参考" --ref char.png,bg.png --ref-video motion.mp4 --ref-audio bgm.mp3 --model seedance-2.0
```

### 7. video_extend — 视频续写
使用 `return_last_frame` 获取尾帧，作为下一段视频的首帧，实现多段连续生成。

```bash
# 第一段（返回尾帧）
python scripts/ai_video_generator.py img2video --prompt "角色开始行走" --image first.png --return-last-frame --output seg1.mp4

# 第二段（用上一段尾帧作为首帧）
python scripts/ai_video_generator.py img2video --prompt "角色继续行走" --image seg1_lastframe.png --output seg2.mp4
```

### 即梦特色参数

| 参数 | 说明 | 适用模型 |
|------|------|---------|
| `--generate-audio` / `--no-audio` | 生成/不生成同步音频 | Seedance 2.0/2.0-fast |
| `--return-last-frame` | 返回尾帧图像，用于连续生成 | Seedance 2.0 |
| `--web-search` | 联网搜索增强 | Seedance 2.0/2.0-fast, Seedream 5.0 Pro |
| `--resolution` | 分辨率: 480p/720p/1080p | 全部 |
| `--ratio` | 宽高比: 16:9/4:3/1:1/3:4/9:16/21:9/adaptive | 全部 |
| `--draft` | Draft样片模式 | Seedance 1.5 Pro |

---

## 三种输入模式

### 模式A：提示词生成
给一句话，自动出片：
```
# 竖屏（默认）
python scripts/script_generator.py --prompt "霸道总裁爱上的灰姑娘其实隐藏身份" --genre 都市爱情 --duration 2 --output drama.json

# 横屏 16:9
python scripts/script_generator.py --prompt "霸道总裁爱上的灰姑娘其实隐藏身份" --genre 都市爱情 --duration 2 --ratio 16:9 --output drama.json
```

### 模式B：脚本/小说解析
提供现成的文字素材，自动转换：对话格式脚本、Markdown格式、小说章节、SRT字幕、分镜脚本。

### 模式C：直接制片
已有标准剧本JSON，直接走制作流程。

---

## 完整制作流程

```
用户输入（提示词/脚本/小说）
    ↓
① 剧本生成（提示词→骨架 / 脚本→解析）
    ↓
② LLM填充对白、画面描述、旁白
    ↓
③ AI视频生成API → 角色动画视频片段（角色能动！）
    ├─ text2video: 文字直接生成
    ├─ img2video: 首帧图片生成（跨镜头角色一致性）
    ├─ ref2video: 参考图风格生成
    ├─ vivid2video: 参考视频运动复刻
    └─ multimodal: 多素材融合生成
    ↓  (未配置API时: 回退到 ImageGen + Ken Burns 缩放)
④ TTS配音（六层级回退链: 火山引擎 → edge-tts → gTTS → pyttsx3 → SAPI5 → 静音占位）
     ↓  (三大服务商独立，微软全线故障时Google/火山仍可用)
⑤ 片头+片尾动画
    ↓
⑥ BGM混音 + FFmpeg合成最终 1080P MP4（竖屏9:16 或 横屏16:9/4:3）
```

### 步骤①：剧本生成

**提示词模式：**
```bash
python scripts/script_generator.py --prompt "霸道总裁爱上的灰姑娘其实隐藏身份" --genre 都市爱情 --duration 2 --output drama.json
```

`--genre` 可选：都市爱情 / 古装宫斗 / 悬疑推理 / 校园青春 / 逆袭爽文 / 玄幻修仙

**脚本解析模式：**
```bash
# 竖屏（默认）
python scripts/script_parser.py --input my_script.txt --format auto --output drama.json

# 横屏 16:9
python scripts/script_parser.py --input my_script.txt --format auto --ratio 16:9 --output drama.json
```

**半自动分镜模式：**
```bash
# 生成分镜计划（默认横屏 16:9，可用 --ratio 9:16 切竖屏）
python scripts/script_director.py plan --topic "新品发布宣传片" --template promotion --style tech --ratio 16:9 -o project.json

# 导出生成指令
python scripts/script_director.py export --project project.json -o output_dir
```

5种分镜模板：narrative（叙事型）/ promotion（推宣型）/ explainer（讲解型）/ showcase（展示型）/ emotional（情感型）

剧本JSON格式详见 `references/short_drama_guide.md`，TTS音色参考 `references/tts_voices.md`。

### 步骤②：LLM填充剧本
自动生成的剧本骨架中，`background_prompt`、`dialogues`、`narration` 字段由LLM自动补充。

### 步骤③：AI视频片段生成

```bash
# 生成所有场景的AI视频
python scripts/short_drama_renderer.py --script drama.json --action videos

# 单独生成一个视频片段
python scripts/ai_video_generator.py text2video --prompt "年轻女子在城堡广场上缓缓转身, anime style, 9:16 vertical" --model seedance-2.0
```

**提示词构建规则：**
- 背景描述 + 角色描述 + 动作运镜 + 画风后缀，自动拼接
- 画风: anime / qcomic / realistic / cute / korean_manga
- 运镜: close_up / pan / zoom_in / zoom_out / static / dramatic

API配置说明见 `references/ai_video_api.md`。

### 步骤④：TTS配音（v3 六层级回退链）

| 优先级 | 后端 | 服务商 | 特点 | 失败场景 |
|--------|------|--------|------|---------|
| L0 | 火山引擎 TTS | 字节跳动 | 最佳音质，多音色，复用ARK_API_KEY | 未配置API Key |
| L1 | edge-tts | 微软 | 高音质，支持13种情感调节 | 微软API 403、限速429 |
| L2 | gTTS | Google | 免费云TTS，无需API Key | 无情感参数，单一音色 |
| L3 | pyttsx3 | 微软(本地) | 本地离线，无需网络 | 较慢，音色有限 |
| L4 | SAPI5 (Win) | 微软(本地) | Windows Speech API，稳定 | 仅Windows |
| L5 | 静音占位 | - | FFmpeg生成静音MP3 | 无语音，仅保证流程不中断 |

### 步骤⑤⑥：片头片尾 + 合成

```bash
# 一键完整渲染（画面比例自动读剧本JSON，也可用 --ratio 覆盖）
python scripts/short_drama_renderer.py --script drama.json --action all --output 短剧第一集.mp4

# 指定横屏 16:9 输出（覆盖剧本中的比例设置）
python scripts/short_drama_renderer.py --script drama.json --action all --ratio 16:9 --output 短剧第一集.mp4

# 添加BGM
python scripts/short_drama_renderer.py --script drama.json --action all --bgm bgm.mp3 --output 短剧第一集.mp4
```

可用转场：fade_black, flash_white, crossfade, slide_left/right, zoom_in, dissolve, dissolve_flash (溶解+闪白，戏剧高潮), cut

### 步骤⑥补充：BGM 曲库与音效（v2.4）

**本地免版权曲库（推荐）：**
```bash
# 设置曲库目录（子目录按情绪分类，或文件名带关键词）
set BGM_LIBRARY_DIR=D:\bgm_library
# 扫描曲库
python scripts/bgm_manager.py scan
# 按情绪匹配（返回真实文件路径）
python -c "import sys; sys.path.insert(0,'scripts'); from bgm_manager import match_bgm_for_scene; print(match_bgm_for_scene('happy'))"
```
曲库结构建议：
```
D:\bgm_library\tense\dark_theme.mp3
D:\bgm_library\happy\upbeat_day.wav
D:\bgm_library\epic_cinematic.mp3   (根目录按文件名关键词匹配)
```

**音效合成（无需外部素材）：**
```bash
# 可用: heartbeat/footsteps/clock_tick/phone_ring/rain/wind/crowd/thunder_hit/glass_break/door_close
python scripts/bgm_manager.py synth --name heartbeat --output hb.mp3 --duration 5
```

### 发布规格与素材参考

- 平台视频规格（抖音/快手/B站/小红书 + 通用导出设置）：`references/platform_specs.md`
- 免版权素材清单（BGM/音效/图片/视频来源+情绪搜索词）：`references/free_resources.md`

---

## 回退模式（无API Key）

当 API 未配置时，自动降级为：
1. ImageGen 生成场景关键帧图片
2. FFmpeg Ken Burns 缓慢缩放效果（静态图+放大动画）
3. 这是**降级方案**，输出的不是真正动画视频

---

## 依赖安装

```bash
python scripts/setup_deps.py
```

安装清单：Pillow, edge-tts, gTTS, pyttsx3, httpx, requests, pydub, FFmpeg/imageio-ffmpeg

---

## 脚本文件说明

| 脚本 | 用途 |
|------|------|
| `ai_video_generator.py` | AI视频/图片生成v3：即梦7种模式（text2img/text2video/img2video/ref2video/vivid2video/multimodal/video_extend） |
| `short_drama_renderer.py` | 短剧渲染主流程（v2: AI视频驱动） |
| `tts_engine.py` | TTS配音引擎v3：六层级回退链(火山→edge→gTTS→pyttsx3→SAPI5→静音)+指数退避重试+预检 |
| `script_generator.py` | 提示词→剧本JSON（v2.4：分镜细化字段 action/shot_type/camera/ambient/emotion/duration_seconds + 斜杠多选原型音色映射修复） |
| `script_parser.py` | 7种格式→剧本JSON |
| `script_director.py` | 半自动分镜流水线（5种模板：叙事/推宣/讲解/展示/情感） |
| `transition_effects.py` | FFmpeg转场特效（真实xfade转场，非黑帧） |
| `bgm_manager.py` | BGM混音 + 免版权曲库索引 + 音效合成 |
| `animate_video.py` | Manim动画（补充能力，默认不预览防卡死） |
| `setup_deps.py` | 依赖安装 |
| `video_api_config.json` | 即梦API配置（已预配端点和模型ID） |

---

## 5 种画风

| 画风 | 适合类型 | 特点 | 参考视频 |
|------|---------|------|---------|
| anime | 都市/玄幻/校园 | 日式动漫，色彩鲜艳 | - |
| qcomic | 古装/武侠/都市 | 国漫风格，线条大胆 | - |
| realistic | 都市/悬疑 | 写实风，电影感 | - |
| cute | 甜宠/校园/日常 | Q版可爱，色彩柔和 | - |
| korean_manga | 现言/都市/甜宠 | 韩式现言漫，低饱和莫兰迪色，暖粉肤色，中心聚焦构图，白色粗描边字幕 | @昭昭漫剪 |

### korean_manga 画风特色

基于抖音"一口气看完"长视频分析提炼的制作方法论：

**画面特征：**
- AI生成韩式现言漫插画（Midjourney级别质量）
- 中心聚焦近景构图：角色占画面~70%，面部在视觉黄金点
- 背景轻微虚化，边缘预留文字/UI空间
- 低饱和暖色莫兰迪色系：暖米色、柔棕色、灰绿底色
- 皮肤暖粉+橘粉腮红，无高饱和色块
- 全局暖黄LUT滤镜

**4层文字层级：**
- Tier 1（核心剧情字幕）：底部居中，白色粗体无衬线+细黑描边
- Tier 2（提示信息）：左上"全文X分钟"，右侧竖排"内容虚拟演绎 切勿带入现实"
- Tier 3（水印）：角色胸部位置"@账号名"，浅粉半透明
- Tier 4（平台UI）：底部右侧平台logo，默认不动

**氛围特效：**
- 白色/金色漂浮星点粒子（sparkle effect）
- 边缘云雾辉光晕
- 让静态AI图片有"活"的感觉

**微动效：**
- 角色呼吸式缩放微振
- 镜头缓慢推入（Ken Burns朝面部zoom）
- 字幕逐句淡入、切换淡出
- 戏剧高潮：闪白+微震

**制作模式：**
模板驱动批量生产：AI生成场景匹配插画 → 剪映导入 → 预设模板(字幕样式/水印位置/粒子效果/合规文字) → 配音+替换字幕 → 导出

---

## 输出规范

所有脚本均支持 `--ratio` 参数选择画面比例：`9:16`（竖屏）/ `16:9`（宽屏）/ `4:3`（横屏）/ `1:1` / `3:4` / `21:9`。

| 参数 | 竖屏模式(默认) | 横屏模式 | 宽屏模式 |
|------|---------------|---------|---------|
| 格式 | MP4 (H.264+AAC) | MP4 (H.264+AAC) | MP4 (H.264+AAC) |
| 分辨率 | 1080x1920 (9:16) | 1440x1080 (4:3) | 1920x1080 (16:9) |
| 帧率 | 24fps | 30fps | 30fps |
| 平台适配 | 抖音/快手 | 抖音/B站 | B站/YouTube |
| CLI 参数 | `--ratio 9:16` | `--ratio 4:3` | `--ratio 16:9` |

使用方式：
```bash
# 剧本生成时指定横屏
python scripts/script_generator.py --prompt "..." --ratio 16:9 --output drama.json

# 渲染时覆盖比例（优先于剧本JSON中的设置）
python scripts/short_drama_renderer.py --script drama.json --ratio 16:9 --output output.mp4

# 脚本解析时指定横屏
python scripts/script_parser.py --input script.txt --ratio 16:9 --output drama.json

# 分镜计划指定横屏
python scripts/script_director.py plan --topic "..." --ratio 16:9 -o project.json
```

剧本JSON中通过 `aspect_ratio` 字段控制：`"9:16"` (竖屏) / `"4:3"` (横屏) / `"16:9"` (宽屏)，CLI `--ratio` 参数优先级高于剧本字段。