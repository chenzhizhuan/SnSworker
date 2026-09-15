# API 参考：media-hub MCP 服务

## 端点与认证

| 项 | 值 |
|---|---|
| 传输协议 | Streamable HTTP（MCP 2025-03-26 规范）|
| 鉴权 | 首次使用时调用 `get_auth` 工具获取凭证，自动写入 `.mcp.json`，无需手动配置 |

## 工具列表

| 工具 | 用途 |
|---|---|
| generate_image | 生成图片，支持多供应商自动轮换（provider="auto"）|
| generate_video | 生成视频，支持多供应商自动轮换（provider="auto"）|
| list_providers | 列出所有支持的供应商及其模态 |
| check_provider_status | 检查哪些供应商的 API key 已配置可用 |

## 工具1：generate_image

生成图片。通过 `provider="auto"` 自动轮换可用供应商（pollinations → agnes → zhipu → modelscope 等），失败自动故障转移。

### 参数

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| provider | string | 是 | 供应商：`auto`（推荐）、`pollinations`、`zhipu`、`modelscope`、`agnes`、`aether`、`custom`；`auto`/`round-robin` 自动轮换 |
| prompt | string | 是 | 文本提示词（中英文均可，英文效果更佳） |
| model | string | 否 | 指定模型（如 zhipu 用 `CogView-3-Flash`），默认各供应商自有默认 |
| size | string | 否 | 图片尺寸如 `"1024x1024"`，默认 `"1024x1024"` |
| seed | int | 否 | 随机种子，-1 为随机（默认） |
| image_url | string | 否 | 源图片 URL（用于图生图） |
| n | int | 否 | 生成数量，默认 1 |
| provider_params | object | 否 | 供应商特定参数透传 |

### 返回

```json
{"ok": true, "provider": "pollinations", "url": "https://...", "local_path": "..."}
```

### 支持的供应商

| provider | 模态 | 模型 | 是否需 key |
|---|---|---|---|
| pollinations | image | sana | 否（免费） |
| zhipu | image | CogView-3-Flash | 是 |
| modelscope | image | FLUX | 是 |
| agnes | image | agnes-image-2.0-flash | 否 |
| aether | image | — | 是 |

## 工具2：generate_video

生成视频。通过 `provider="auto"` 自动轮换可用供应商（pollinations → agnes → zhipu 等），失败自动故障转移。同步返回结果，无需手动轮询。

### 参数

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| provider | string | 是 | 供应商：`auto`（推荐）、`pollinations`、`zhipu`、`agnes`、`custom`；`auto` 自动轮换 |
| prompt | string | 是 | 视频内容描述（建议加入运镜/氛围描述） |
| model | string | 否 | 指定模型（如 zhipu 用 `CogVideoX-Flash`） |
| image_url | string | 否 | 起始图片 URL（用于图生视频） |
| seed | int | 否 | 随机种子，-1 为随机（默认） |
| duration | int | 否 | 视频时长秒数，默认 5（单次最大5秒） |
| aspect_ratio | string | 否 | 宽高比如 `"16:9"`、`"9:16"`、`"1:1"`，默认 `"16:9"` |
| provider_params | object | 否 | 供应商特定参数透传 |

### 返回

```json
{"ok": true, "provider": "agnes", "url": "https://...", "local_path": "..."}
```

### 像素约束（视频）

- 总像素范围 [3,686,400, 16,777,216]
- 宽高比范围 [1/16, 16]
- 不符合尺寸规则会被服务端拦截

### 支持的供应商

| provider | 模态 | 模型 | 是否需 key |
|---|---|---|---|
| agnes | video | agnes-video-v2.0 | 否 |
| zhipu | video | CogVideoX-Flash | 是 |
| pollinations | video | — | 否（但成功率较低） |

## 工具3：list_providers

列出所有支持的供应商、各自支持的模态（image/video）及所需环境变量。

### 参数

无

### 返回

JSON 列表，每项包含 provider 名称、支持模态、所需环境变量等。

> 注意：此工具在某些版本存在服务端 Bug（"Object of type coroutine is not JSON serializable"），不影响 generate_image/generate_video 正常使用。

## 工具4：check_provider_status

检查当前哪些供应商的 API key / token 已配置可用。

### 参数

无

### 返回

JSON，列出各供应商的状态（configured / missing）及缺少的环境变量名。

---

## 常用工作流示例

### 1. 文生图（provider=auto 自动轮换）

```
generate_image(
  provider="auto",
  prompt="日落时分的城市天际线，电影感，柔光，金色光线",
  size="1024x1024"
)
```

### 2. 文生图（横版 16:9）

```
generate_image(
  provider="auto",
  prompt="赛博朋克街道，霓虹灯，雨水倒影",
  size="1920x1080"
)
```

### 3. 图生图

```
generate_image(
  provider="auto",
  prompt="把照片转为水彩画风格",
  image_url="https://example.com/source.jpg"
)
```

### 4. 文生视频（指定时长和宽高比）

```
generate_video(
  provider="auto",
  prompt="镜头缓慢推进，雨夜街道，人物撑伞走过",
  duration=5,
  aspect_ratio="16:9"
)
```

### 5. 图生视频

```
generate_video(
  provider="auto",
  prompt="让人物缓缓转头微笑，背景树叶轻摆",
  image_url="https://example.com/portrait.jpg",
  duration=5
)
```

### 6. 检查供应商状态

```
check_provider_status()
```

### 7. 长视频分段生成与合并

当需要超过5秒的视频时，将视频拆分为多个5秒分段，分别生成后合并：

