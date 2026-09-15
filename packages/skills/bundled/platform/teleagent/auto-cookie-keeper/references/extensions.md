---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '03f889a7-6869-4d67-bdce-56116beec25f'
  PropagateID: '03f889a7-6869-4d67-bdce-56116beec25f'
  ReservedCode1: '166e7079-eb20-4f3d-9c66-b880b14ae7a4'
  ReservedCode2: '166e7079-eb20-4f3d-9c66-b880b14ae7a4'
---

# 20 项扩展操作详细框架

> 本文件为公网版模式的扩展操作配置引导。每项操作包含：提示词模板、配置参数表、定时任务脚本骨架、注意事项。
>
> **公网版前提**：Cookie 已由 Agent 提取并保存到用户指定目录（如 `D:\cookies`），Cookie 刷新定时任务已创建并正常运行。以下所有扩展操作脚本均从该目录读取 Cookie。
>
> Agent 在引导用户配置时，按以下流程执行：
> 1. 展示操作清单，用户选择需要的项目
> 2. 针对每项，用大白话向用户解释需要什么参数，收集配置（API 地址、频率、推送方式等）
> 3. 基于骨架脚本生成完整定时任务，保存到 `.temp/` 目录
> 4. 通过 `scheduler` 技能创建定时任务
> 5. 首次运行验证，向用户确认输出正确
>
> **面向 0 基础用户原则**：每个参数都用大白话解释含义，不要假设用户懂技术术语。

---

## 通用：Cookie 读取与 HTTP 请求

所有扩展操作脚本共用 Cookie 文件读取逻辑。Cookie 文件路径来自公网版第三步用户指定的保存目录：

```python
import json, ssl, gzip, os
from urllib import request, error

# ========== 配置区（Agent 根据用户信息填充）==========
SYSTEM_NAME = "系统名称"       # 用户在第一步起的系统名
COOKIE_DIR = r"用户指定目录"     # 用户在第一步指定的文件夹，如 D:\cookies
COOKIE_FILE = os.path.join(COOKIE_DIR, f"{SYSTEM_NAME}_cookies.json")
# ===================================================

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

def load_cookies(cookie_file):
    """从 JSON 文件加载 Cookie，返回 Cookie 字符串"""
    with open(cookie_file, "r", encoding="utf-8") as f:
        cookies = json.load(f)
    parts = [f"{c['name']}={c['value']}" for c in cookies]
    return "; ".join(parts)

def api_request(url, method="GET", data=None, cookie_str=None, max_retries=3):
    """安全 HTTP 请求（防连接泄漏）"""
    headers = {
        "Accept": "application/json, text/plain, */*",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept-Encoding": "gzip, identity",
    }
    if method == "POST":
        headers["Content-Type"] = "application/json;charset=UTF-8"
    if cookie_str:
        headers["Cookie"] = cookie_str
    for attempt in range(max_retries):
        try:
            req_data = json.dumps(data, ensure_ascii=False).encode("utf-8") if data else None
            req = request.Request(url, data=req_data, headers=headers, method=method)
            resp = request.urlopen(req, context=SSL_CTX, timeout=30)
            try:
                raw = resp.read()
                if resp.headers.get("Content-Encoding") == "gzip":
                    raw = gzip.decompress(raw)
                body = raw.decode("utf-8")
                if body.lstrip().startswith(("<!DOCTYPE", "<html", "<HTML")):
                    raise Exception("登录已失效（API 返回 HTML 登录页）")
                return json.loads(body)
            finally:
                resp.close()
        except error.HTTPError as e:
            try:
                e.read()
            finally:
                try: e.close()
                except: pass
            if attempt < max_retries - 1:
                import time; time.sleep(2)
            else:
                raise
        except Exception:
            if attempt < max_retries - 1:
                import time; time.sleep(2)
            else:
                raise
```

---

## 1. 资料下载

| 参数 | 说明 | 示例 |
|------|------|------|
| download_api | 下载接口地址 | `http://系统/api/files/list` |
| save_dir | 本地保存目录 | `D:\downloads\reports` |
| naming_rule | 文件命名规则 | `{date}_{filename}.xlsx` |
| frequency | 下载频率 | 每天一次 / 每小时 |
| mode | 增量或全量 | `incremental` / `full` |

