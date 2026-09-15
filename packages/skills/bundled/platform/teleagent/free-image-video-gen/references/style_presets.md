# 风格预设完整参考

本文件列出所有内置风格预设、运镜模板和分辨率版式，供 `prompt_builder.py` 和智能体直接参考使用。

---

## 一、风格预设（20种）

### 图像 + 视频通用风格

| 风格ID | 中文名 | 英文名 | 关键词摘要 | 色调 | 适用场景 |
|--------|--------|--------|-----------|------|---------|
| cinematic | 电影感 | Cinematic | cinematic lighting, shallow depth of field, film grain, dramatic shadows | teal and orange | 人物特写、情感叙事、品牌宣传 |
| realistic | 写实摄影 | Realistic Photography | photorealistic, ultra-detailed, natural lighting, DSLR quality | natural colors | 产品摄影、纪实、建筑摄影 |
| cyberpunk | 赛博朋克 | Cyberpunk | neon lights, rain-soaked streets, holographic signs, futuristic megacity | magenta and cyan | 科幻主题、未来城市、科技产品 |
| chinese_ink | 中国水墨 | Chinese Ink | ink painting, brush strokes, negative space, misty mountains, zen | monochrome ink | 传统文化、意境表达、品牌东方美学 |
| minimalist | 极简主义 | Minimalist | negative space, limited palette, clean, simple, geometric | monochrome/duotone | 产品海报、品牌视觉、社交媒体 |
| 3d_render | 3D渲染 | 3D Render | C4D, Blender, octane render, soft shadows, material textures | soft pastel/studio | 产品展示、品牌吉祥物、概念设计 |
| anime_style | 动漫风格 | Anime Style | cel shading, vibrant colors, detailed background, Ghibli inspired | vibrant saturated | IP设计、内容创作、游戏素材 |
| vintage_film | 复古胶片 | Vintage Film | 35mm grain, light leaks, faded colors, analog warmth, nostalgic | faded warm/sepia | 怀旧主题、品牌复古调性、vlog |
| fantasy | 奇幻史诗 | Fantasy Epic | epic landscape, magical atmosphere, ethereal light, floating islands | ethereal gold/blue | 游戏宣传、奇幻主题、概念艺术 |

### 仅图片风格

| 风格ID | 中文名 | 英文名 | 关键词摘要 | 适用场景 |
|--------|--------|--------|-----------|---------|
| flat_illustration | 扁平插画 | Flat Illustration | flat design, vector style, bold colors, minimal detail | UI设计、信息图、社交媒体配图 |
| oil_painting | 油画质感 | Oil Painting | brush strokes, rich texture, classical lighting, canvas texture | 艺术创作、高端品牌、文化主题 |
| watercolor | 水彩画 | Watercolor | soft color bleeding, paper texture, dreamy, flowing colors | 婚礼设计、文创产品、书籍插图 |
| pixel_art | 像素艺术 | Pixel Art | 16-bit retro game, limited palette, dithering, crisp pixels | 游戏素材、复古设计、社交媒体 |
| isometric | 等距视角 | Isometric | 2.5D perspective, miniature scene, clean vector style | 信息图、产品爆炸图、场景设计 |

### 仅视频风格

| 风格ID | 中文名 | 英文名 | 关键词摘要 | 运镜建议 | 适用场景 |
|--------|--------|--------|-----------|---------|---------|
| tech_promo | 科技宣传 | Tech Promotional | digital particles, data streams, holographic interface, blue-gold | slow orbit, push-in | 科技产品发布、品牌宣传片 |
| product_showcase | 产品展示 | Product Showcase | clean studio background, soft box lighting, product on pedestal | 360 rotation, macro close-up | 电商视频、产品开箱、广告 |
| nature_landscape | 自然风光 | Nature Landscape | golden hour, misty mountains, flowing water, time-lapse clouds | aerial drone, sweeping panorama | 旅游宣传、纪录片、环境素材 |
| urban_night | 城市夜景 | Urban Night | night skyline, light trails, neon reflections, traffic flow | slow tracking, time-lapse | 城市宣传、vlog片头、氛围视频 |
| abstract_art | 抽象艺术 | Abstract Art | fluid animation, color gradient morphing, particle system | slow zoom, rotation | 艺术展示、背景视频、MV特效 |
| portrait_dynamic | 人物动态 | Portrait Dynamic | portrait close-up, natural skin texture, hair movement, micro expressions | slow push-in, shallow DoF | 人物介绍、采访片头、品牌代言 |

---

## 二、视频运镜模板（12种）

| 运镜ID | 英文描述 | 适用场景 |
|--------|---------|---------|
| push_in | camera slowly pushes in, dolly forward, gradual zoom | 强调主体、建立聚焦 |
| pull_back | camera slowly pulls back, dolly backward, reveal wider scene | 揭示全景、场景转换 |
| orbit | camera orbits around the subject, arc shot, 360 rotation | 产品全貌展示、人物环绕 |
| pan_left | camera pans slowly from right to left | 风景展开、场景浏览 |
| pan_right | camera pans slowly from left to right | 风景展开、场景浏览 |
| crane_up | camera cranes up, rising, bird's eye reveal | 升镜头、宏大感 |
| crane_down | camera descends, lowering, ground level approach | 降镜头、切入细节 |
| aerial | aerial drone shot, sweeping flyover, bird's eye view | 航拍、大场景展示 |
| handheld | subtle handheld camera, natural slight shake | 纪实感、vlog风格 |
| static | static camera, fixed shot, no movement | 产品定格、稳定画面 |
| rotation | slow rotational pan, panoramic sweep | 全景环视、空间展示 |
| tracking | tracking shot following the subject, smooth gimbal | 跟随主体、运动场景 |