```bash
# 创建分镜脚本
cat > storyboard.json << 'EOF'
{
  "aspect_ratio": "16:9",
  "segments": [
    {"prompt": "镜头1：星空开场...", "duration": 5, "seed": -1},
    {"prompt": "镜头2：办公室场景...", "duration": 5, "seed": -1},
    {"prompt": "镜头3：数据安全...", "duration": 5, "seed": -1},
    {"prompt": "镜头4：品牌收尾...", "duration": 5, "seed": -1}
  ]
}
EOF

# 执行分段生成与合并
python scripts/generate_long_video.py --storyboard storyboard.json --output output.mp4
```

每段5秒，4段合并为20秒完整视频。脚本自动处理：
- 逐段调用 generate_video（provider="auto"）
- 下载所有片段
- 使用 ffmpeg 合并为单个MP4文件
- 队列满（503）自动重试

### 8. 提示词智能构建

```bash
# 交互式构建
python scripts/prompt_builder.py --interactive

# 直接构建英文提示词
python scripts/prompt_builder.py --content "城市夜景" --style cyberpunk --type video --lang en

# 列出所有风格
python scripts/prompt_builder.py --list-styles
```

### 9. 旁白配音与字幕合成

为已生成视频添加 TTS 旁白配音和自动对齐字幕：

```bash
# 基本用法（自动选引擎，烧录字幕 + SRT 文件）
python scripts/add_voice_subtitle.py \
  --video input.mp4 \
  --narration narration.txt \
  --output output_配音.mp4

# 直接传文本（用 | 分段）
python scripts/add_voice_subtitle.py \
  --video input.mp4 \
  --narration-text "第一段旁白|第二段旁白" \
  --output output.mp4

# 指定男声 + 软字幕
python scripts/add_voice_subtitle.py \
  --video input.mp4 \
  --narration n.txt \
  --engine edge --voice yunxi \
  --subtitle-mode subtitle \
  --output output.mp4
```

#### 参数

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| --video | path | 是 | 输入视频路径 |
| --narration | path | 否* | 旁白文本文件（每行一段） |
| --narration-text | string | 否* | 旁白文本（用 \| 分段），与 --narration 二选一 |
| --engine | enum | 否 | TTS 引擎：auto/edge/sapi，默认 auto |
| --voice | string | 否 | 声音：edge 用 xiaoxiao/yunxi 等；sapi 用 huihui/zira |
| --subtitle-mode | enum | 否 | 字幕模式：burn/subtitle/both/none，默认 burn |
| --output | path | 否 | 输出视频（默认桌面） |
| --srt-output | path | 否 | SRT 字幕输出路径（both 模式下默认加 _字幕后缀，避免播放器自动加载叠加） |
| --font-size | int | 否 | 字幕字号，默认 22 |
| --margin-v | int | 否 | 字幕底部边距，默认 40 |

#### 双 TTS 引擎

- **edge-tts**（默认优先）：微软 Edge 在线 TTS，音质自然，男/女多声色，需 `pip install edge-tts` + 联网
- **Windows SAPI**（自动回退）：系统自带，离线可用，中文女声 Huihui

#### 可用声音

| 引擎 | key | 完整 voice id |
|---|---|---|
| edge | xiaoxiao（默认女） | zh-CN-XiaoxiaoNeural |
| edge | xiaoyi（女） | zh-CN-XiaoyiNeural |
| edge | yunxi（男） | zh-CN-YunxiNeural |
| edge | yunyang（男） | zh-CN-YunxiNeural |
| edge | yunjian（男） | zh-CN-YunjianNeural |
| sapi | huihui（中文女） | - |
| sapi | zira（英文女） | - |

## 错误处理

### 生成失败

- **media-hub 工具不可用**：检查 .mcp.json 配置和 X-Request-Trace；若配置未生效（如尚未重启应用），可通过 Pollinations 免费 URL API 直接生成图片作为零配置降级方案
- **auto 连续失败**：调用 `check_provider_status()` 查看可用供应商，指定具体 provider 重试
- **4xx**：通常是参数问题，检查 size/aspect_ratio 是否符合像素规则、prompt 是否非空
- **5xx**：服务端临时问题，等待 30 秒后重试
- **503 video_queue_full**：视频队列已满，等待 35 秒后重试，最多6次
- **网络超时**：再试一次；连续失败则告知用户服务可能不可用

### 长视频分段失败

- 单段失败：跳过该段，继续生成其余段
- 合并失败：保留分段文件，提示用户手动合并
- ffmpeg不可用：安装 `imageio-ffmpeg`（`pip install imageio-ffmpeg`）

### 配音字幕失败

- **edge-tts 未安装/断网**：自动回退 Windows SAPI（系统自带，离线可用）
- **SAPI 生成失败**：检查 pywin32：`pip install pywin32`
- **字幕烧录失败**（filter graph 报错）：确认 ffmpeg 启用了 libass；或改用 `--subtitle-mode subtitle` 软字幕
- **中文显示为方块/乱码**：确认 `C:\Windows\Fonts` 下有 msyh.ttc/simhei.ttf，脚本自动降级选用
- **旁白时长与视频不匹配**：配音较短时视频后半静音，建议按分镜段数准备对应旁白行数
- **字幕重复显示（上下两行相同）**：播放器自动加载了同目录同名 srt 并叠加在硬字幕上。解决：用 `--subtitle-mode burn`（默认）不输出 srt；或删除多余 srt；或在播放器中关闭软字幕

## 模型能力对照

### pollinations（免费，免 key）
- 图片：sana 模型，速度快
- 视频：成功率较低，通常作为 auto 轮换中的第一个尝试

### agnes（免费，免 key）
- 图片：agnes-image-2.0-flash / agnes-image-2.1-flash
- 视频：agnes-video-v2.0，单次最大5秒，异步任务（media-hub 已封装为同步）

### zhipu（需 key）
- 图片：CogView-3-Flash
- 视频：CogVideoX-Flash