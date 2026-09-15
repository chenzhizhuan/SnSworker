---
name: godogen
description: >
  游戏开发技能：按文字描述自主开发游戏，支持 Godot 4(.NET/C#)、Bevy(Rust)、Babylon.js(TypeScript) 三款引擎；
  并支持生成游戏美术资产（PNG 图片、GLB 3D 模型、骨骼角色、重定向动画、逐帧动画精灵、抠图）。
  当用户提到“开发游戏”“做一个游戏”“game development”“Godot”“Bevy”“Babylon.js”“游戏资产生成”
  “生成3D模型”“GLB”“游戏精灵”“角色动画”“抠图”“游戏美术”“game asset”时触发。
name_cn: 游戏开发与资产生成
description_cn: Godot/Bevy/Babylon.js 三引擎自主游戏开发 + Gemini/Grok/Tripo3D 美术资产生成
create_source: external-godogen
---

# Godogen 游戏开发技能

按文字描述自主开发游戏：选择引擎 → 生成美术资产 → 构建项目 → 运行 → 截图/录像验证。
本技能整合自 Godogen 开源项目，并已适配 TeleAgent（Windows + PowerShell）运行环境。

## 本机环境现状（执行前必读）

- **GPU**：AMD Radeon RX 470（无 CUDA）→ rembg/推理使用 **CPU 版 onnxruntime**（已装）。切勿安装 `onnxruntime-gpu` / `nvidia-cudnn-cu12`。
- **Python**：3.12（TeleAgent 内置）。命令一律用 `python`，**不要用 `python3`**（本机 `python3` 指向 Windows Store 别名，会弹商店）。
- **已就绪工具**：`python`、`ffmpeg`。`magick`（ImageMagick）：未安装（本机无法访问 GitHub 下载源，winget 与直链均失败）；**不影响 skill 运行**，需图像裁剪/缩放/翻转时用 Python(Pillow) 替代。若需原生 magick，待网络恢复后 `winget install ImageMagick.Q16-HDRI`。
- **引擎运行环境**需用户自备，用到时再装：Godot（.NET/mono 版）+ dotnet 9 / Rust 工具链 / Node 22+。详见各 `engines/*.md`。
- **付费 API key**（资产生成必需，缺一则生成调用必失败，须先提醒用户配置环境变量）：
  - `GOOGLE_API_KEY` — Gemini 图像生成
  - `XAI_API_KEY` — xAI Grok 图像/视频生成
  - `TRIPO3D_API_KEY` — 图转 3D（GLB / 骨骼 / 动画重定向）
  - 配置方式（PowerShell，永久，需重开终端）：`setx GOOGLE_API_KEY "你的key"`，其余同理。

## 资产生成 — asset-gen

详细说明见 `asset-gen/SKILL.md`（占位符已渲染为本机绝对路径，命令已统一为 `python`）。工具位于 `asset-gen/tools/`。抠图规则见 `asset-gen/rembg.md`。

TeleAgent 调用模板（PowerShell 工具）：

```
python "C:/Users/meepo/.config/TeleAgent/skills/godogen/asset-gen/tools/asset_gen.py" image --prompt "a red sports car, 3/4 view, solid gray background" -o assets/img/car.png
```

子命令：`image` / `video` / `glb` / `rig` / `retarget` / `resume`。

执行要点：
- 生成是**付费**的，首次生成前须与用户确认花费（单价见 `asset-gen/SKILL.md` 的 Costs 段：Grok 图 2¢、Gemini 1K 图 7¢、GLB 30¢、rig +25¢、retarget 10¢、视频 5¢/s）。
- 每条命令输出 JSON 到 stdout：成功 `{"ok": true, "path": "...", "cost_cents": 7}`，失败 `{"ok": false, "error": "..."}` → 直接读 stdout 判断，无需重定向。
- 独立图像可并发生成（一条消息里发多个 powershell 工具调用）。
- **抠图铁律**（见 `asset-gen/rembg.md`）：不要 prompt “透明背景”（会画棋盘格），先用纯色背景再抠图；抠图后用 `--preview` 生成 `_qa.png` 核验，删除前必看。
- Tripo3D 任务常停在 99% 空输出，超时≠失败；侧车 `.tripo.json` 已存任务 id，用 `resume` 续跑，**切勿重新提交**（会重复扣费）。
- 本机 rembg 已装 CPU 版；`rembg.md` 里“auto-detects CUDA”在本机即恒走 CPU，正常现象。

## 引擎指南

按用户需求选一款，**动手前先 read 对应指南**（含栈、项目布局、运行方式、静默失败陷阱、录像配方）：

| 引擎 | 栈 | 指南 | 用户观看方式 | 录像注意（Windows） |
|------|----|------|------------|------------------|
| Godot 4 | .NET / C# | `engines/godot.md` | `godot --path .` 或编辑器 | 指南里 `xvfb-run`/`-pattern_type glob` 是 Linux 用法；Windows 直接窗口运行或用 movie writer |
| Bevy | Rust (edition 2024) | `engines/bevy.md` | `cargo run` | 离屏捕获二进制方案可用，软件 Vulkan 可接受 |
| Babylon.js | TS / Vite | `engines/babylon.md` | `npm run dev` → 浏览器固定端口 URL | 用 Playwright/Chromium 截图录像，注意等场景渲染完成再截 |

资产存放：Godot/Bevy 放项目 `assets/`；Babylon 放 `src/assets/`。

## 工作流程

1. **明确需求**：从用户描述提取游戏类型与要素，确认引擎选择（未指定时按 Godot=桌面3D/2D、Babylon=浏览器、Bevy=Rust 偏好建议）。
2. **建项目目录与 README**：在工作目录建项目，`README.md` 持续跟踪已建/待建内容与**资产表**。资产表必含“游戏内尺寸”列（3D 用米、纹理用瓦片米数、背景用像素+行为、精灵用显示像素），否则美术极易缩放错。
3. **首生成前确认花费**：向用户列出预计单价与总量，获确认后再调 asset-gen。
4. **生成资产**（并发），按上表路径存放；关键图先生成再转 GLB（坏图浪费 30¢+）。
5. **按引擎指南构建并运行**。
6. **从运行中的游戏核验**：截图/录像，以可见结果驱动下一轮迭代，而非只看能否编译通过。
7. **交付**：可让用户看实时运行（Babylon 给 URL，Godot/Bevy 让用户自行运行）；若用户未看过运行，则以 15–20s 游戏录像作证据，自己先回看再交付。

## TeleAgent 适配注意

原项目面向 Linux/macOS + Claude Code/Codex，本机为 Windows + TeleAgent，已做如下适配：

- 所有命令用 `python`（非 `python3`），通过 powershell 工具执行。
- 原 bash 日志重定向（`mktemp`/`2>"$_log"`/`tail`）已移除，改读 stdout JSON。
- 录像脚本里的 `xvfb-run`、`-pattern_type glob` 等 Linux 用法不适用，按各引擎指南的 Windows 替代法处理。
- 临时文件遵循 TeleAgent 约定放工作目录下 `.temp/`，最终交付物放工作目录根。
- 工具脚本 shebang `#!/usr/bin/env python3` 在 Windows 无影响（直接 `python xxx.py` 调用），保留不动。

## 参考文档

- `docs/demo_prompts.md` — 示例游戏提示词
- `docs/gdscript-vs-csharp.md` — GDScript / C# 对照（Godot 用 C#，避免混淆）

## 文件结构

```
SKILL.md                          本文件（TeleAgent 入口）
asset-gen/SKILL.md                资产生成详细说明（已渲染路径 + python 化）
asset-gen/rembg.md                抠图说明（已渲染路径 + python 化）
asset-gen/tools/                  Python 工具：asset_gen.py / rembg_matting.py / find_loop_frame.py / grid_slice.py / tripo3d.py
asset-gen/tools/requirements.txt  原项目依赖清单（仅供参考；含 onnxruntime-gpu/nvidia-cudnn，本机改用 CPU 版，且文件已被系统注入水印——勿直接 pip install -r）
engines/godot.md|bevy.md|babylon.md   引擎开发指南
docs/demo_prompts.md              示例提示词
docs/gdscript-vs-csharp.md        GDScript/C# 对照
LICENSE.md                        许可证
```
