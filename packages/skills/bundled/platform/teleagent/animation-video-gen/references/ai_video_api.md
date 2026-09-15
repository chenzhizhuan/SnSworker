---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '7a8d7de6-796b-4680-8335-6928ac8c6d7d'
  PropagateID: '7a8d7de6-796b-4680-8335-6928ac8c6d7d'
  ReservedCode1: '65951ca8-50b7-45e9-9a78-36710e71a936'
  ReservedCode2: '65951ca8-50b7-45e9-9a78-36710e71a936'
---

# AI 视频/图片生成 API 参考

本技能通过即梦（火山方舟）Seedream/Seedance API 生成视频和图片。
API 配置已预配在 `scripts/video_api_config.json` 中，只需设置环境变量 `ARK_API_KEY`。

---

## API 端点

| 功能 | 方法 | 端点 |
|------|------|------|
| 视频生成 | POST | `https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks` |
| 视频查询 | GET | `https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks/{task_id}` |
| 视频取消 | DELETE | `https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks/{task_id}` |
| 图片生成 | POST | `https://ark.cn-beijing.volces.com/api/v3/images/generations` |

认证：`Authorization: Bearer {ARK_API_KEY}`

---

## 模型矩阵

### 视频模型 (Seedance)

| 模型名 | model_id | 时长范围 | 分辨率 | 支持模式 |
|--------|----------|---------|--------|---------|
| seedance-2.0 | doubao-seedance-2.0 | 4-15秒 | 720p | text2video, img2video, firstlast2video, multimodal, vivid2video, video_extend |
| seedance-2.0-fast | doubao-seedance-2.0-fast | 4-15秒 | 720p | text2video, img2video, firstlast2video, multimodal |
| seedance-2.0-mini | doubao-seedance-2.0-mini | 4-10秒 | 720p | text2video, img2video, firstlast2video |
| seedance-1.5-pro | doubao-seedance-1.5-pro | 4-12秒 | 1080p | text2video, img2video, firstlast2video, draft_mode |

### 图片模型 (Seedream)

| 模型名 | model_id | 最大分辨率 | 特性 |
|--------|----------|-----------|------|
| seedream-5.0-pro | doubao-seedream-5.0-pro | 4K | text2img, img2img, web_search, sequential_img |
| seedream-5.0 | doubao-seedream-5.0 | 4K | text2img, img2img, web_search |
| seedream-5.0-lite | doubao-seedream-5.0-lite | 2K | text2img, img2img |

---

## 7 种生成模式详解

### 1. text2img — 文生图
```json
{
  "model": "doubao-seedream-5.0-lite",
  "prompt": "城堡广场, 赛博朋克风格",
  "size": "2048x2048",
  "n": 1,
  "seed": -1
}
```

### 2. text2video — 文生视频
```json
{
  "model": "doubao-seedance-2.0",
  "content": [{"type": "text", "text": "女子转身, anime style, 9:16"}],
  "ratio": "9:16",
  "duration": 5,
  "seed": -1,
  "generate_audio": true,
  "watermark": false,
  "return_last_frame": false
}
```

### 3. img2video — 图生视频（首帧±尾帧）
```json
{
  "model": "doubao-seedance-2.0",
  "content": [
    {"type": "text", "text": "女子从站到坐"},
    {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,...", "role": "first_frame"}},
    {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,...", "role": "last_frame"}}
  ],
  "ratio": "adaptive",
  "duration": 5
}
```

### 4. ref2video — 参考图生视频（≤9张）
```json
{
  "content": [
    {"type": "text", "text": "[图1]角色造型 [图2]场景背景"},
    {"type": "image_url", "image_url": {"url": "...", "role": "reference_image"}},
    {"type": "image_url", "image_url": {"url": "...", "role": "reference_image"}}
  ]
}
```

### 5. vivid2video — 参考视频复刻（≤3段, 总≤15s）
```json
{
  "content": [
    {"type": "text", "text": "赛博朋克城市, 相同运镜"},
    {"type": "video_url", "video_url": {"url": "...", "role": "reference_video"}}
  ]
}
```

### 6. multimodal — 多模态参考融合
图片(≤9) + 视频(≤3, 总≤15s) + 音频(≤3, 总≤15s) + 文本，全能融合。
```json
{
  "content": [
    {"type": "text", "text": "[图1]角色 [图2]场景 [视频1]运动参考"},
    {"type": "image_url", "image_url": {"url": "...", "role": "reference_image"}},
    {"type": "video_url", "video_url": {"url": "...", "role": "reference_video"}},
    {"type": "audio_url", "audio_url": {"url": "...", "role": "reference_audio"}}
  ]
}
```

### 7. video_extend — 视频续写
使用 `return_last_frame: true`，响应中包含 `last_frame_url`，下载后作为下一段视频的首帧。

---

## 响应格式

### 视频任务创建
```json
{
  "id": "task_xxx"
}
```

### 视频任务查询
```json
{
  "id": "task_xxx",
  "status": "succeeded",
  "output": {
    "video_url": "https://...",
    "duration": 5.0,
    "last_frame_url": "https://..."
  }
}
```

状态值：`processing` | `succeeded` | `failed`

### 图片任务
```json
{
  "data": {
    "images": [{"url": "https://..."}]
  }
}
```

---

## 即梦特色参数

| 参数 | 类型 | 说明 | 默认值 |
|------|------|------|--------|
| `generate_audio` | bool | 生成与画面同步的音频 | true |
| `return_last_frame` | bool | 返回尾帧图像（用于视频续写） | false |
| `watermark` | bool | 是否添加水印 | false |
| `ratio` | string | 宽高比: 16:9/4:3/1:1/3:4/9:16/21:9/adaptive | adaptive |
| `resolution` | string | 分辨率: 480p/720p/1080p | 由模型决定 |
| `tools` | array | `[{"type": "web_search"}]` 联网搜索增强 | 无 |
| `draft` | bool | Draft样片模式（仅1.5-pro） | false |
| `service_tier` | string | 推理等级: default/flex | 无 |

---

## 配置文件

`scripts/video_api_config.json` 已预配即梦 API 端点和全部模型 ID。用户只需设置环境变量：

```bash
set ARK_API_KEY=your-api-key-here
```

获取 API Key：https://console.volcengine.com/ark

---

## 提示词最佳实践

- **中文+英文混合**效果最佳：中文描述剧情和角色，英文描述画风和运镜
- **竖屏后缀**: 始终添加 "9:16 vertical composition"
- **画风后缀**: "anime style" / "Chinese manhua" / "photorealistic" / "kawaii chibi"
- **运镜后缀**: "close-up shot" / "slow pan" / "zoom in" / "tracking shot"
- **动作描述**: 具体描述角色动作，如 "woman turns around, hair flowing in wind"
- **多模态引用**: 在 prompt 中用 `[图1]...[图2]...` 显式指定各参考素材的作用
- **避免**: "文字" "水印" "logo" (模型不会生成文字)

---

## 回退策略

当 API Key 未设置或 API 调用失败时:
1. 自动回退到 ImageGen + Ken Burns 缩放模式（静态图+缓慢放大）
2. 这不是真正的动画视频，仅作为降级方案
3. 设置 `ARK_API_KEY` 环境变量后即可使用完整即梦 API 功能

---

## 旧版别名兼容

以下旧模型别名仍可使用，自动映射到新模型：

| 旧别名 | 映射到 |
|--------|--------|
| pro | seedance-2.0 |
| lite | seedance-2.0-fast |
| seedance-2.0-pro | seedance-2.0 |
| seedance-2.0-lite | seedance-2.0-fast |