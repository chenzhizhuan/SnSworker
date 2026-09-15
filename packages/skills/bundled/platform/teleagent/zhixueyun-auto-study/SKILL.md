---
name: zhixueyun-auto-study
description: >
  Automate course learning on zhixueyun.com (China Telecom Online University).
  Supports two modes: GUI mode (interactive ttkbootstrap desktop app) and CLI mode (headless command-line).
  Use when user mentions "电信网上大学", "知学云", "自动学习", "刷课", "培训班学习", "网大",
  or needs to automate video playback, document scrolling, course progress on zhixueyun.com platform.
name_cn: 电信网上大学自动学习
description_cn: 自动化知学云网大课程学习，支持GUI图形界面和CLI命令行双模式，自动播放视频、滚动文档、跳过考试
create_source: super-agent-skill-creator
---

# 电信网上大学自动学习

基于 Playwright 浏览器自动化，在知学云平台自动完成课程学习。支持 **GUI 模式** 和 **CLI 模式**，使用时由用户选择。

## 前置条件

- Python 3.8+，已安装 `playwright`（`pip install playwright && playwright install chromium`）
- 系统已安装 Chrome 或 Edge 浏览器
- GUI 模式额外需要 `ttkbootstrap`（`pip install ttkbootstrap`）
- 用户有知学云平台账号

## 模式选择

向用户确认运行模式：

- **GUI 模式**：启动桌面图形界面，交互式配置URL、倍速、浏览器等参数，适合日常手动使用
- **CLI 模式**：命令行直接运行，支持多URL、无头模式、无限循环，适合定时任务/批量刷课

## GUI 模式

```bash
python -B scripts/zhixueyun_auto_study.py --mode gui
```

或直接运行（默认 gui 模式）：

```bash
python -B scripts/zhixueyun_auto_study.py
```

功能：多URL列表管理（添加/编辑/删除/排序/撤销重做）、浏览器自动检测、视频倍速、无头模式、无限循环、实时日志和进度条。

## CLI 模式

```bash
python -B scripts/zhixueyun_auto_study.py --mode cli --url "<URL>" [选项]
```

**必须参数：**
- `--url`：目标页面URL（可多次指定处理多个URL）

**可选参数：**
- `--speed`：视频播放倍速（默认 1.5）
- `--headless`：无头模式，不显示浏览器
- `--max-rounds`：每个URL最大扫描轮数（默认 10）
- `--browser`：浏览器类型 chrome/msedge（默认 chrome）
- `--browser-path`：浏览器可执行文件路径（留空自动检测）
- `--user-data-dir`：浏览器用户数据目录（默认 ./网大浏览器数据）
- `--infinite`：无限循环模式

**示例：**

```bash
# 单URL自动学习
python -B scripts/zhixueyun_auto_study.py --mode cli --url "https://kc.zhixueyun.com/#/branch-list-v/xxxx"

# 多URL + 倍速
python -B scripts/zhixueyun_auto_study.py --mode cli --url "URL1" --url "URL2" --speed 1.5

# 无头 + 无限循环（适合定时任务）
python -B scripts/zhixueyun_auto_study.py --mode cli --url "URL" --headless --infinite
```

## 工作流程

1. **启动浏览器** — 使用 Playwright 启动 Chrome/Edge，保持登录状态
2. **等待登录** — 若未登录，等待用户手动登录（超时5分钟）
3. **发现课程** — 根据 URL 类型自动选择模式：
   - 专题列表页（branch-list-v）：遍历轮播图专题 → 进入每个专题 → 通过 iframe 获取课程列表
   - 单课程页（subject/detail）：展开章节 → 获取待学课程
4. **逐课学习** — 视频自动播放（可调倍速），文档模拟滚动阅读，自动跳过考试/测试
5. **弹窗处理** — 自动关闭评价弹窗、点赞弹窗、"我知道了"提示
6. **循环控制** — 支持多轮扫描、多URL切换、无限循环

## 核心能力

- 自动跳过考试/测试类课程（关键词：考试、测试、测验、quiz、exam、test）
- 支持专题列表页（swiper 轮播图 + iframe 嵌套）和单课程详情页两种页面结构
- 视频倍速播放 + 自动播放恢复（防暂停）
- PDF/文档模拟滚动阅读
- 自动处理评价弹窗和提示弹窗
- 多URL顺序处理，URL间自动切换
- 翻页支持（Ant Design / Element UI 分页组件）

## 注意事项

- 首次登录需手动扫码，之后使用持久化浏览器数据保持登录状态
- 无头模式下无法手动登录，需先用 GUI 模式登录一次
- 知学云平台更新可能导致 DOM 选择器失效，需相应调整脚本
- 考试类课程无法自动完成，会自动跳过并在日志中标记