---

## 三、分辨率与版式对照

### 图像版式

| 版式 | 宽高比 | 推荐尺寸 | 推荐模型 | 像素范围 | 适用场景 |
|------|--------|---------|---------|---------|---------|
| 正方形 | 1:1 | 1024x1024 | 2.0/2.1 | 1,048,576 | 头像、社交媒体、商品图 |
| 横版 | 16:9 | 1920x1080 | 2.1 + ratio | 2,073,600 | 封面图、横幅、壁纸、PPT配图 |
| 竖版 | 9:16 | 1080x1920 | 2.1 + ratio | 2,073,600 | 手机壁纸、短视频封面、朋友圈海报 |
| 宽幅 | 21:9 | 2560x1080 | 2.1 + ratio | 2,764,800 | 电影感宽屏、网页头图 |
| 方版(大) | 4:3 | 1024x768 | 2.0/2.1 | 786,432 | 文档插图、演示配图 |
| 竖版(长) | 3:4 | 768x1024 | 2.0/2.1 | 786,432 | 海报、传单、杂志 |

> **注意**：16:9 / 9:16 / 21:9 等非1:1比例需使用 `agnes-image-2.1-flash` 模型并设置 `ratio` 参数。

### 视频版式

| 版式 | 推荐尺寸 | 像素总数 | 是否合规 | 适用场景 |
|------|---------|---------|---------|---------|
| 横版标准 | 1152x768 | 884,736 | 是 | 标准视频、宣传片段 |
| 竖版标准 | 768x1152 | 884,736 | 是 | 短视频平台、手机观看 |
| 正方形 | 1024x1024 | 1,048,576 | 是 | 社交媒体信息流 |
| 横版高清 | 1280x720 | 921,600 | 是 | 高清横版视频 |
| 竖版高清 | 720x1280 | 921,600 | 是 | 高清竖版视频 |
| 横版大 | 1920x1080 | 2,073,600 | 是(接近上限) | 全高清横版 |
| 竖版大 | 1080x1920 | 2,073,600 | 是(接近上限) | 全高清竖版 |

> **像素约束**：视频总像素范围 [3,686,400, 16,777,216]，宽高比范围 [1/16, 16]。

---

## 四、通用负面词库

### 基础负面词（所有场景通用）
```
blurry, distorted, deformed, disfigured, low quality, watermark, text artifacts,
extra limbs, bad anatomy, blurry background, flickering, jpeg artifacts,
overexposed, underexposed, washed out
```

### 风格专属负面词

| 风格 | 专属负面词 |
|------|-----------|
| cinematic | flat lighting, overexposed, washed out, low contrast |
| realistic | cartoon, anime, illustration, painting, 3D render, CGI |
| cyberpunk | daytime, bright sunlight, rural, nature, vintage |
| chinese_ink | colorful, neon, modern, industrial, 3D render |
| flat_illustration | realistic, 3D, gradient, shadow, texture, photograph |
| 3d_render | photograph, 2D, flat, sketch, painting |
| oil_painting | photograph, 3D, digital, flat, cartoon |
| minimalist | cluttered, busy, ornate, detailed, complex |
| anime_style | realistic, 3D, photograph, western cartoon |
| vintage_film | digital, sharp, modern, clean, bright |
| product_showcase | cluttered background, harsh shadows, low quality |
| nature_landscape | urban, city, buildings, artificial, CGI |
| portrait_dynamic | distorted face, deformed, blurry, low quality |

---

## 五、提示词构建公式

### 图像提示词公式

```
[主体描述] + [风格关键词] + [光影描述] + [构图视角] + [色调描述] + [质量增强词]
```

**示例**：
- 输入："城市夜景"
- 增强："Neon-lit city at night, rain-soaked streets reflecting colorful lights,
  cyberpunk style, neon magenta and cyan glow, wide-angle shot, volumetric fog,
  blade runner aesthetic, ultra-detailed, 8K"

### 视频提示词公式

```
[图像提示词] + [运镜描述] + [动态效果] + [氛围词]
```

**示例**：
- 输入："产品展示视频"
- 增强："Product on a clean studio pedestal, soft box lighting, floating particles
  around the product, premium feel, macro detail, 8K, 360 degree rotation, slow zoom-in,
  macro close-up, smooth gimbal movement, clean white background with accent colors"

### 长视频分镜公式

```
段1: [开篇] 主体 + 场景建立 + 大远景/航拍
段2: [展开] 切换角度 + 中景叙事
段3: [高潮] 特写/特效 + 视觉冲击
段4: [收尾] 品牌露出 + 情感升华 + 镜头放缓
```
