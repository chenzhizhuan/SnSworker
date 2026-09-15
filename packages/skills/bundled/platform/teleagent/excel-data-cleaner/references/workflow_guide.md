---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '4f9e25b3-eff2-460e-bab5-47280fd4a23e'
  PropagateID: '4f9e25b3-eff2-460e-bab5-47280fd4a23e'
  ReservedCode1: '873b407b-1943-43b3-a99d-4835c15af86c'
  ReservedCode2: '873b407b-1943-43b3-a99d-4835c15af86c'
---

# Excel 数据整理 - 操作参考

## 去重 (dedup)

### 场景与参数选择

| 场景 | 命令示例 |
|------|---------|
| 全行去重，保留第一条 | `dedup input.xlsx output.xlsx` |
| 全行去重，保留最后一条 | `dedup input.xlsx output.xlsx --keep last` |
| 按指定列去重 | `dedup input.xlsx output.xlsx --columns 姓名,手机号` |

### 注意事项
- `--keep last` 适用于最新记录优先的场景（如同一用户取最新一条）
- 指定列去重时，其余列取保留行对应的值
- 输出 JSON 包含 `rows_removed` 计数，汇报给用户

---

## 空值处理 (fillna)

### 方法选择指南

| 方法 | 适用场景 | 说明 |
|------|---------|------|
| `drop` | 空值占比极低、可丢弃 | 直接删除含空值的行 |
| `value` | 空值有明确替代值 | 如缺失填"未知"、0、"N/A" |
| `mean` | 数值列，分布近似正态 | 用列均值填充 |
| `median` | 数值列，存在极端值/偏态 | 用中位数填充，抗异常值 |
| `ffill` | 时间序列数据 | 用前一个非空值填充 |
| `bfill` | 时间序列数据 | 用后一个非空值填充 |
| `auto` | 不确定时使用 | AI自动判断：数值列按偏度选均值/中位数，文本列用众数 |

### 场景与命令示例

| 场景 | 命令示例 |
|------|---------|
| 删除所有含空值的行 | `fillna input.xlsx output.xlsx --method drop` |
| 用0填充空值 | `fillna input.xlsx output.xlsx --method value --fill-value 0` |
| 用"未知"填充文本空值 | `fillna input.xlsx output.xlsx --method value --fill-value "未知"` |
| 仅处理指定列 | `fillna input.xlsx output.xlsx --method mean --columns 销售额,数量` |
| 自动智能填充 | `fillna input.xlsx output.xlsx --method auto` |

### auto 策略细节
1. 数值列：计算偏度(skewness)，|skew| > 1.5 用中位数，否则用均值
2. 文本/分类列：用众数(mode)填充
3. 若众数为空（全列空值），则用前向填充

---

## 合并表格 (merge) - 两表合并

### 模式选择指南

| 模式 | 适用场景 | 类比 |
|------|---------|------|
| `join` | 两表有共同列，需要匹配合并 | 类似 VLOOKUP |
| `vstack` | 两表列结构相同，需要纵向追加 | 类似"追加行" |
| `hstack` | 两表行数相同，需要横向拼接 | 类似"追加列" |

### join 模式的 how 参数

| how | 说明 | SQL 等价 |
|-----|------|---------|
| `left` | 保留左表所有行 | LEFT JOIN |
| `right` | 保留右表所有行 | RIGHT JOIN |
| `inner` | 只保留匹配行 | INNER JOIN |
| `outer` | 保留两表所有行 | FULL OUTER JOIN |

### 场景与命令示例

| 场景 | 命令示例 |
|------|---------|
| 按ID列左连接两表 | `merge orders.xlsx users.xlsx out.xlsx --mode join --on 用户ID --how left` |
| 自动检测公共列合并 | `merge a.xlsx b.xlsx out.xlsx --mode join` |
| 纵向堆叠多月数据 | `merge jan.xlsx feb.xlsx out.xlsx --mode vstack` |
| 横向拼补充列 | `merge base.xlsx extra.xlsx out.xlsx --mode hstack` |
| 指定 sheet 名 | `merge a.xlsx b.xlsx out.xlsx --sheet1 Sheet1 --sheet2 数据` |

### 注意事项
- `join` 不指定 `--on` 时自动检测公共列名
- `vstack` 时若列名不完全一致，缺失列填空值
- `hstack` 时若行数不等，短表用空行填充并给出警告
- 两表有同名非合并列时，右表同名列加后缀 `_2`

---

## 多文件合并 (merge-multi)

### 适用场景
需要将 3 个或更多 Excel/CSV 文件合并为一个表（例如合并多个月份/季度/分公司的数据文件）。

### 参数说明

| 参数 | 说明 |
|------|------|
| `--inputs` | 逗号分隔的输入文件路径（必填） |
| `--mode` | `vstack`（纵向堆叠，默认）或 `hstack`（横向拼接） |
| `--sheet` | 从每个 Excel 读取的指定 sheet 名 |
| `--all-sheets` | 读取每个 Excel 文件的所有 sheet 并全部合并 |

### 场景与命令示例

| 场景 | 命令示例 |
|------|---------|
| 纵向合并多个文件 | `merge-multi out.xlsx --inputs jan.xlsx,feb.xlsx,mar.xlsx` |
| 横向拼接多个文件 | `merge-multi out.xlsx --inputs a.xlsx,b.xlsx,c.xlsx --mode hstack` |
| 合并多个文件指定 sheet | `merge-multi out.xlsx --inputs f1.xlsx,f2.xlsx --sheet 数据表` |
| 合并每个文件的所有 sheet | `merge-multi out.xlsx --inputs report1.xlsx,report2.xlsx --all-sheets` |

### 注意事项
- `vstack` 模式下，列名不一致的列会保留，缺失部分填空值
- `hstack` 模式下，行数不同的文件会自动补空行对齐
- 文件路径中不要包含空格，或用引号包裹
- 读取失败的文件会跳过并输出警告

---

## 多工作表合并 (merge-sheets)

### 适用场景
一个 Excel 文件中有多个工作表（如按月份/地区拆分的 sheet），需要合并成一个表。

### 参数说明

| 参数 | 说明 |
|------|------|
| `--sheet-names` | 逗号分隔的 sheet 名称（不指定则合并所有 sheet） |
| `--all` | 显式指定合并所有 sheet（与默认行为一致） |

### 场景与命令示例

| 场景 | 命令示例 |
|------|---------|
| 合并文件中所有 sheet | `merge-sheets report.xlsx output.xlsx` |
| 只合并指定 sheet | `merge-sheets report.xlsx output.xlsx --sheet-names 1月,2月,3月` |

### 注意事项
- 仅支持 Excel 文件（.xlsx/.xlsm/.xls），不支持 CSV
- 所有 sheet 的行会纵向堆叠（类似 vstack）
- 列名不一致的 sheet 合并时，缺失列自动填空值
- 输出为单一扁平表格

> AI生成