**提示词模板**：
> 定时从 {系统名称} 批量下载报表文件，保存到 {保存目录}。文件命名规则：{命名规则}。下载模式：{增量/全量}。下载频率：{频率}。

**脚本骨架**：
```python
def run_download(cookie_file, config):
    cookie_str = load_cookies(cookie_file)
    data = api_request(config["download_api"], cookie_str=cookie_str)
    for item in data.get("files", []):
        file_url = item["url"]
        filename = config["naming_rule"].format(
            date=item.get("date", ""), filename=item["name"])
        save_path = os.path.join(config["save_dir"], filename)
        # 下载文件...
        log(f"已下载: {filename}")
```

---

## 2. 数据库更新

| 参数 | 说明 | 示例 |
|------|------|------|
| source_api | 数据源接口 | `http://系统/api/data/list` |
| db_type | 数据库类型 | `sqlite` / `mysql` |
| db_conn | 连接串 | `sqlite:///data.db` |
| field_mapping | 字段映射 | `{"sys_id": "id", "sys_name": "name"}` |
| write_mode | 写入模式 | `upsert` / `append` / `replace` |
| frequency | 同步频率 | 每小时 / 每天 |

**提示词模板**：
> 定时从 {系统名称} 拉取数据，写入 {数据库类型} 数据库。写入模式：{覆盖/追加/更新}。同步频率：{频率}。

**脚本骨架**：
```python
def run_db_sync(cookie_file, config):
    cookie_str = load_cookies(cookie_file)
    data = api_request(config["source_api"], cookie_str=cookie_str)
    # 数据库写入逻辑
    for record in data.get("list", []):
        mapped = {k: record.get(v) for k, v in config["field_mapping"].items()}
        # upsert / append / replace 逻辑
    log(f"同步完成: {len(data.get('list', []))} 条")
```

---

## 3. 变动提醒

| 参数 | 说明 | 示例 |
|------|------|------|
| monitor_api | 监控接口 | `http://系统/api/status` |
| change_logic | 变动判断逻辑 | `threshold:50` / `diff:10%` / `new_record` |
| last_state_file | 状态存储文件 | `last_state.json` |
| notify_channel | 通知渠道 | `bark` / `email` |
| frequency | 检查频率 | 每 30 分钟 |
| dedup_seconds | 防重复间隔 | 3600 秒 |

**提示词模板**：
> 监控 {系统名称} 的 {监控指标}，变动超过 {阈值} 时通过 {渠道} 推送通知。检查频率：{频率}。

---

## 4. 增量资料

| 参数 | 说明 | 示例 |
|------|------|------|
| api_url | 增量查询接口 | `http://系统/api/data?since={watermark}` |
| watermark_field | 水位线字段 | `update_time` |
| watermark_file | 水位线存储 | `watermark.json` |
| fallback_full | 异常回退全量 | `true` / `false` |

**提示词模板**：
> 从 {系统名称} 增量拉取数据，水位线字段：{字段名}。异常时回退全量拉取。拉取频率：{频率}。

---

## 5. 网络故障巡查

| 参数 | 说明 | 示例 |
|------|------|------|
| alert_api | 告警接口 | `http://AIOps/api/alerts` |
| filter_conditions | 筛选条件 | `level>=3, status=open` |
| notify_template | 通知模板 | `故障: {title}\n级别: {level}\n责任人: {owner}` |
| owner_mapping | 责任人映射 | `{"区域A": "张三"}` |
| frequency | 巡查频率 | 每 15 分钟 |
| quiet_hours | 静默时段 | `0-8` |

**提示词模板**：
> 定时巡查 {告警平台} 的未处理故障，级别 {级别} 以上时通知责任人。巡查频率：{频率}。静默时段：{时段}。

---

## 6. 自动接单

