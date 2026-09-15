---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: 'fceaa606-c602-4d92-98bb-3a4d5ce57800'
  PropagateID: 'fceaa606-c602-4d92-98bb-3a4d5ce57800'
  ReservedCode1: '92006c4f-7581-42a9-9f5f-f6d550864ffb'
  ReservedCode2: '92006c4f-7581-42a9-9f5f-f6d550864ffb'
---

# 移动端APP UI规格

单HTML文件中内嵌CSS/JS，模拟手机屏幕。

## 页面结构

```
┌─────────────────────┐
│  Status Bar (模拟)   │ 44px
├─────────────────────┤
│  Nav Bar    [←] 标题 │ 44px
├─────────────────────┤
│                     │
│  Content Area       │
│  (scrollable)       │
│                     │
│                     │
├─────────────────────┤
│  Tab1 | Tab2 | Tab3 │ 50px
└─────────────────────┘
```

## 设备模拟

- 外层容器: 居中显示, 带手机外框阴影
- 视口宽度: 375px
- 视口高度: 812px (iPhone X比例)
- 背景色: 外层#f0f2f5, 屏幕内#ffffff
- 圆角: 外框40px

## 配色

| 元素 | 色值 |
| 导航栏背景 | #FFFFFF + 底部1px阴影 |
| 导航栏文字 | #333333, 17px |
| TabBar背景 | #FFFFFF + 顶部1px阴影 |
| TabBar激活 | #1677FF (蓝色图标+文字) |
| TabBar未激活 | #999999 |
| 页面背景 | #F5F5F5 |
| 卡片背景 | #FFFFFF, 圆角8px, 下方阴影 |
| 主文字 | #333333, 15px |
| 次要文字 | #999999, 13px |
| 按钮 | #1677FF 背景, 白色文字, 圆角8px, 高度44px |

## 导航栏

- 高度: 44px
- 返回箭头: ← 或 ‹ 黑色, 左侧16px
- 标题: 居中, 17px bold
- 右侧操作: 文字按钮, #1677FF

## TabBar

- 高度: 50px (含安全区域模拟)
- Tab数量: 3-5个
- 图标: 使用unicode/emoji, 24px
- 文字: 10px
- 选中态: 蓝色图标 + 蓝色文字
- 未选中: 灰色图标 + 灰色文字

## 列表卡片

- 背景: 白色, margin 12px, padding 16px, 圆角8px
- 卡片间距: 12px
- 标题: 16px bold, 单行溢出省略
- 描述: 13px gray, 2行溢出省略
- 底部信息: 12px gray + 右侧操作按钮

## 表单

- 标签: 14px #333, 宽度80px
- 输入框: 16px, 底部1px边框, 无外框
- 选择器: 右侧箭头 ›, 点击弹出模拟picker
- 开关: iOS风格 toggle
- 按钮: 全宽蓝色, 底部固定或页面底部

## 对话框

- 底部弹出式 (ActionSheet风格)
- 圆角顶部12px
- 半透明遮罩 #000000 50%
- 取消按钮: 独立于底部

## 角色切换器

- 导航栏右侧, ⚙️图标
- 点击弹出底部ActionSheet选择角色

> AI生成