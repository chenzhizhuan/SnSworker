---
name: ths-ifind
display_name: 同花顺iFinD金融数据
title: 同花顺iFinD金融数据查询 skill
description: 同花顺iFinD金融数据查询，查询股票、基金、宏观经济、行业经济、新闻公告、债券、港美股及指数板块数据；其中A股、基金、债券、指数支持日内高频/实时行情数据，同时支持智能选股、选基、宏观行业经济指标搜索、金融公告资讯搜索等服务。
homepage: https://www.10jqka.com.cn/
author: TeleAgent
version: 1.0.0
required_env_vars:
  - THS_COOKIE
credentials:
  - type: cookie
    name: THS_COOKIE
    description: 同花顺问财网页端 Cookie，从浏览器请求头中复制 Cookie 字段值
---

# ths-ifind 同花顺iFinD金融数据查询 skill

同花顺iFinD金融数据查询，查询**股票、基金、宏观经济、行业经济、新闻公告、债券、港美股及指数板块**数据；其中**A股、基金、债券、指数支持日内高频/实时行情数据**，同时支持**智能选股、选基、宏观行业经济指标搜索、金融公告资讯搜索**等服务。

## 功能说明

基于 `pywencai` 开源库（封装同花顺问财接口），通过自然语言查询句获取结构化金融数据。核心调用入口为 `pywencai.get()`，返回 `pandas.DataFrame`（列表查询）或 `dict`（详情查询）。

### 支持的数据类型（query_type）

| query_type | 含义 | 说明 |
|------------|------|------|
| `stock` | 股票 | A股个股行情、财务指标、资金流向、概念板块（默认） |
| `zhishu` | 指数 | 沪深300、上证50、中证500等指数数据 |
| `fund` | 基金 | 公募基金净值、持仓、评级、选基筛选 |
| `hkstock` | 港股 | 港股个股行情、财务数据 |
| `usstock` | 美股 | 美股个股行情、财务数据 |
| `conbond` | 可转债 | 可转债行情、溢价率、条款 |
| `insurance` | 保险 | 保险产品信息 |
| `futures` | 期货 | 期货行情、持仓 |
| `lccp` | 理财 | 银行理财产品 |
| `foreign_exchange` | 外汇 | 汇率数据 |

### 实时/高频行情查询

通过 query 中包含实时关键词（如"最新价"、"今日涨跌幅"、"实时行情"），可获取日内实时行情数据。支持的实时数据类型：
- A股实时行情（最新价、涨跌幅、成交量、换手率等）
- 基金实时净值估算
- 债券实时报价
- 指数实时点位

## 配置

### 环境依赖

- **Python 3.8+**
- **Node.js v16+**（pywencai 依赖 Node.js 执行 JS 加密脚本生成 hexin-v token）
- **pywencai** 库：`pip install pywencai`
- **pandas** 库：数据结构依赖

### Cookie 配置

由于问财接口策略调整，必须配置 Cookie 才能使用：

1. 浏览器打开 https://www.10jqka.com.cn/ 并登录同花顺账号
2. 按 F12 打开开发者工具 → Network 面板
3. 刷新页面，找到任意请求，复制请求头中的 `Cookie` 字段完整值
4. 将 Cookie 设置到环境变量 `THS_COOKIE`：
   ```powershell
   $env:THS_COOKIE = "你的cookie值"
   ```
   或在脚本调用时通过 `--cookie` 参数传入

### 输出目录

- 默认输出目录：脚本同级目录下 `output/`
- 输出文件名前缀：`ths_ifind_`
- 输出文件：
  - `ths_ifind_{query}.csv` - 查询结果 CSV（UTF-8 BOM 编码，Excel 直接可读）
  - `ths_ifind_{query}_description.txt` - 查询条件和结果统计描述
  - `ths_ifind_{query}_raw.json` - 原始 JSON 数据（字典类结果）

## 使用方式

### 命令行调用

```bash
# ==================== A股个股查询 ====================
# 查询个股实时行情
python ths_ifind.py "贵州茅台最新价"
python ths_ifind.py "000001平安银行今日 realtime"

# 查询个股财务指标
python ths_ifind.py "贵州茅台市盈率市净率净资产收益率"
python ths_ifind.py "600519近五年营业收入净利润"

# ==================== 智能选股 ====================
python ths_ifind.py "今日涨幅大于2%的A股"
python ths_ifind.py "市盈率小于20并且市净率小于2"
python ths_ifind.py "ROE大于15%，净利润连续三年增长"
python ths_ifind.py "股价在10元到20元之间，换手率大于5%"

# ==================== 基金查询（选基） ====================
python ths_ifind.py --query-type fund "近一年收益率大于20%的股票型基金"
python ths_ifind.py --query-type fund "易方达蓝筹精选最新净值"
python ths_ifind.py --query-type fund "晨星评级5星的混合型基金"

# ==================== 港美股查询 ====================
python ths_ifind.py --query-type hkstock "腾讯控股最新价"
python ths_ifind.py --query-type usstock "苹果公司市盈率"

# ==================== 可转债查询 ====================
python ths_ifind.py --query-type conbond "双低值小于130的可转债"
python ths_ifind.py --query-type conbond "剩余期限小于1年的可转债"

# ==================== 指数查询 ====================
python ths_ifind.py --query-type zhishu "沪深300成分股"
python ths_ifind.py --query-type zhishu "上证50今日涨跌幅"

# ==================== 宏观经济/行业经济 ====================
python ths_ifind.py "中国GDP增速"
python ths_ifind.py "CPI PPI 最新数据"
python ths_ifind.py "半导体行业市盈率"

# ==================== 新闻公告资讯 ====================
python ths_ifind.py "贵州茅台最新公告"
python ths_ifind.py "今日涨停股票原因分析"

# ==================== 高级参数 ====================
# 指定排序
python ths_ifind.py "A股今日涨幅" --sort-key "涨跌幅" --sort-order desc
# 循环获取全部数据（默认只返回100条）
python ths_ifind.py "市盈率小于30的股票" --loop
# 循环获取前5页
python ths_ifind.py "市盈率小于30的股票" --loop 5
# 付费版（需付费cookie）
python ths_ifind.py "近3个月每日市盈率" --pro
# 置顶指定股票
python ths_ifind.py "A股今日涨幅" --find 600519 000010
```

