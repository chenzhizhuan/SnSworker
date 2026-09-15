---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: 'd83aaf49-c1f8-4887-a985-dc9ebad34f54'
  PropagateID: 'd83aaf49-c1f8-4887-a985-dc9ebad34f54'
  ReservedCode1: '71fa247d-72a2-4732-8ee7-3ff751bb1d1c'
  ReservedCode2: '71fa247d-72a2-4732-8ee7-3ff751bb1d1c'
---

# 示例短剧《都市重逢》

## 人物设定（characters.json）

```json
{
  "characters": {
    "林小满": {"voice": "zh-CN-XiaoxiaoNeural", "gender": "女", "desc": "女主，温柔坚定"},
    "陆沉": {"voice": "zh-CN-YunjianNeural", "gender": "男", "desc": "男主，内敛深沉"},
    "旁白": {"voice": "zh-CN-YunxiNeural", "gender": "男", "desc": "叙述者"}
  }
}
```

## 剧本文本（script.txt）

```
# 都市重逢

【场景：深夜写字楼天台】
旁白：三年了，她终于又回到了这座城市。
林小满：陆沉，你还记得我们的约定吗？
陆沉：记得，只是我没想到，你真的会回来。

【场景：老城咖啡店】
林小满：这杯咖啡，还和从前一样苦。
陆沉：苦的从来不是咖啡。
（林小满低头笑了笑，没有说话）

【场景：清晨江边】
旁白：有些话，说了就是一辈子。
林小满：往后余生，请多指教。
```

## 使用方式

```powershell
# 1. 解析
python parse_script.py script.txt --characters characters.json --out ./output
# 2. 配音
python tts.py --out ./output
# 3. 渲染
python render_video.py --out ./output
# 4. 发布包
python publish_pack.py --video ./output/都市重逢.mp4 --title "被全网骂退圈三年后，影后带着真相杀回来了" --tags "短剧,都市情感,反转" --out ./output --zip
```

> AI生成