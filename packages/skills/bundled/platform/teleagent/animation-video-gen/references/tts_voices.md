---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: 'fcdf8bb6-660c-46a2-a4b7-61b0bd2ef519'
  PropagateID: 'fcdf8bb6-660c-46a2-a4b7-61b0bd2ef519'
  ReservedCode1: 'd975bab2-9400-4ea4-93eb-afcc9905b0f0'
  ReservedCode2: 'd975bab2-9400-4ea4-93eb-afcc9905b0f0'
---

# TTS 音色参考 (v3)

## 六层级TTS回退链 (v3)

引擎自动按以下顺序回退，三大服务商独立：

| 优先级 | 后端 | 服务商 | 可用性 | 限制 |
|--------|------|--------|--------|------|
| L0 | 火山引擎 TTS | 字节跳动 | 需ARK_API_KEY | 需配置API Key |
| L1 | edge-tts | 微软 | 需网络+微软Token | 可能403/429 |
| L2 | gTTS | Google | 需网络，免费 | 无情感参数，单一音色 |
| L3 | pyttsx3 | 微软(本地) | 本地离线 | 较慢，音色少 |
| L4 | SAPI5 | 微软(本地) | 仅Windows | 无情感参数 |
| L5 | 静音占位 | FFmpeg | 始终可用 | 无语音 |

**v3 关键改进：** 多服务商独立，微软全线故障时 Google(gTTS) 或火山引擎仍可用。

**回退逻辑：**
1. 预检（health_check）探测可用后端，跳过已知不可用的
2. 每片段独立重试（指数退避：2s→4s→8s，默认3次）
3. 认证错误(403) → 直接换后端（不重试）
4. 限速(429) → 等待后重试同一后端
5. 网络错误 → 重试同一后端
6. 所有后端失败 → 生成静音占位（流程不中断）

---

## L0: 火山引擎 TTS 音色

需配置环境变量 `ARK_API_KEY`（与即梦视频生成共用同一Key）。

| 音色ID | 适用角色 | 风格 |
|--------|---------|------|
| zh_male_chunhou | 男主角 | 醇厚男声 |
| zh_male_cancan | 霸总、硬汉 | 灿灿男声 |
| zh_male_jieshuo | 旁白、解说 | 解说男声 |
| zh_female_qingxin | 女主角 | 清新女声 |
| zh_female_wenrou | 温柔角色 | 温柔女声 |
| zh_female_ganlian | 女强人 | 干练女声 |
| zh_female_chengshu | 成熟女性 | 成熟女声 |
| zh_female_tianmei | 甜系角色 | 甜美女声 |
| zh_female_tongsheng | 儿童 | 童声 |

---

## L1: edge-tts 中文音色列表

### 5个已验证可用音色

| 音色ID | 风格 | 适用角色 | 情感支持 |
|--------|------|---------|---------|
| zh-CN-YunxiNeural | 年轻男性，沉稳温暖 | 男主角、暖男 | cheerful, sad, angry, serious, friendly |
| zh-CN-YunjianNeural | 低沉有力，坚定刚毅 | 霸总、硬汉、反派 | angry, serious, sad |
| zh-CN-YunyangNeural | 新闻播音风，正式清晰 | 旁白、解说 | newscast, narrative, serious |
| zh-CN-XiaoxiaoNeural | 活泼开朗 | 女主角、闺蜜 | cheerful, angry, sad, friendly, gentle |
| zh-CN-XiaoyiNeural | 温柔细腻 | 温柔角色、恋人 | sad, gentle, cheerful |

### 3个已失效音色（v7.2.8，NoAudioReceived）

| 音色ID | 原适用角色 | 替代方案 |
|--------|-----------|---------|
| ~~zh-CN-XiaochenNeural~~ | 女强人 | → XiaoxiaoNeural (serious/angry) |
| ~~zh-CN-XiaomoNeural~~ | 成熟女性 | → XiaoxiaoNeural (narrative) |
| ~~zh-CN-XiaohanNeural~~ | 儿童 | → XiaoyiNeural (gentle) |

### 其他音色（未逐一验证）

| 音色ID | 风格 | 适用角色 |
|--------|------|---------|
| zh-CN-YunxiaNeural | 清亮少年/助手风 | 少年、AI助手 |
| zh-CN-YunzeNeural | 成熟儒雅 | 长辈、教授 |
| zh-CN-XiaomengNeural | 甜美可爱 | 小妹妹、甜妹 |
| zh-CN-XiaoruiNeural | 沉稳大气 | 女王、长辈 |

### 常用角色音色映射模板

```json
{
  "旁白": "zh-CN-YunyangNeural",
  "林墨": "zh-CN-YunjianNeural",
  "苏晚": "zh-CN-XiaoxiaoNeural",
  "老陈": "zh-CN-YunzeNeural",
  "小雨": "zh-CN-XiaoyiNeural"
}
```

---

## L2: gTTS (Google Text-to-Speech)

- 免费，无需API Key
- `pip install gTTS`
- 仅支持 `lang='zh-CN'`，无多音色选择
- 无情感参数（rate/pitch/volume/style 均无效）
- 作为微软全线故障时的独立备选

---

## 情感风格参数（仅 L0/L1 支持）

| emotion值 | 效果 | 建议语速调整 |
|-----------|------|-------------|
| angry | 愤怒/激动 | +15% |
| sad | 悲伤/低落 | -15% |
| cheerful | 开心/愉快 | +10% |
| serious | 严肃/郑重 | -5% |
| friendly | 友好/亲切 | +0% |
| gentle | 温柔/轻柔 | -5% |
| narrative | 叙述/旁白 | -5% |
| newscast | 新闻播报 | +0% |

## 语速/音量/音高调节（仅 L0/L1 支持）

```python
# 语速: 百分比调整
rate="+20%"    # 加快20%
rate="-10%"    # 减慢10%

# 音量
volume="+20%"  # 增大
volume="-10%"  # 减小

# 音高
pitch="+5Hz"   # 升高
pitch="-5Hz"   # 降低
```

---

**诊断命令：**
```bash
python scripts/tts_engine.py --script drama.json --health-check
```