### Python 脚本调用

```python
from ths_ifind import THSQuery

# 初始化（自动从环境变量 THS_COOKIE 读取 cookie）
ths = THSQuery()

# 查询A股
df = ths.query("今日涨幅大于2%的A股")
print(df)

# 查询基金
df = ths.query("近一年收益率大于20%的股票型基金", query_type="fund")

# 查询港股
df = ths.query("腾讯控股最新价", query_type="hkstock")

# 循环获取全部数据
df = ths.query("市盈率小于30的股票", loop=True)

# 指定排序
df = ths.query("A股今日涨幅", sort_key="涨跌幅", sort_order="desc")

# 保存为CSV
ths.save_csv(df, "涨幅前100")
```

## 处理流程

```
用户自然语言查询
      │
      ▼
  解析命令行参数（query, query_type, sort, loop, cookie等）
      │
      ▼
  检测环境（pywencai/pandas是否安装、Node.js是否可用、cookie是否配置）
      │
      ▼
  调用 pywencai.get()  ──→  同花顺问财服务器
      │                         │
      │                         ├─ get_robot_data: 解析自然语言 → 生成查询条件
      │                         │
      │                         └─ get_data_list: 按条件分页获取数据
      │                              │
      │                              ├─ 列表查询 → 返回 pandas.DataFrame
      │                              │
      │                              └─ 详情查询 → 返回 dict（含文本和DataFrame）
      │
      ▼
  格式化输出
      ├─ DataFrame → CSV 文件（UTF-8 BOM）
      ├─ dict → JSON 文件
      └─ 终端打印统计摘要
      │
      ▼
  保存描述文件（查询条件 + 行数 + 列名）
```

## API 参数详解

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `query` | str | 是 | 自然语言查询句 |
| `query_type` | str | 否 | 数据类型，默认 `stock`，可选：stock/zhishu/fund/hkstock/usstock/conbond/insurance/futures/lccp/foreign_exchange |
| `cookie` | str | 是 | 同花顺问财 Cookie（从环境变量 `THS_COOKIE` 或 `--cookie` 参数获取） |
| `sort_key` | str | 否 | 排序字段，值为返回结果的列名 |
| `sort_order` | str | 否 | 排序规则：`asc`（升序）或 `desc`（降序） |
| `loop` | bool/int | 否 | 是否循环分页。`True`=获取全部，数字=获取指定页数 |
| `page` | int | 否 | 查询页号，默认1 |
| `perpage` | int | 否 | 每页条数，默认100，最大100 |
| `pro` | bool | 否 | 付费版传 `True`，需付费版 cookie |
| `retry` | int | 否 | 请求失败重试次数，默认10 |
| `sleep` | float | 否 | 循环请求间隔秒数，默认0 |
| `find` | list | 否 | 置顶指定标的，如 `['600519', '000010']` |
| `no_detail` | bool | 否 | 为 `True` 时不返回详情字典，只返回 DataFrame |
| `log` | bool | 否 | 是否打印日志 |

## 异常情形与处理方式

| 异常情形 | 可能原因 | 处理方式 |
|----------|----------|----------|
| **ModuleNotFoundError: No module named 'pywencai'** | pywencai 库未安装 | 运行 `pip install pywencai` |
| **没有 node 命令或版本过低** | Node.js 未安装或版本 < v16 | 安装 Node.js v16+ |
| **cookie 为空或已过期** | 环境变量 THS_COOKIE 未设置或 Cookie 过期 | 重新登录同花顺获取新 Cookie |
| **data_list is empty** | 查询条件无匹配结果 | 检查查询语句，放宽筛选条件 |
| **请求超时 / Connection error** | 网络问题或代理配置 | 检查网络连接，确保证书验证通过 |
| **返回结果为 None** | 查询过于复杂或问财无法解析 | 简化查询语句，使用更自然直白的表达 |
| **返回 dict 而非 DataFrame** | 查询的是个股/指标详情 | 属正常行为，详情类查询返回字典 |

## 与 mx-xuangu 技能的对比

| 维度 | ths-ifind（本技能） | mx-xuangu |
|------|---------------------|-----------|
| 数据源 | 同花顺问财（iFinD体系） | 东方财富妙想 |
| 覆盖范围 | 股票/基金/港股/美股/可转债/期货/外汇/宏观/新闻 | A股选股为主 |
| 实时行情 | 支持（日内高频/实时） | 不支持实时 |
| 查询方式 | 自然语言 → DataFrame/Dict | 自然语言 → CSV |
| 认证方式 | Cookie（免费） | API Key |
| 付费版 | 支持（pro参数） | 不支持 |
| 输出格式 | CSV + JSON + 描述文件 | CSV + 描述文件 |
