---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '5c6b2092-3096-4a85-aa8b-68c1b4c71535'
  PropagateID: '5c6b2092-3096-4a85-aa8b-68c1b4c71535'
  ReservedCode1: '2985b5ff-0fba-49cd-b96d-75a3ea62ace0'
  ReservedCode2: '2985b5ff-0fba-49cd-b96d-75a3ea62ace0'
---

# 免版权素材资源清单（BGM / 音效 / 图片 / 视频）

## 使用原则

只使用授权清晰、可商用的素材。优先许可：
- CC0（公有领域）
- CC BY（仅署名）
- CC BY-SA（署名+相同方式共享）
- Royalty-free（免版税，可用于商用）

**严禁**使用未经许可的版权角色、音乐、视频、美术素材。

## BGM 免费音乐库

| 来源 | 网址 | 许可 | 备注 |
|------|------|------|------|
| Pixabay Music | https://pixabay.com/music/ | Pixabay License（免版税） | 曲库大，可按情绪搜索 |
| Mixkit | https://mixkit.co/free-stock-music/ | Mixkit License | 免费商用 |
| Free Music Archive | https://freemusicarchive.org/ | 各曲目不同 | 需逐曲确认许可 |
| Incompetech | https://incompetech.com/music/ | CC BY | Kevin MacLeod 曲库 |
| Bensound | https://www.bensound.com/ | Bensound License | 署名免费 |
| YouTube Audio Library | https://studio.youtube.com | YouTube License | YouTube 内容免费 |

### 短剧常用 BGM 分类与搜索词

| 情绪（mood） | 搜索关键词 | 典型用途 |
|--------------|-----------|---------|
| sad（悲伤） | "piano emotional", "sad strings", "heartbreak" | 离别、虐心、回忆 |
| tense（紧张） | "suspense dark", "thriller", "dark ambient" | 冲突、揭底、对峙 |
| romantic（浪漫） | "love gentle", "romantic piano" | 表白、甜蜜、心动 |
| happy（开心） | "happy upbeat", "energetic pop", "cheerful" | 喜剧、日常、反转爽点 |
| epic（史诗） | "cinematic epic", "orchestral", "heroic" | 高潮、打斗、反转 |
| mysterious（神秘） | "mysterious", "ambient synth", "mystery" | 伏笔、探索、穿越 |
| action（动作） | "action", "battle", "intense drums" | 追逐、打斗、快节奏 |
| calm（平静） | "lo-fi chill", "ambient calm", "relax" | 蒙太奇、日常过场 |

> 本地曲库目录：设置环境变量 `BGM_LIBRARY_DIR` 指向下载目录，`bgm_manager.py scan` 自动按
> 子目录（tense/happy/...）或文件名关键词索引，`match_bgm_for_scene()` 直接返回文件路径。

## 音效（SFX）来源

| 来源 | URL | 许可 |
|------|-----|------|
| Pixabay SFX | https://pixabay.com/sound-effects/ | Pixabay License |
| Mixkit SFX | https://mixkit.co/free-sound-effects/ | Mixkit License |
| Freesound | https://freesound.org/ | CC（逐条不同） |
| ZapSplat | https://www.zapsplat.com/ | ZapSplat License |

### 常用音效（本技能可直接合成，无需下载）

| 音效名 | 合成 | 说明 |
|--------|------|------|
| heartbeat | 支持 | 低频双脉冲心跳 |
| footsteps | 支持 | 低频短促脚步 |
| clock_tick | 支持 | 清脆钟摆滴答 |
| phone_ring | 支持 | 440/660Hz 双音响铃 |
| rain | 支持 | 白噪+带通≈雨声 |
| wind | 支持 | 粉红噪声低通≈风声 |
| crowd | 支持 | 人群嘈杂 |
| thunder_hit | 支持 | 雷击轰鸣 |
| glass_break | 支持 | 玻璃碎裂 |
| door_close | 支持 | 关门撞击 |
| car / sword | 需下载 | 建议从上方免版权库获取 |

用法：`python scripts/bgm_manager.py synth --name heartbeat --output hb.mp3 --duration 5`

## 图片素材（场景生成/参考）

| 来源 | URL | 许可 | 备注 |
|------|-----|------|------|
| Pixabay | https://pixabay.com/images/ | Pixabay License | 照片+插画 |
| Unsplash | https://unsplash.com/ | Unsplash License | 高质量照片 |
| Pexels | https://www.pexels.com/ | Pexels License | 照片+视频 |
| Wikimedia Commons | https://commons.wikimedia.org/ | 逐文件不同 | 需核对 |
| OpenClipart | https://openclipart.org/ | CC0 | 矢量剪贴画 |

**提示**：角色图优先用 AI 生成（ImageGen），避免肖像权/版权问题，且风格更统一。

## 视频素材（参考/素材）

| 来源 | URL | 许可 |
|------|-----|------|
| Pixabay Video | https://pixabay.com/videos/ | Pixabay License |
| Pexels Video | https://www.pexels.com/videos/ | Pexels License |
| Mixkit Video | https://mixkit.co/free-stock-video/ | Mixkit License |
| Coverr | https://coverr.co/ | Coverr License |

## AI 生成内容

- AI 生成图片/视频在多数司法辖区无版权争议，可放心用于场景背景、角色参考、视频帧
- 保持跨场景风格一致（建议固定画风参数：anime / qcomic / realistic / cute / korean_manga）
- 短剧优先插画/动漫风格（连贯性好于写实）

> AI生成