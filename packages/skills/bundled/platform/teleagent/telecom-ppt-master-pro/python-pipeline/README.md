---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '2ef8bc1b-cdf7-4fa1-8e71-667d928767ec'
  PropagateID: '2ef8bc1b-cdf7-4fa1-8e71-667d928767ec'
  ReservedCode1: 'c32a1a10-32ad-498e-86b7-a727d090f059'
  ReservedCode2: 'c32a1a10-32ad-498e-86b7-a727d090f059'
---

# Python SVG 管道 — 辅引擎集成

本目录是 ppt-master (hugohe3, GitHub 39.8k stars) Python SVG 管道的集成层。当电信场景需要原生PPT深度能力（过渡动画、音频旁白、Swiss Grid高设计感排版、非标准画布）时，可切换到本管道。

## 前置条件

```bash
# 1. 确认 Python 3.10+ 已安装
python --version

# 2. 安装依赖（从源码目录）
cd <telecom-ppt-master>/python-pipeline/source
pip install -r skills/ppt-master/requirements.txt

# 3. 图像能力（可选）
# 由宿主环境提供受控的图像生成或检索能力；技能目录不保存认证信息。
```

## 源码位置

完整 `ppt-master` 源码位于：
```
<工作空间>\.temp\ppt-master-source\
```

核心脚本路径（相对于源码根目录）：
```
skills/ppt-master/scripts/
├── project_manager.py     # 项目初始化、素材导入
├── source_to_md.py        # 源文件→Markdown转换
├── image_gen.py           # AI图像生成（由宿主受控能力提供）
├── image_search.py        # 网页图像搜索
├── svg_quality_checker.py # SVG质量检查
├── finalize_svg.py        # SVG后处理
├── svg_to_pptx.py          # SVG→PPTX编译
├── native_enhance_pptx.py  # 原生PPTX增强（动画/旁白）
└── ...
```

## 使用方式

在技能工作流中，当用户需求匹配以下条件时，切换到Python管道：

### 触发条件

| 用户需求 | 推荐引擎 | 理由 |
|---------|---------|------|
| 电信业务报告/运营分析/宣贯 | **JS (pptxgenjs)** | 快速、内容组织强 |
| 总经理座谈会/半年会封面设计 | **Python (SVG)** | 高设计感、原生深度 |
| 需要幻灯片切换动画/元素入场动画 | **Python (SVG)** | JS引擎动画能力弱 |
| 需要演讲者备注→语音旁白 | **Python (SVG)** | JS引擎不支持 |
| 非16:9画布（小红书/朋友圈/海报） | **Python (SVG)** | 支持8种画布格式 |
| 数据驱动的表格/图表密集型 | **JS (pptxgenjs)** | 数据智能层成熟 |
| 已有.pptx模板填充内容 | **Python (SVG)** | 原生模板填充工作流 |

### 调用方式

在技能工作流中，通过宿主提供的 Python 运行环境调用脚本：

```text
# 项目初始化
python .temp/ppt-master-source/skills/ppt-master/scripts/project_manager.py init <project_name> --format ppt169

# 源文件导入
python .temp/ppt-master-source/skills/ppt-master/scripts/project_manager.py import-sources <project_path> <source_files...> --move

# 脚手架
python .temp/ppt-master-source/skills/ppt-master/scripts/project_manager.py scaffold-spec <project_path>
python .temp/ppt-master-source/skills/ppt-master/scripts/project_manager.py scaffold-lock <project_path>

# 最终导出
python .temp/ppt-master-source/skills/ppt-master/scripts/finalize_svg.py <project_path>
python .temp/ppt-master-source/skills/ppt-master/scripts/svg_to_pptx.py <project_path>
```

### 管线概览

```
源文件 → source_to_md.py → project_manager init → scaffold → 
  Strategist规划 → Image获取 → Executor逐页SVG生成 → 
  svg_quality_checker → finalize_svg → svg_to_pptx → exports/*.pptx
```

详细工作流参见 `ppt-master-source/skills/ppt-master/workflows/generate-pptx.md`

## 能力边界

| 能力 | Python管道 | JS管道 |
|------|-----------|--------|
| 生成速度（10页） | 10-20分钟 | 1-3分钟 |
| 原生PPT形状（可调手柄） | 支持（187种预设） | 基础形状 |
| 幻灯片母版/版式继承 | 完全支持 | 有限支持 |
| 过渡动画 | 支持 | 极弱 |
| 音频旁白 | 支持 | 不支持 |
| AI生图管道 | 支持（由宿主能力提供） | 无 |
| Web搜图 | 支持 | 无 |
| 非标准画布 | 8种格式 | 仅16:9 |
| 已有PPTX模板填充 | 支持 | 不支持 |
| 数据表格/图表 | 支持（原生Chart） | 支持（pptxgenjs图表） |
| 内容组织模式 | 无明确系统 | 19+6种模式 |
| 场景预设 | 无 | 12种 |
| 自进化/风格记忆 | 无 | 四文件三级记忆 |

## 注意事项

1. Python管道生成速度慢5-10倍，仅用于高端场景
2. 需要安装Python依赖（`pip install -r requirements.txt`）
3. AI生图/搜图由宿主环境提供，技能目录不包含或保存认证信息
4. Windows下参考 `ppt-master-source/docs/windows-installation.md`
5. 详细文档见 `ppt-master-source/` 下的各reference文件