| 参数 | 说明 | 示例 |
|------|------|------|
| pool_api | 工单池接口 | `http://系统/api/workorder/pool` |
| accept_conditions | 接单条件 | `type=网络故障, area=南开` |
| accept_api | 接单操作接口 | `http://系统/api/workorder/accept` |
| reply_template | 自动回复模板 | `已接单，正在处理...` |
| conflict_strategy | 冲突处理 | `first_come` / `skip_if_taken` |

**提示词模板**：
> 监控 {系统} 工单池，符合条件（{条件}）的新工单自动接单并回复。检查频率：{频率}。

> **注意**：自动接单涉及写操作，属于敏感操作。配置时必须让用户确认接单条件和回复内容。

---

## 7. 公文流转监控

| 参数 | 说明 | 示例 |
|------|------|------|
| doc_api | 公文列表接口 | `http://OA/api/documents` |
| read_marker_file | 已读标记存储 | `read_docs.json` |
| summary_rule | 摘要提取规则 | `title + first_100_chars` |
| notify_channel | 推送渠道 | `bark` / `email` |
| frequency | 检查频率 | 每 2 小时 |

**提示词模板**：
> 定时检查 {OA系统} 是否有新公文下发，发现新公文时推送通知并提取摘要。检查频率：{频率}。

---

## 8. 审批流程催办

| 参数 | 说明 | 示例 |
|------|------|------|
| pending_api | 待审批列表接口 | `http://OA/api/approvals/pending` |
| timeout_hours | 超时阈值 | 24 小时 |
| urge_template | 催办消息模板 | `{审批人}，您有 {N} 项待审批超时，请尽快处理` |
| escalate_rules | 升级机制 | `超48h→上级, 超72h→部门负责人` |
| frequency | 检查频率 | 每天上午 9 点 |

**提示词模板**：
> 定时检查 {OA系统} 待审批事项，超时 {N} 小时未处理自动催办。检查频率：{频率}。

---

## 9. 报表自动生成

| 参数 | 说明 | 示例 |
|------|------|------|
| source_apis | 数据源接口列表 | `["url1", "url2"]` |
| aggregation_logic | 汇总逻辑 | `sum, avg, count` |
| report_template | 报表模板 | Excel 模板路径 |
| output_format | 输出格式 | `xlsx` / `pdf` |
| recipients | 推送对象 | `["user1@example.com"]` |
| frequency | 生成频率 | 每周一上午 |

**提示词模板**：
> 定时从 {N} 个数据源拉取数据，按模板生成 {格式} 报表，推送给 {对象}。生成频率：{频率}。

---

## 10. 工单状态跟踪

| 参数 | 说明 | 示例 |
|------|------|------|
| query_api | 工单查询接口 | `http://系统/api/workorder/query` |
| track_conditions | 跟踪条件 | `status!=archived, created>7days` |
| timeout_threshold | 超时阈值 | 48 小时无更新 |
| alert_channel | 告警渠道 | `bark` |
| frequency | 跟踪频率 | 每小时 |

**提示词模板**：
> 跟踪 {系统} 工单处理进度，超过 {N} 小时无更新时告警。跟踪频率：{频率}。

---

## 11. 值班排班提醒

| 参数 | 说明 | 示例 |
|------|------|------|
| schedule_source | 排班数据源 | API 地址 / 本地文件路径 |
| advance_hours | 提前提醒时间 | 2 小时 |
| reminder_template | 提醒模板 | `今天您值班，值班时间 {time}，地点 {location}` |
| holiday_handling | 节假日处理 | `skip` / `still_remind` |

**提示词模板**：
> 定时读取排班表，值班前 {N} 小时推送提醒。节假日处理：{策略}。

---

## 12. 资源利用率监控

| 参数 | 说明 | 示例 |
|------|------|------|
| monitor_api | 监控接口 | `http://监控平台/api/metrics` |
| metrics_list | 监控指标 | `["cpu", "memory", "disk", "bandwidth"]` |
| thresholds | 阈值配置 | `{"cpu": 80, "memory": 90, "disk": 85}` |
| confirm_count | 连续超次确认 | 3 次 |
| alert_level | 告警级别 | `warning` / `critical` |

**提示词模板**：
> 监控 {监控平台} 资源利用率，{指标} 超过 {阈值} 连续 {N} 次时告警。检查频率：{频率}。

