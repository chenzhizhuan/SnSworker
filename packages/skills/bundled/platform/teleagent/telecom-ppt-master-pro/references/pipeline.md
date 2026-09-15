# Pipeline: 从规划到交付

## 运行条件

- Node.js 与 `pptxgenjs`：用于 JS 生成引擎
- Python 与 `python-pptx`：用于原生模板继承
- 宿主渲染能力：可选，用于输出逐页缩略图和视觉 QA

依赖安装和程序执行由宿主运行环境管理，技能目录不执行系统级安装或配置操作。

## 推荐项目结构

```text
my-deck/
├── figures/            图片素材
├── slide_contract.md   页面规划
├── gen_main.js         pages 模块生成脚本
├── output/             最终 PPTX
└── preview/            可选 QA 缩略图
```

## 工作流

1. 选择主题与场景预设。
2. 建立 Slide Contract；数据表较多时增加 Table Contract。
3. 按页面角色选择 T1-T34 模板，避免连续三页结构重复。
4. 生成 PPTX；复杂 JS 项目推荐接入 pages 模块预览。
5. 运行版面检查、内容检查和 deck 级 QA。
6. 按用户反馈微调并重新检查。

## Pages 模块

```js
const { run } = require("./progress-preview/runner");
const themes = require("./progress-preview/lib/themes");

const deckMeta = {
  title: "PPT 标题",
  author: "",
  theme: "telecom-red",
  slideMetas: [
    { title: "封面", template: "T1-Cover" },
    { title: "概览", template: "T7-3Card" },
  ],
};

const buildSlides = [
  (pres, ctx) => {
    const slide = pres.addSlide();
    slide.background = { color: ctx.C.bg };
  },
  (pres, ctx) => {
    const slide = pres.addSlide();
    slide.background = { color: ctx.C.bg };
  },
];

module.exports = {
  deckMeta,
  setup: pres => themes.setup(pres, deckMeta.theme),
  buildSlides,
};

if (require.main === module) {
  run({ pages: module.exports, outputPath: "output/deck.pptx" });
}
```

每个 `buildSlides[i]` 只操作传入的 `pres` 和 `ctx`，不依赖可变全局状态。这样既便于逐页检查，也便于失败后重建单页。

## 实时进度预览

`assets/progress-preview/` 提供本地进度界面：

- `runner.js` 在当前 Node 进程内启动本地服务并构建页面
- `reporter.js` 上报构建状态
- `server.js` 仅监听回环地址，使用随机会话令牌
- 缩略图只写入本次会话的系统临时目录
- 宿主提供 `renderSlide` 受控适配器时显示缩略图
- 未提供渲染器时自动降级为状态预览，不影响 PPTX 生成

安全实现及接入参数见 `assets/progress-preview/README.md`。

## Python 原生模板继承

使用 `电信5G原生模板1.0.pptx` 时：

1. 加载模板并选择 `2019-004` layout。
2. 由 layout 原生继承红色方块、5G logo 与红色横线。
3. 使用 `add_header_title` 补充页眉标题文字。
4. 正文布局限制在 y=1.15"~7.35" 的安全区域。
5. 由宿主受控渲染能力输出缩略图进行 QA；不可用时执行结构检查并在交付说明中标注。

## QA

逐页检查：

- 内容是否在安全区域内
- 是否存在文字裁剪、遮挡或溢出
- 主题色、字体和标题层级是否一致
- 表格与图表是否准确落位
- 模板页眉、5G logo 和分隔线是否完整
- 关键数字是否按主题规则高亮

Deck 级检查：

- 10页材料至少使用4种宏观版式
- 无连续3页相同结构
- 章节过渡清晰，结论页闭合论述
- 数据页有明确 takeaway，方法页有清晰信息流

## 电信主题注意事项

1. JS 引擎使用 `assets/telecom-boilerplate.js`。
2. 标准电信布局安全区为 y=0.55"~7.05"。
3. 使用 `addTelecomNav`、`addTelecomFooter` 和 `fmtNumber`。
4. 版式选择遵循 `content-patterns.md`，文字遵循 `writing-style.md`。
5. 原生模板模式不添加标准页脚，正文从页眉红线下开始。
