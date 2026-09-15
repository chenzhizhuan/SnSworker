---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: 'd80c0341-1da8-44a2-b0f9-3ce98250d774'
  PropagateID: 'd80c0341-1da8-44a2-b0f9-3ce98250d774'
  ReservedCode1: 'ac8f6e22-0b3a-4e0b-9ae0-00df40bf509d'
  ReservedCode2: 'ac8f6e22-0b3a-4e0b-9ae0-00df40bf509d'
---

---
---

# 短剧制作指南

## 剧本JSON格式

完整的短剧剧本格式如下：

```json
{
  "title": "逆光而行",
  "style": "anime",
  "episodes": 1,
  "aspect_ratio": "9:16",
  "resolution": "1080x1920",
  "voice_mapping": {
    "旁白": "zh-CN-YunyangNeural",
    "林墨": "zh-CN-YunjianNeural",
    "苏晚": "zh-CN-XiaoxiaoNeural"
  },
  "bgm_mood": "tense",
  "scenes": [
    {
      "id": 1,
      "background_prompt": "夜晚的城市天台，霓虹灯闪烁，细雨绵绵",
      "characters": [
        {"name": "林墨", "position": "left", "prompt": "穿黑色风衣的年轻男人，表情坚毅，雨中侧脸"},
        {"name": "苏晚", "position": "right", "prompt": "撑红伞的女人，长发飘逸，表情复杂"}
      ],
      "dialogues": [
        {"speaker": "林墨", "text": "我不甘心！三年了，我不会放弃！", "emotion": "angry", "mode": "subtitle"},
        {"speaker": "苏晚", "text": "有些事，不是坚持就有结果的。", "emotion": "sad", "mode": "bubble"},
        {"speaker": "林墨", "text": "那你当初为什么还要开始？", "emotion": "serious", "mode": "subtitle"}
      ],
      "narration": "雨夜，天台上只剩两个人的对峙。",
      "transition": "fade_black"
    },
    {
      "id": 2,
      "background_prompt": "温暖的咖啡厅内景，阳光从落地窗洒入",
      "characters": [
        {"name": "苏晚", "position": "center", "prompt": "穿白色连衣裙的女人，低头搅咖啡"}
      ],
      "dialogues": [
        {"speaker": "苏晚", "text": "也许……我们都该放下了。", "emotion": "sad", "mode": "subtitle"}
      ],
      "narration": "第二天，她做了最后的决定。",
      "transition": "flash_white"
    }
  ]
}
```

## 字段说明

### 顶层字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| title | string | 是 | 短剧标题 |
| style | string | 否 | 画风: anime/qcomic/realistic/cute/korean_manga，默认 anime |
| episodes | int | 否 | 集数 |
| aspect_ratio | string | 否 | 画面比例: 9:16(竖屏)/4:3(横屏)/16:9(宽屏)，默认 9:16 |
| resolution | string | 否 | 分辨率，默认 1080x1920(竖屏) 或 1440x1080(横屏) |
| voice_mapping | object | 否 | 角色名→TTS音色映射 |
| bgm_mood | string | 否 | 整体BGM情感基调 |
| compliance | object | 否 | 合规声明配置（见下方） |
| watermark | object | 否 | 水印配置（见下方） |
| particles | object | 否 | 粒子特效配置（见下方） |
| scenes | array | 是 | 场景列表 |

### 场景字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | int | 是 | 场景编号 |
| background_prompt | string | 是 | 背景画面描述（用于AI生图） |
| characters | array | 否 | 场景中的角色列表 |
| dialogues | array | 否 | 对白列表 |
| narration | string | 否 | 旁白文字 |
| transition | string | 否 | 到下一场的转场效果 |

### 角色字段

| 字段 | 类型 | 说明 |
|------|------|------|
| name | string | 角色名 |
| position | string | 位置: left/center/right |
| prompt | string | 角色画面描述（用于AI生图） |

### 对白字段

| 字段 | 类型 | 说明 |
|------|------|------|
| speaker | string | 说话人 |
| text | string | 对白内容 |
| emotion | string | 情感: angry/sad/cheerful/serious/romantic/calm |
| mode | string | 显示模式: subtitle(字幕)/bubble(气泡) |

### 合规声明字段 (compliance)

```json
"compliance": {
  "enabled": true,
  "text": "内容虚拟演绎 切勿带入现实",
  "position": "right_vertical",
  "color": "#FFFFFF80"
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| enabled | bool | 是否启用合规声明 |
| text | string | 声明文字，默认"内容虚拟演绎 切勿带入现实" |
| position | string | 位置: right_vertical(右侧竖排)/bottom_left(左下) |
| color | string | 颜色(含透明度)，默认白色50%透明 |

### 水印字段 (watermark)

```json
"watermark": {
  "enabled": true,
  "text": "@昭昭漫剪",
  "position": "character_chest",
  "color": "#FFB6C180"
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| enabled | bool | 是否启用水印 |
| text | string | 水印文字 |
| position | string | 位置: character_chest(角色胸部)/bottom_right(右下) |
| color | string | 颜色(含透明度)，默认浅粉50%透明 |

### 粒子特效字段 (particles)

```json
"particles": {
  "enabled": true,
  "type": "sparkle",
  "color": "white_gold",
  "density": 30,
  "speed": 0.5
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| enabled | bool | 是否启用粒子特效 |
| type | string | 粒子类型: sparkle(星点)/petal(花瓣)/snow(雪花) |
| color | string | 粒子颜色: white_gold/white/pink |
| density | int | 粒子密度(1-100)，默认30 |
| speed | float | 漂浮速度(0.1-2.0)，默认0.5 |

### 场景扩展字段

| 字段 | 类型 | 说明 |
|------|------|------|
| breathing | bool | 角色呼吸微动效，默认true(仅korean_manga) |
| glow_edge | bool | 边缘辉光晕效果 |
| subtitle_tier | int | 字幕层级(1-4)，默认1(核心剧情) |

## 制作规格

### 抖音/快手适配

| 参数 | 抖音 | 快手 |
|------|------|------|
| 画面比例 | 9:16 | 9:16 |
| 分辨率 | 1080x1920 | 1080x1920 |
| 帧率 | 24-30fps | 24-30fps |
| 编码 | H.264 | H.264 |
| 时长限制 | 15s-15min | 15s-15min |
| 文件格式 | MP4 | MP4 |

### 短剧节奏建议

- 每集 1-3 分钟
- 每场景 5-15 秒
- 开头 3 秒必须有悬念/冲突
- 结尾必须有钩子（下集预告）

### 画风选择建议

| 画风 | 适合类型 | 特点 |
|------|---------|------|
| anime | 都市/玄幻/校园 | 日式动漫，色彩鲜艳 |
| qcomic | 古装/武侠/都市 | 国漫风格，线条大胆 |
| realistic | 都市/悬疑 | 写实风，电影感 |
| cute | 甜宠/校园/日常 | Q版可爱，色彩柔和 |
| korean_manga | 现言/都市/甜宠 | 韩式现言漫，莫兰迪暖色，中心聚焦，白描边字幕 |