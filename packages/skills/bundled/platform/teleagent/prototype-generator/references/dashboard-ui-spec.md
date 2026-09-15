---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '6e44af6a-9780-4c7a-a3da-4257c6e40550'
  PropagateID: '6e44af6a-9780-4c7a-a3da-4257c6e40550'
  ReservedCode1: '5567e190-c891-4c53-b7dd-8847f0cb56ab'
  ReservedCode2: '5567e190-c891-4c53-b7dd-8847f0cb56ab'
---

# 大屏展示 UI规格

单HTML文件，深色科技风，可加载ECharts CDN。

## 页面结构 (2行3列Grid)

```
┌────────────────────────────────────────────────┐
│  Header: 系统名称                2026-01-15 周三 │
├────────────┬──────────────┬────────────────────┤
│            │              │                    │
│  模块1     │  模块2       │  模块3              │
│  (饼图)    │  (柱状图)    │  (柱状图)           │
│            │              │                    │
├────────────┼──────────────┼────────────────────┤
│            │              │                    │
│  模块4     │  模块5       │  模块6              │
│  (柱状图)  │  (地图)      │  (地图)             │
│            │              │                    │
└────────────┴──────────────┴────────────────────┘
```

## 配色

| 元素 | 色值 |
| 页面背景 | #0a1929 |
| 标题背景 | 透明 |
| 标题文字 | #ffffff, 16px bold |
| 模块背景 | rgba(6, 30, 65, 0.8), 圆角4px |
| 模块边框 | 1px solid rgba(32, 160, 255, 0.2) |
| 模块标题 | #00d4ff, 14px, 底部2px渐变线(#00d4ff → transparent) |
| 主文字 | #ffffff |
| 次要文字 | #8899aa |
| 强调色-蓝 | #00d4ff |
| 强调色-绿 | #00ff88 |
| 强调色-红 | #ff6b6b |
| 强调色-橙 | #ffaa00 |
| 强调色-紫 | #b37feb |

## Grid布局

- 外层: padding 12px, gap 12px
- Grid: grid-template-rows: 1fr 1fr, grid-template-columns: 1fr 1.2fr 1fr
- 中间列略宽（适合地图/大图表）
- 每个模块: overflow hidden, position relative

## Header

- 高度: 50px
- 左侧: 系统名称, 20px bold, 文字发光效果(text-shadow)
- 右侧: 当前日期时间, 12px, #8899aa
- 背景: 渐变 linear-gradient(90deg, transparent, rgba(0,212,255,0.1), transparent)
- 底部: 2px渐变线

## 图表通用规则

- ECharts从CDN加载: `https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js`
- 图表容器: div指定固定id, 100%宽高
- 背景透明, 网格线: rgba(255,255,255,0.06)
- 坐标轴文字: #8899aa, 11px
- 图例文字: #8899aa
- tooltip: 暗色背景(#1a2332), 白色文字, 圆角4px
- 数据更新: 页面加载时用setTimeout模拟动画入场

## 数字翻牌器 (KPI展示)

- 大号数字: 32px bold, #00d4ff
- 单位: 14px, #8899aa
- 左侧标签: 12px, #8899aa
- 布局: 左上角标签, 右下角数字+单位

## 地图模块

- 中国地图: ECharts geo组件
- 地图底色: #0e2740
- 区域边界: rgba(32,160,255,0.3)
- 标注点: 散点图, 大小反映数值
- 点击事件: 弹出半透明弹窗

## 弹窗

- 背景: rgba(0,0,0,0.6)遮罩
- 弹窗: #1a2332背景, 圆角8px, 宽400px
- 标题: #00d4ff, 左侧装饰条
- 表格: 暗色行条纹, #2a3a4a/#1a2332交替
- 关闭: 右上角 × 按钮, #8899aa

## 动画效果

- 模块入场: fadeIn + translateY(20px → 0), 依次延迟100ms
- 数字: 从0递增到目标值
- 图表: ECharts自带入场动画
- 顶部线条: 从左到右流光效果 (CSS animation)

> AI生成