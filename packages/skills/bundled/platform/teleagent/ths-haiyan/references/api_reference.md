---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: 'fe5b515f-d43b-4b55-9517-cd49868fc49c'
  PropagateID: 'fe5b515f-d43b-4b55-9517-cd49868fc49c'
  ReservedCode1: '8b154902-b5cc-492f-ad2a-ea0813c7ed95'
  ReservedCode2: '8b154902-b5cc-492f-ad2a-ea0813c7ed95'
---

# 同花顺数据接口参考

基于 akshare (v1.18+) 开源库封装的同花顺数据中心接口，所有数据来源为同花顺（10jqka.com.cn）公开页面。

## 依赖

```bash
pip install akshare pandas
```

## 功能模块与接口列表

### 1. 实时行情

| 命令(func) | 说明 | 参数 |
|---|---|---|
| `a_spot` | A股全部实时行情 | 无 |
| `sh_spot` | 沪A实时行情 | 无 |
| `sz_spot` | 深A实时行情 | 无 |

### 2. 历史K线

| 命令(func) | 说明 | 参数 |
|---|---|---|
| `hist` | 个股历史K线 | `--symbol`(6位代码) `--period`(daily/weekly/monthly) `--start_date`(YYYYMMDD) `--end_date`(YYYYMMDD) `--adjust`(qfq/hfq) |

示例：
```bash
python ths_data.py hist --symbol 000001 --period daily --start_date 20240101 --end_date 20240630 --adjust qfq
```

### 3. 同花顺行业板块

| 命令(func) | 说明 | 参数 |
|---|---|---|
| `industry_name` | 行业板块列表 | 无 |
| `industry_info` | 行业板块成分股及详情 | `--symbol`(板块名称，如"半导体") |
| `industry_summary` | 行业板块汇总 | 无 |
| `industry_index` | 行业板块指数历史 | `--symbol`(板块名称) `--start_date` `--end_date` |

### 4. 同花顺概念板块

| 命令(func) | 说明 | 参数 |
|---|---|---|
| `concept_name` | 概念板块列表 | 无 |
| `concept_info` | 概念板块成分股及详情 | `--symbol`(概念名称，如"人工智能") |
| `concept_summary` | 概念板块汇总 | 无 |
| `concept_index` | 概念板块指数历史 | `--symbol`(概念名称) `--start_date` `--end_date` |

### 5. 同花顺技术选股

| 命令(func) | 说明 | 参数 |
|---|---|---|
| `rank_cxg` | 创新高 | `--symbol`(创月新高/创季新高/创半年新高/创年新高) |
| `rank_cxd` | 创新低 | `--symbol`(创月新低/创季新低/创半年新低/创年新低) |
| `rank_ljqs` | 连涨 | 无 |
| `rank_ljqd` | 连跌 | 无 |
| `rank_lxsz` | 连续缩量 | 无 |
| `rank_cxfl` | 创周新高 | 无 |

### 6. 资金流向

| 命令(func) | 说明 | 参数 |
|---|---|---|
| `fund_flow` | 个股资金流向 | `--stock`(代码) `--market`(sh/sz) |
| `market_fund_flow` | 大盘资金流向 | 无 |
| `sector_fund_rank` | 板块资金排名 | `--indicator`(今日/3日/5日/10日) `--sector_type`(行业资金流/概念资金流) |
| `individual_fund_rank` | 个股资金排名 | `--indicator`(今日/3日/5日/10日) |

### 7. 龙虎榜

| 命令(func) | 说明 | 参数 |
|---|---|---|
| `lhb_detail` | 龙虎榜明细 | `--start_date`(YYYYMMDD) `--end_date`(YYYYMMDD) |
| `lhb_statistic` | 龙虎榜上榜统计 | `--symbol`(近一月/近三月/近六月/近一年) |

### 8. 个股信息与财务

| 命令(func) | 说明 | 参数 |
|---|---|---|
| `stock_info` | 个股基本信息 | `--symbol`(6位代码) |
| `financial_abstract` | 同花顺主要财务指标 | `--symbol`(6位代码) `--indicator`(按报告期/按年度) |
| `financial_indicator` | 财务分析指标 | `--symbol`(6位代码) |

### 9. 人气排名

| 命令(func) | 说明 | 参数 |
|---|---|---|
| `hot_rank` | 人气排名 | 无 |

### 通用参数

| 参数 | 说明 |
|---|---|
| `--limit N` | 限制返回行数(0=全部) |

## 返回格式

JSON，结构为 `{"count": N, "data": [...]}` 或 `{"error": "..."}`

## 常见用途场景

- 查某只股票的实时行情和K线：`a_spot` / `hist`
- 查某行业的成分股和资金流：`industry_info` / `sector_fund_rank`
- 查某概念板块的成分股：`concept_info`
- 查资金流入流出排名：`individual_fund_rank` / `sector_fund_rank`
- 查创新高/连涨等技术选股：`rank_cxg` / `rank_ljqs`
- 查龙虎榜机构席位：`lhb_detail`
- 查个股基本面：`stock_info` / `financial_abstract`

> AI生成