---

## 13. 会议纪要归档

| 参数 | 说明 | 示例 |
|------|------|------|
| meeting_api | 会议列表接口 | `http://OA/api/meetings` |
| minutes_field | 纪要字段 | `minutes_content` |
| archive_dir | 归档目录 | `D:\archive\meetings\{year}\{month}` |
| participants_field | 参会人字段 | `attendees` |
| notify_channel | 推送渠道 | `bark` / `email` |

**提示词模板**：
> 定时从 {OA系统} 提取会议纪要，归档到 {目录}，并推送给参会人员。检查频率：{频率}。

---

## 14. 考勤数据同步

| 参数 | 说明 | 示例 |
|------|------|------|
| attendance_api | 考勤接口 | `http://考勤系统/api/records` |
| sync_scope | 同步范围 | `dept:IT, period:last_month` |
| data_mapping | 数据映射 | `{"clock_in": "上班时间", "clock_out": "下班时间"}` |
| stats_rules | 统计规则 | `late: >09:30, early: <17:00` |
| output_format | 输出格式 | `xlsx` |

**提示词模板**：
> 定时拉取 {考勤系统} 数据，同步到本地并生成统计报表。同步范围：{范围}。同步频率：{频率}。

---

## 15. 资产台账核对

| 参数 | 说明 | 示例 |
|------|------|------|
| asset_api | 资产接口 | `http://资产系统/api/assets` |
| compare_dimensions | 核对维度 | `["location", "status", "owner"]` |
| last_inventory_file | 上次台账文件 | `last_assets.json` |
| notify_admin | 通知对象 | 资产管理员 |

**提示词模板**：
> 定时核对 {资产系统} 台账，检测资产变更并通知管理员。核对频率：{频率}。

---

## 16. 合同到期提醒

| 参数 | 说明 | 示例 |
|------|------|------|
| contract_api | 合同接口 | `http://合同系统/api/contracts` |
| expire_field | 到期日期字段 | `end_date` |
| remind_gradient | 提醒梯度 | `[30, 15, 7, 3, 1]` 天 |
| remind_targets | 提醒对象映射 | `{"30": "经办人", "7": "部门负责人"}` |
| notify_channel | 推送渠道 | `bark` / `email` |

**提示词模板**：
> 监控 {合同系统} 合同到期情况，到期前 {梯度} 天分别提醒 {对象}。检查频率：{频率}。

---

## 17. 流程节点监控

| 参数 | 说明 | 示例 |
|------|------|------|
| process_api | 流程实例接口 | `http://OA/api/process/instances` |
| key_nodes | 关键节点定义 | `["审批", "归档", "归集"]` |
| stall_hours | 停滞阈值 | 48 小时 |
| escalate_chain | 升级通知链 | `["处理人", "上级", "部门负责人"]` |

**提示词模板**：
> 监控 {OA系统} 业务流程关键节点，卡住超过 {N} 小时自动通知。检查频率：{频率}。

---

## 18. 知识库更新检测

