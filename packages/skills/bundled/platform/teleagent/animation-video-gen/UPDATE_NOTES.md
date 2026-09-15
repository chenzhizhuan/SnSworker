---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '85bf145e-3248-4577-8f6f-64a98b3c9fe7'
  PropagateID: '85bf145e-3248-4577-8f6f-64a98b3c9fe7'
  ReservedCode1: '5d49406b-3036-48b6-b4cd-3f596cee12d3'
  ReservedCode2: '5d49406b-3036-48b6-b4cd-3f596cee12d3'
---

# 更新说明

## animation-video-gen 横屏输出功能升级

**版本：** v2.4 → v2.5
**更新日期：** 2026-09-09
**更新人：** 明明熊（TeleAgent）

---

## 一、更新背景

原 animation-video-gen 技能仅支持竖屏（9:16）输出，无法满足横屏场景需求（B站横屏视频、YouTube 横屏内容、企业宣传片等）。本次升级在不破坏现有竖屏功能的前提下，全链路新增横屏输出能力，用户可通过 `--ratio` 参数自由选择输出画面比例。

## 二、新增功能

### 1. 六种画面比例支持

| 比例 | 分辨率 | 适用场景 |
|------|--------|---------|
| 9:16 | 1080×1920 | 抖音/快手竖屏短剧（默认） |
| 16:9 | 1920×1080 | B站/YouTube 横屏视频 |
| 4:3 | 1440×1080 | 传统横屏/企业宣传片 |
| 1:1 | 1080×1080 | 朋友圈/小红书方形视频 |
| 3:4 | 1080×1440 | 竖屏海报式视频 |
| 21:9 | 2560×1080 | 电影宽银幕/超宽屏 |

### 2. `--ratio` CLI 参数（全脚本统一）

所有 5 个核心脚本均新增 `--ratio` 参数，选项统一为：

```
--ratio {9:16, 16:9, 4:3, 1:1, 3:4, 21:9}
```

### 3. 优先级机制

```
CLI --ratio 参数  >  剧本 JSON 的 aspect_ratio 字段  >  默认值 9:16
```

用户通过 CLI 指定的比例始终优先于剧本中预设的比例，未指定时自动读取剧本字段，均未指定时回退到 9:16 竖屏默认值。

## 三、修改文件清单

共修改 **6 个文件**：

### 1. `scripts/ai_video_generator.py`（1455行）

| 修改点 | 说明 |
|--------|------|
| `generate_scene_videos()` | 新增 `ratio` 参数，优先用传入值，其次读剧本 JSON 的 `aspect_ratio` 字段，默认 9:16 |
| `create_video_task()` | 原本已有 `ratio` 参数，本次通过 `generate_scene_videos()` 正确传递 |
| `effective_ratio` 逻辑 | `ratio or script.get("aspect_ratio", "9:16")`，确保比例在生成链路中正确传递 |

### 2. `scripts/script_generator.py`（560行）

| 修改点 | 说明 |
|--------|------|
| `RATIO_RESOLUTION_MAP` | 新增比例→分辨率映射表（6种比例） |
| `generate_from_prompt()` | 新增 `ratio` 参数（默认 "9:16"），写入剧本 JSON 的 `aspect_ratio` 和 `resolution` |
| `expand_outline()` | 新增 `ratio` 参数（默认 "9:16"），同上 |
| CLI `main()` | 新增 `--ratio` 参数，choices 为 6 种比例 |

### 3. `scripts/short_drama_renderer.py`（1194行）

| 修改点 | 说明 |
|--------|------|
| `__init__` | 新增 `ratio` 参数，CLI 优先于剧本 JSON；根据比例设置 WIDTH/HEIGHT（6种） |
| `self.aspect_ratio` | 新增实例属性，存储最终生效的画面比例 |
| `_generate_ai_videos()` | 调用 `generate_scene_videos()` 时传递 `ratio=self.aspect_ratio` |
| CLI `main()` | 新增 `--ratio` 参数（默认 None，表示读剧本 JSON） |

### 4. `scripts/script_parser.py`（559行）

