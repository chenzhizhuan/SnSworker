---
name: fairyland-hero
description: Use when launching or developing 仙境Hero / Fairyland Hero. This skill package already contains the game code; only img/music/video media is downloaded from Gitee on first play.
AIGC:
  ContentProducer: 001191110102MAD55U9H0F10002
  ContentPropagator: 001191110102MAD55U9H0F10002
  Label: '1'
  ProduceID: 86c8bdbd-c16d-406a-95c1-3a8f65df9673
  PropagateID: 86c8bdbd-c16d-406a-95c1-3a8f65df9673
  ReservedCode1: 90fa55d6-280e-44c9-9e86-b2b5ebd5fdec
  ReservedCode2: 90fa55d6-280e-44c9-9e86-b2b5ebd5fdec
description_cn: DQ风格RPG「仙境英雄传」。是由CheLia参照仙境传说开发出的一款回合制角色扮演类RPG页游，主要玩法是通过对人物属性加点的理解与搭配提升人物的属性，以及小队选人随机组合最终击败BOSS完成冒险。游戏主要讲了一个妖怪横行的异世界，主角一路追寻自己姐姐的故事，游戏通过随机探索完成剧情遇怪增益和boss战。目前推出前4章供大家试玩，如有好的意见和BUG反馈请邮件：610820767@qq.com
---
# 仙境Hero

DQ 风格长篇文字 RPG。本 skill **已经带上游戏代码**。Gitee 只用来补 `img/`、`music/`、`video/` 里的立绘、BGM 和短视频，不要把整仓代码再 clone 一遍当工程。

仓库（仅媒体）：https://gitee.com/jerry_mus/fairyland-hero

## 包内有什么

本目录就是可运行工程（`SKILL.md` 与代码在同一层）：

| 文件 | 职责 |
|------|------|
| `frontend.py` | Streamlit 界面 |
| `backend.py` | Flask：音乐/立绘/视频、PVP |
| `dq_rpg.py` | 游戏引擎 |
| `asset_bootstrap.py` | 检查并下载 **仅** img/music/video |
| `asset_manifest.json` | 媒体文件清单 |
| `config.py` / `requirements.txt` | 端口与依赖 |
| `img/` `music/` `video/` | **空文件夹**，首次进游戏再下内容 |
| `games/` | 本地存档目录（不要提交 `dq_saves.csv`） |

**不要打进包、也不要从 Gitee 当“代码”再下一遍：** `.venv`、存档 CSV、`.jpg` / `.mp3` / `.mp4`。

## 启动

在 **本 skill 解压后的根目录**（有 `SKILL.md` 和 `frontend.py` 的那一层）执行：

```bash
python backend.py
streamlit run frontend.py --server.port 8503 --server.headless true
```

**注意：依赖（flask、streamlit 等）只需安装一次，不要每次启动都跑 `pip install`。**
仅在首次使用或报 `ModuleNotFoundError` 时才执行：`python -m pip install -r requirements.txt`。

若已有项目 `.venv` 也可：`source .venv/bin/activate` 后再跑上面两条。

浏览器：http://localhost:8503

缺媒体时会出现下载页：开始下载 / 跳过下载。只下载 img、music、video，代码用包里这份。

## 智能体注意

- **不要每次启动都执行 `pip install`**——依赖已预装，重复安装会弹窗且浪费时间。
- 以本包为工作区，不要再 `git clone` 整个仓库来覆盖代码。
- 资源不齐时打开前端，让玩家在下载页选择；不要替玩家点跳过。
- 不要把媒体文件写进 skill 再导出。

## 必须遵守的坑

- Streamlit 同一 run 只能开一个 dialog。
- 主角/队友同时加点：确认后不要立刻 `st.rerun()`，用 `dq_stat_keep_*` 保留其他人草稿。
- MP 不足或冷却导致 `turn_done=False` 时不要播战斗视频。
- `_main_story_scene` 按 `sid` 分流，Q1 不要回落到 Q5。
- 回复用简体中文。不要主动 commit/push，不要提交 `.venv` 和 `games/dq_saves.csv`。