| 参数 | 说明 | 示例 |
|------|------|------|
| kb_api | 知识库接口 | `http://知识库/api/articles` |
| change_detection | 变更检测方式 | `version_diff` / `update_time` |
| sync_dir | 本地同步目录 | `D:\knowledge_base\` |
| summary_rule | 摘要规则 | `title + first_200_chars` |
| notify_channel | 推送渠道 | `bark` / `email` |

**提示词模板**：
> 监控 {知识库系统} 内容变更，增量同步到本地并推送更新摘要。检查频率：{频率}。

---

## 19. 运维日志收集

| 参数 | 说明 | 示例 |
|------|------|------|
| log_apis | 日志接口列表 | `["url1", "url2", "url3"]` |
| filter_rules | 过滤规则 | `level>=WARNING` |
| archive_dir | 归档目录 | `D:\logs\{system}\{date}` |
| summary_logic | 摘要逻辑 | `count_by_level + top_errors` |
| retention_days | 保留期限 | 90 天 |

**提示词模板**：
> 定时收集 {N} 个系统运维日志，归档并生成日志摘要。保留期限：{N} 天。收集频率：{频率}。

---

## 20. 跨系统数据比对

| 参数 | 说明 | 示例 |
|------|------|------|
| system_apis | 多系统接口 | `{"sys_a": "url1", "sys_b": "url2"}` |
| align_key | 对齐键 | `workorder_id` |
| compare_fields | 比对字段 | `["status", "owner", "level"]` |
| tolerance | 容忍度 | `exact` / `case_insensitive` / `ignore_null` |
| report_format | 差异报告格式 | `xlsx` / `html` |

**提示词模板**：
> 从 {系统A} 和 {系统B} 拉取同类数据，以 {对齐键} 比对 {字段} 差异，生成差异报告。比对频率：{频率}。

---

## 定时任务创建流程

每项扩展操作配置完成后，通过 `scheduler` 技能创建定时任务：

1. **生成脚本**：基于骨架脚本 + 用户配置参数，生成完整 Python 脚本
2. **保存脚本**：脚本保存到 `.temp/` 目录（中间文件）
3. **创建定时任务**：调用 `scheduler` 技能，按用户指定频率创建 cron 任务
4. **首次验证**：手动触发一次，确认输出正确
5. **通知验证**：如涉及推送，确认通知能收到

### 定时任务脚本通用骨架

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""{操作名称} 定时任务脚本"""

import json, os, sys, time, ssl, gzip
from urllib import request, error
from datetime import datetime

# ========== 配置区（Agent 根据用户信息填充）==========
SYSTEM_NAME = "系统名称"
COOKIE_DIR = r"用户指定目录"     # 公网版第一步用户指定的文件夹
COOKIE_FILE = os.path.join(COOKIE_DIR, f"{SYSTEM_NAME}_cookies.json")
CONFIG = {
    # 用户配置参数填充区
}
# ===================================================

# ========== Cookie 加载 ==========
def load_cookies(cookie_file):
    with open(cookie_file, "r", encoding="utf-8") as f:
        cookies = json.load(f)
    return "; ".join(f"{c['name']}={c['value']}" for c in cookies)

# ========== API 请求 ==========
def api_request(url, method="GET", data=None, cookie_str=None):
    # 见通用 HTTP 请求模式
    pass

# ========== Bark 推送 ==========
def send_bark(title, body):
    # 见 code-patterns.md 第 14 节
    pass

# ========== 主逻辑 ==========
def main():
    if not os.path.exists(COOKIE_FILE):
        print(f"[ERROR] Cookie 文件不存在: {COOKIE_FILE}")
        sys.exit(1)
    
    cookie_str = load_cookies(COOKIE_FILE)
    
    try:
        # {操作特定逻辑}
        result = api_request(CONFIG["api_url"], cookie_str=cookie_str)
        # 处理结果...
        print(f"[OK] {datetime.now()} 执行完成")
    except Exception as e:
        print(f"[ERROR] {e}")
        send_bark("任务执行失败", str(e))
        sys.exit(1)

if __name__ == "__main__":
    main()
```

---

## 配置引导对话示例

以下是一个完整的引导对话示例（以「变动提醒」为例）：

```
Agent: 你选择了「变动提醒」功能。我需要确认几个参数：
  1. 监控哪个系统的什么指标？
  2. 变动判断逻辑？（阈值/差值/新增记录）
  3. 通知渠道？（Bark 推送 / 邮件 / 其他）
  4. 检查频率？（每 30 分钟 / 每小时 / 其他）

用户: 监控 AIOps 告警平台的未处理工单数量，超过 10 个就通知我，用 Bark 推送，每 15 分钟检查一次。

Agent: 好的，配置确认：
  - 监控接口：AIOps 告警列表 API
  - 变动逻辑：未处理工单数量 > 10
  - 通知渠道：Bark 推送
  - 检查频率：每 15 分钟
  
  正在生成定时任务脚本...
  脚本已生成，正在创建定时任务...
  定时任务已创建。首次运行验证中...
  
  验证通过：当前未处理工单 5 个，未触发阈值。
  任务已就绪，每 15 分钟自动检查。
```