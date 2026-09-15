---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: 'c5f8cba3-44c5-4bd3-9d07-578d0a10910d'
  PropagateID: 'c5f8cba3-44c5-4bd3-9d07-578d0a10910d'
  ReservedCode1: '894a2bde-a25f-40b3-9df9-b8b7cc2db410'
  ReservedCode2: '894a2bde-a25f-40b3-9df9-b8b7cc2db410'
---

# PPT 生成进度预览 · 电信PPT大师 实时预览工具

一个本地 Web 工具，让 PPT 生成过程"开一个浏览器实时可见"：
- **进度状态可视化**：毫秒级跟随，看到每一页从待生成→构建中→已构建→渲染中→已渲染
- **真实页面缩略图**：每页生成后异步用 PowerPoint COM 渲染成 PNG，在浏览器里逐页"长出来"
- **事件日志区**：所有阶段事件滚动展示，方便排错
- **电信红主题界面**：与中国电信运营材料视觉统一

## 架构

```
┌─────────────────────┐         ┌──────────────────────┐
│   gen_main.js        │  fork   │  render-single.js     │
│   (主进程)            │ ──────► │  (单页渲染子进程)       │
│   - 串行构建各页      │         │  - 构造独立 pres        │
│   - 每页构建完         │         │  - 执行 buildSlides[i] │
│     → 上报进度         │         │  - writeFile 临时 pptx  │
│     → 入队异步渲染     │         │  - 调 render-worker.ps1 │
│                       │         │     PowerPoint COM→PNG │
│   - 全部构建完         │         │  - process.send 结果   │
│     → writeFile 主 pptx│         └──────────────────────┘
│   - 等待渲染队列空      │                   │
│   - 上报 deck_done     │                   │ PNG 写到
└──────────┬────────────┘                   │ .ppt-preview-cache/thumbs/
           │ HTTP POST /api/progress         │
           ▼                                  ▼
┌──────────────────────────────────────────────────────┐
│                  server.js (HTTP + SSE)              │
│  - /api/progress 接收事件 → 更新 state                 │
│  - /api/events  SSE 长连接 → 推送给浏览器              │
│  - /cache/* 静态服务缩略图                             │
│  - / 静态服务前端 index.html                          │
└──────────────────────┬───────────────────────────────┘
                       │ SSE 事件流
                       ▼
┌──────────────────────────────────────────────────────┐
│                  浏览器 (telecom-red UI)              │
│  - 顶部条 deck 标题 + 主题 + 总页数 + 用时              │
│  - 进度条 + 统计 (已构建/已渲染/失败)                   │
│  - 卡片网格：每页一个卡片，徽章+缩略图                  │
│  - 底部事件日志（可折叠）                              │
└──────────────────────────────────────────────────────┘
```

## 文件清单

```
progress-preview/
├── server.js            # 本地 Web 服务器（HTTP + SSE + 静态服务）
├── reporter.js          # 进度上报器（生成脚本调用的 HTTP 客户端）
├── runner.js            # 一站式入口：启动 server + 构建 + 调度渲染
├── render-single.js     # 单页渲染子进程（fork 启动，构造单页 pres + 调 PS）
├── render-worker.ps1    # PowerShell：用 PowerPoint COM 把 .pptx 单页导出 PNG
├── gen_demo.js          # 示例生成脚本（5 页电信红 deck）
├── lib/
│   └── themes.js        # telecom-red 主题 + 一组 helper（addTelecomNav 等）
├── public/
│   ├── index.html       # 前端骨架
│   ├── style.css        # 电信红主题样式
│   └── app.js           # SSE 客户端 + DOM 更新
└── README.md
```

## 快速开始

```powershell
$env:NODE_PATH = (npm root -g)     # 让 pptxgenjs 可被 require
cd assets\progress-preview
node gen_demo.js
```

首次执行会：
1. 检测 server 是否在跑，没跑就后台拉起一个（默认端口 51720）
2. 自动打开系统默认浏览器到 `http://127.0.0.1:51720/`
3. 串行构建 5 页 → 每页构建完入队异步渲染 → 浏览器实时收到事件
4. 全部渲染完成 → 主 pptx 保存到 `gen_demo.js` 同目录 → 浏览器显示"已完成"

## 集成自己的生成脚本

把传统的"块状"脚本改造成 **pages 模块** 结构即可接入：