| 修改点 | 说明 |
|--------|------|
| `RATIO_RESOLUTION_MAP` | 新增比例→分辨率映射表（6种比例） |
| `parse_script()` | 新增 `ratio` 参数；解析完成后统一覆盖 `script["aspect_ratio"]` 和 `script["resolution"]` |
| CLI `main()` | 新增 `--ratio` 参数，choices 为 6 种比例 |
| 各 Parser 类内部 | 保留 `"9:16"` 作为默认值（不动），在 `parse_script()` 出口处统一覆盖 |

### 5. `scripts/script_director.py`（243行）

| 修改点 | 说明 |
|--------|------|
| `RATIO_RESOLUTION_MAP` | 新增比例→分辨率映射表（6种比例） |
| `build_plan()` | `plan` 命令新增 `--ratio` 参数（默认 16:9，因为分镜导演通常做横屏内容） |
| 项目 JSON | `aspect_ratio` 和 `resolution` 字段写入项目文件 |
| `export_project()` | 从项目 JSON 读取 `aspect_ratio`，传递给 `step2_img2video` |

### 6. `SKILL.md`（403行）

| 修改点 | 说明 |
|--------|------|
| `description` | 追加横屏支持说明（英文） |
| `description_cn` | 追加横屏支持说明（中文） |
| 正文开头 | 新增横屏双模式说明 |
| 命令示例 | 添加 `--ratio 16:9` 横屏命令示例 |
| 输出规范表格 | 从竖屏单列扩展为竖屏/横屏/宽屏三列 |

## 四、全链路 ratio 传递路径

```
用户 CLI (--ratio 16:9)
    │
    ├─ script_generator.py     → 剧本 JSON 写入 aspect_ratio: "16:9"
    │
    ├─ script_parser.py       → 解析后统一覆盖 aspect_ratio + resolution
    │
    ├─ script_director.py     → 项目 JSON 写入 aspect_ratio: "16:9"
    │
    ├─ short_drama_renderer   → __init__ 读取 ratio → 设置 WIDTH/HEIGHT
    │         │
    │         └─ _generate_ai_videos(ratio=self.aspect_ratio)
    │                    │
    │                    └─ ai_video_generator.generate_scene_videos(ratio="16:9")
    │                               │
    │                               └─ create_video_task(ratio="16:9")
    │                                          │
    │                                          └─ 即梦 API 生成 16:9 视频
    │
    └─ ffmpeg 渲染合成 → 1920×1080 横屏 MP4 输出
```

## 五、向后兼容性

- **不传 `--ratio` 参数时**：所有脚本默认行为与升级前完全一致（9:16 竖屏）
- **剧本 JSON 已有 `aspect_ratio` 字段时**：自动读取，无需额外传参
- **`--ratio` 参数优先级最高**：可随时覆盖剧本中预设的比例
- **各 Parser 类内部默认值不变**：保留 `"9:16"` 作为 fallback，仅在出口处统一覆盖，不影响内部逻辑

## 六、使用示例

### 竖屏输出（默认，与原来一致）

```bash
python script_generator.py --topic "校园恋爱" --ratio 9:16
python short_drama_renderer.py --script drama_script.json
```

### 横屏 16:9 输出（本次新增）

```bash
python script_generator.py --topic "企业宣传片" --ratio 16:9
python short_drama_renderer.py --script drama_script.json --ratio 16:9
```

### 横屏 4:3 输出

```bash
python script_generator.py --topic "产品介绍" --ratio 4:3
python short_drama_renderer.py --script drama_script.json --ratio 4:3
```

### 分镜导演横屏项目

```bash
python script_director.py plan --topic "年度回顾" --ratio 16:9
python script_director.py export --project project.json
```

## 七、验证结果

- [x] 5 个脚本 CLI 均已添加 `--ratio` 参数，choices 统一
- [x] 3 份 `RATIO_RESOLUTION_MAP` 映射值一致
- [x] 全链路 ratio 传递正确：generator → parser → renderer → ai_video_generator → API
- [x] 优先级正确：CLI > 剧本 JSON > 默认 9:16
- [x] 向后兼容：不传参数时行为与升级前一致
- [x] SKILL.md 描述、示例、输出规范表格均已更新