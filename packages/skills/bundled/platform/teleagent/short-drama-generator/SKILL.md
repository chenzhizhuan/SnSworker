---
name: short-drama-generator
description: 根据剧本和人物特性自动生成竖屏短视频短剧（本地合成渲染 + 预留云端视频模型接口）。当用户提供剧本/脚本/台词/人物设定，希望自动生成、制作一部短视频、短剧、微短剧、漫剧，或把文字剧本转成带配音、字幕、运镜的可发布 MP4，或需要保存发送到抖音/红果短剧等平台时使用。触发词：生成短剧、短视频生成、剧本转视频、短剧制作、微短剧、竖屏短剧。
name_cn: 短剧视频生成器
description_cn: 根据剧本与人物设定，自动生成带配音、字幕、运镜的竖屏短视频，并打包为可发到短剧平台的发布包。
create_source: super-agent-skill-creator
---

# 短剧视频生成器

## 概述

把「剧本 + 人物设定」自动变成可发布的竖屏短剧：
剧本解析 → 分镜 → 多音色配音 → AI 场景插画 → 运镜 + 字幕 → 成片合成 → 发布包。

默认本地合成（edge-tts 在线配音 + AI 场景插画 + ffmpeg），零 API Key、零 GPU 即可出片；
AI 插画由内置 ImageGen 生成带人物与场景的竖屏画面（漫剧风格），无插画时自动回退渐变底图；
同时预留云端视频大模型接口（见文末扩展），后续接入可灵/即梦/海螺等实现真实动态画面。

## 工作流（按顺序执行）

1. **环境检查（首次）**
   `python scripts/check_env.py` —— 缺失依赖时 `python scripts/check_env.py --install` 自动安装

2. **解析剧本**
   `python scripts/parse_script.py 剧本.txt --characters 人物.json --out 输出目录`
   - 剧本：.txt/.md；人物：JSON（可选，缺省自动用默认音色）
   - 生成 `输出目录/.work/shots.json`（分镜清单）

3. **配音**
   `python scripts/tts.py --out 输出目录`
   - 引擎：edge-tts（在线微软语音）→ SAPI（Windows 本地兜底），失败自动重试
   - 每镜一个 mp3，时长写回 shots.json

4. **渲染成片**
   `python scripts/render_video.py --out 输出目录 [--preview 3]`
   - 每场景生成底图，每镜自动运镜（推/拉）＋字幕＋配音
   - 输出 `输出目录/剧名.mp4`（1080x1920 / 30fps / H.264+AAC）

   **AI 场景插画（推荐）**：`parse_script.py` 会在 `shots.json` 的 `scenes` 数组中
   为每个场景生成英文插画提示词（含人物 age/gender/desc）。用 ImageGen 逐场景生成
   竖屏 9:16 插画（建议 1440x2560），转 PNG 后保存为
   `输出目录/.work/frames/scene_<场景id:04d>.png`。
   渲染时自动检测并优先复用这些插画；未提供时回退本地渐变底图。

   插画文件命名规则（与 scenes 数组的 id 字段对应）：
   ```
   scene_0001.png  ← 场景 1
   scene_0002.png  ← 场景 2
   ...
   ```

5. **生成发布包**
   `python scripts/publish_pack.py --video 成片.mp4 --title "钩子标题" --desc "简介" --tags "短剧,都市情感" --out 输出目录 [--zip]`
   - 输出封面 + 发布文案 JSON + 成片副本（zip 可选），可直接上传抖音/红果

完整示例见 `assets/sample-drama/README.md`；平台标题/简介/话题规范见 `references/platform-format.md`。

## 剧本格式

```
# 剧名
【场景：深夜写字楼天台】       ← 场景标记（决定画面）
旁白：三年了，她终于回来了。   ← 旁白（无说话人名牌）
林小满：你还记得约定吗？       ← 角色台词（自动分配音色）
字幕：屏幕字                 ← 仅字幕不配音
（她低下头笑了笑）           ← 动作描述（配音为旁白+字幕）
```

- `## 人物` 章节自动跳过，不生成分镜
- 未识别文本当作动作描述处理

## 人物设定 JSON（可选）

```json
{
  "characters": {
    "林小满": {"voice": "zh-CN-XiaoxiaoNeural", "gender": "女", "desc": "温柔女主"},
    "陆沉":   {"voice": "zh-CN-YunjianNeural", "gender": "男", "desc": "深沉男主"}
  }
}
```

- `voice`：edge-tts 中文音色。常见：女声 XiaoxiaoNeural / XiaoyiNeural；男声 YunxiNeural / YunjianNeural / YunyangNeural
- 未指定音色时：角色默认女声 XiaoxiaoNeural，旁白默认男声 YunxiNeural
- 人物 `desc` 可留作未来云端视频模型生成角色形象

## 平台规范要点

- 抖音/红果短剧：竖屏 9:16、MP4(H.264+AAC)、≥30fps——本技能默认参数已满足
- 标题 ≤25 字带钩子；简介 55 字内；话题 3-5 个（1 热门口 + 2 垂类 + 1 情绪词）
- 详细规范见 `references/platform-format.md`

## 画面升级路径

### 已支持：AI 场景插画（漫剧风格）
```
parse_script.py 生成 scenes[].prompt（英文提示词 + 人物描述）
    → ImageGen 逐场景生成竖屏插画（1440x2560 PNG）
    → 保存为 .work/frames/scene_<id:04d>.png
    → render_video.py 自动复用 AI 插画 + zoompan 运镜 + 字幕
```
- 每个场景一张静态插画，所有分镜共享同场景画面 + 不同字幕/运镜
- 效果：漫剧/绘本风格，画面有真实人物形象与场景氛围
- 零额外费用，无需 API Key

### 预留：云端视频大模型（真实动态画面）
当前管线：
```
场景文本 → render_scene_image() 生成/复用底图 → zoompan 运镜 → 字幕叠加 → 单镜 mp4 → concat
```

升级真实动态画面只需：
- 把 `render_video.py` 中 `render_scene_image()` 替换为文生视频 API 调用（返回 9:16 片段）
- 每镜独立 clip（`clips/clip_NNN.mp4`）结构不变，云端片段可直接替换后重新 concat
- `shots.json` 已含 scene / dialogue / voice / duration 字段，云端管线可直接消费

## 注意事项

- 剧本文件会被系统自动注入 AIGC 水印（不可见字符），解析器已内置清洗，无需处理
- Windows 控制台若报 GBK 编码错误，先执行 `$env:PYTHONIOENCODING="utf-8"`
- 依赖：edge-tts、Pillow、numpy、imageio-ffmpeg（check_env.py --install 自动装）
- ffmpeg 由 imageio-ffmpeg 内置，无需单独安装
- 配音失败自动重试 3 次；仍失败时该镜改为无配音仅字幕