```js
// gen_main.js
const { run } = require("./runner");
const { setup } = require("./lib/themes");

const NAV = ["章节1", "章节2"];

const deckMeta = {
  title:  "你的 PPT 标题",
  author: "作者/单位",
  theme:  "telecom-red",            // 目前内置 telecom-red
  totalPages: 3,
  slideMetas: [                     // 可选：每页的标题/模板名（用于卡片显示）
    { title: "封面",     template: "T1-Cover" },
    { title: "概览",     template: "T7-3Card" },
    { title: "总结",     template: "T16-Summary" },
  ],
};

function setup(pres) {
  pres.title = deckMeta.title;
  pres.author = deckMeta.author;
  return require("./lib/themes").setup(pres, "telecom-red");
}

const buildSlides = [
  // 每个 buildSlides[i](pres, ctx) 必须能独立调用：只往传入的 pres 加一页
  (pres, ctx) => {
    const { C, F, W, H, addTelecomNav, addTelecomFooter, addTitle } = ctx;
    const s = pres.addSlide();
    s.background = { color: C.bg };
    addTelecomNav(s, 0, NAV);
    addTitle(s, "这一页标题", "副标题");
    addTelecomFooter(s, 1, deckMeta.totalPages);
    // ... 你的元素
  },
  // ... 第 2、3 页
];

module.exports = { deckMeta, setup, buildSlides };

// 用 require.main 守卫，避免被 render-single.js require 时递归调 run()
if (require.main === module) {
  run({ pages: module.exports, outputPath: "我的PPT.pptx" })
    .then(r => { console.log("DONE:", r); setTimeout(() => process.exit(0), 1500); })
    .catch(e => { console.error(e); process.exit(1); });
}
```

**关键三件事**：

1. **`module.exports = { deckMeta, setup, buildSlides }`** — 必须导出这三个，runner 通过 require 拿到它们，render-single.js 也是
2. **`if (require.main === module) run(...)`** — 必须守卫，否则渲染子进程会无限递归
3. **每个 `buildSlides[i](pres, ctx)` 独立** — 不要让单页依赖闭包里的 mutable 状态（如全局 NAV_ACTIVE），每个函数自己控制自己的状态

## 三种启动方式

| 方式 | 命令 | 适用 |
|------|------|------|
| **一站式**（推荐） | `node gen_main.js` | 跑生成脚本时自动拉起 server + 开浏览器 |
| **分离式** | `node server.js` 后台跑 → `node gen_main.js` | 想固定开一个仪表盘窗口、多次跑生成 |
| **纯浏览** | `node server.js --no-browser` → 自己用浏览器访问 | 远程或 CI 场景 |

server 命令行参数：
- `--port 51800` 指定端口（默认 51720）
- `--no-browser` 不自动开浏览器

## 性能参考

| 阶段 | 耗时 |
|------|------|
| 5 页主 deck 构建 | < 500 ms |
| 主 pptx `writeFile` | 300–800 ms |
| **单页 PowerPoint COM 导 PNG** | **3–8 秒/页** ← 主要瓶颈 |
| SSE 事件推送延迟 | < 100 ms |

> PowerPoint COM 是慢的主要来源：每次渲染都要启动一个 PowerPoint 实例、打开、Export、关闭。
> 已用串行队列（SerialQueue）保证不并发，避免 PowerPoint 进程互相打架。
> 5 页 deck 全程约 25–40 秒，与原本生成 +QA 转图的总时间持平，但全程可视化。

## 已知限制

1. **PowerPoint 必须安装**：渲染缩略图依赖 PowerPoint COM。没装的话，进度仍能上报但缩略图会失败（卡片标记"渲染失败"，不影响主 pptx 生成）
2. **窗口会闪现**：`Presentations.Open(WithWindow=false)` 在某些 Office 版本仍会瞬间弹窗，渲染时会看到 PowerPoint 一闪而过
3. **cache 路径**：缩略图默认写到 `技能根目录/.ppt-preview-cache/thumbs/`，由 server 在启动时一次性锁定，**运行期间不可被客户端改写**（安全加固：修复了旧版 `/api/config` 可把缓存目录指向任意系统目录、进而被 `/cache/*` 无鉴权读取的越权目录穿越漏洞）；可手动删，下次运行重建
4. **单 deck 会话**：当前 server 同时只服务一个生成会话；新 `start` 事件会覆盖旧状态
5. **不支持模板锚定**：本工具是"从零生成 + 预览"模式，不支持载入现成 .pptx 模板作为骨架——如需模板，用 `assets/template-analyzer.py` 解剖后填进 pages 模块

## 排错

| 现象 | 排查 |
|------|------|
| 浏览器打不开 | 检查 51720 端口是否被占用，或用 `--port` 换端口 |
| 卡片全显示"渲染失败" | 单独跑 `render-worker.ps1` 看错误：`powershell -File render-worker.ps1 -PptxPath xxx.pptx -OutPath xxx.png -PageIdx 1` |
| 缩略图不显示但状态已渲染 | 刷新浏览器（SSE 重连后会重新拿 snapshot + /cache/ 路径会带时间戳防缓存） |
| 主进程提前退出但渲染没完成 | 检查 `runner.js` 的 `SerialQueue.push(...)` 传的是否是"返回 Promise 的函数"而不是立即执行的 Promise |
| 中文乱码（命令行输出） | 用 `chcp 65001` 切 UTF-8，或忽略——文件路径在 Node 内部处理正确，仅显示乱码 |