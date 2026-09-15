---
name: ths-haiyan
description: 同花顺股票数据获取与分析技能，基于akshare开源库封装同花顺数据中心公开接口，可获取9大功能模块数据：(1)A股实时行情，(2)个股历史K线，(3)同花顺行业板块及成分股，(4)同花顺概念板块及成分股，(5)技术选股排名(创新高/连涨/缩量等)，(6)资金流向(个股/板块/大盘)，(7)龙虎榜数据，(8)个股基本信息与财务指标，(9)人气排名。当用户提到同花顺、股票行情、板块成分股、资金流向、龙虎榜、技术选股、个股分析、股票数据、个股财务时触发。关键词：同花顺、股票、行情、K线、板块、概念、资金流、龙虎榜、选股、财务指标、人气排名。
name_cn: 光明顶-同花顺-海燕版
description_cn: 封装同花顺数据中心公开接口，获取实时行情、个股财务、板块成分股、资金流向、龙虎榜、技术选股等9大功能模块全量数据
create_source: super-agent-skill-creator
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '58ba738c-479a-4ff7-b088-b7606fd0d8c1'
  PropagateID: '58ba738c-479a-4ff7-b088-b7606fd0d8c1'
  ReservedCode1: 'b0d12f5d-e0da-4a16-b1db-5ecba5b4b1de'
  ReservedCode2: 'b0d12f5d-e0da-4a16-b1db-5ecba5b4b1de'
---

# 同花顺-海燕版

基于 akshare 开源库封装同花顺数据中心接口，获取A股全市场数据。

## 依赖安装

首次使用需安装 akshare：

```bash
pip install akshare pandas
```

## 核心脚本

[scripts/ths_data.py](scripts/ths_data.py) — 统一CLI入口，通过 `func` 参数选择功能。

## 使用方式

通过 PowerShell 调用脚本获取数据，结果为 JSON 格式 `{"count": N, "data": [...]}`。

### 实时行情

```bash
python scripts/ths_data.py a_spot --limit 20
python scripts/ths_data.py sh_spot --limit 10
python scripts/ths_data.py sz_spot --limit 10
```

### 个股历史K线

```bash
python scripts/ths_data.py hist --symbol 000001 --period daily --start_date 20240101 --end_date 20240630 --adjust qfq
python scripts/ths_data.py hist --symbol 000001 --period weekly --adjust qfq
```

### 同花顺行业板块

```bash
# 行业板块列表
python scripts/ths_data.py industry_name
# 某行业成分股（如"半导体"）
python scripts/ths_data.py industry_info --symbol "半导体"
# 行业板块汇总
python scripts/ths_data.py industry_summary
# 行业板块指数历史
python scripts/ths_data.py industry_index --symbol "元件" --start_date 20240101
```

### 同花顺概念板块

```bash
# 概念板块列表
python scripts/ths_data.py concept_name
# 某概念成分股（如"人工智能"）
python scripts/ths_data.py concept_info --symbol "人工智能"
# 概念板块汇总
python scripts/ths_data.py concept_summary
# 概念板块指数历史
python scripts/ths_data.py concept_index --symbol "阿里巴巴概念" --start_date 20240101
```

### 技术选股排名

```bash
# 创月新高（可选：创月新高/创季新高/创半年新高/创年新高）
python scripts/ths_data.py rank_cxg --symbol "创月新高" --limit 30
# 创月新低
python scripts/ths_data.py rank_cxd --symbol "创月新低" --limit 30
# 连涨
python scripts/ths_data.py rank_ljqs --limit 30
# 连跌
python scripts/ths_data.py rank_ljqd --limit 30
# 连续缩量
python scripts/ths_data.py rank_lxsz --limit 30
# 创周新高
python scripts/ths_data.py rank_cxfl --limit 30
```

### 资金流向

```bash
# 个股资金流向
python scripts/ths_data.py fund_flow --stock 600000 --market sh
# 大盘资金流向
python scripts/ths_data.py market_fund_flow
# 板块资金排名（行业/概念，今日/3日/5日/10日）
python scripts/ths_data.py sector_fund_rank --indicator "今日" --sector_type "行业资金流"
python scripts/ths_data.py sector_fund_rank --indicator "3日" --sector_type "概念资金流"
# 个股资金排名
python scripts/ths_data.py individual_fund_rank --indicator "5日" --limit 30
```

### 龙虎榜

```bash
# 龙虎榜明细
python scripts/ths_data.py lhb_detail --start_date 20240601 --end_date 20240630
# 龙虎榜上榜统计（近一月/近三月/近六月/近一年）
python scripts/ths_data.py lhb_statistic --symbol "近一月"
```

### 个股信息与财务

```bash
# 个股基本信息
python scripts/ths_data.py stock_info --symbol 000001
# 主要财务指标（按报告期/按年度）
python scripts/ths_data.py financial_abstract --symbol 000063 --indicator "按报告期"
# 财务分析指标
python scripts/ths_data.py financial_indicator --symbol 600004
```

### 人气排名

```bash
python scripts/ths_data.py hot_rank --limit 30
```

## 工作流程建议

1. **选股筛选**：`a_spot` 全市场行情 → `individual_fund_rank` 资金流入股 → `rank_cxg` 创新高股
2. **板块分析**：`industry_name`/`concept_name` 列板块 → `sector_fund_rank` 看资金 → `industry_info`/`concept_info` 查成分股
3. **个股深度**：`stock_info` 基本信息 → `hist` K线走势 → `financial_abstract` 财务指标 → `fund_flow` 资金流向
4. **龙虎榜跟踪**：`lhb_detail` 查机构席位 → `lhb_statistic` 统计上榜次数

## 接口完整参考

详见 [references/api_reference.md](references/api_reference.md)，包含全部命令、参数说明和返回格式。