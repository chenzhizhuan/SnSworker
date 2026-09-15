#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_period.py - 步骤标注格式34项检测器
v2026.09.12-v2 形态层防截断改造（▸子行→表格，新增6项废弃/动作列检测器29-34）

检测项目（34项）：
  1.  步骤名重用（同一名称出现两次）
  2.  步骤名重置（名称序列从非预期位置重新开始）
  3.  步骤名跳号（如步骤序列跳过中间项）
  4.  步骤内容重复（两个步骤的表格内容高度相似）
  5.  degraded后重做（degraded标注后又重复执行相同操作）
  6.  截断标记误用-自然截断标记出现在非截断场景
  7.  截断标记误用-工具调用中断标记出现在非中断场景
  8.  批次标记文本出现（静默分界禁止输出批次文本）
  9.  三种截断标记混用（同一位置出现两种以上标记）
  10. 📝要点列缺失（状态卡第3列不存在）
  11. 📝要点列超长（状态卡第3列超长）
  12. 过渡文字（最后一张表格与工具调用之间存在过渡文字）
  13. 单批超4步（单次消息流连续输出超过4个Step）
  14. 表格单元格标点结尾（单元格以禁止的标点符号结尾）
  15. 主行超长（Step主行超过40字）
  16. 表格单元格超长（单元格超过80字）
  17. 同名称重写（已输出的步骤名称被重新输出）
  18. 📝要点列语义不完整（纯状态词或疑似词断截断）
  19. 静默分界后确认提问（第4/8/12个步骤后禁止紧接question确认类提问）
  20. 静默分界后无工具调用（第4/8/12个步骤后6行内无工具调用→批次停滞）
  21. 名称乱序（步骤名称小于前序最大且未出现过，非预期重置场景）
  22. 功能标题重复（同一功能标题相似度≥80%出现两次）
  23. 工具调用返回后无续批Step（工具调用块后有文本但无新Step标注→工具返回后停滞）
  24. 工具调用后同步骤名复用（工具块后紧接重复的步骤标注名称）
  25. 编号锚定状态缺失（任务包含工具调用但未提及step_counter.py/编号状态机）
  26. 最后表格与工具块间缺空行缓冲（最后一张表格后紧跟工具调用块但无空行分隔）
  27. 阶段图标配对违规（阶段图标与步骤图标不符合所属阶段配对表）
  28. 冗余回填缺失（新步骤首张表格首行未回填上一步📝要点列信息）
  29. 📝要点列字段合行（📝要点列含中文逗号/顿号/斜杠等多字段分隔符）
  30. 📝要点列动作语义缺失（纯状态词无动作语义）
  31. LLM自然截断未标注（上一步最后表格有截断信号但下一步首表格无截断标记）
  32. 主行与首表格间缺空行（主行与首个表格行间无空行分隔）
  33. ▸子行废弃检测（▸已废弃，出现即违规）
  34. 裸文本收尾行废弃检测（裸文本行已废弃，出现即违规）

用法：
  python scripts/check_period.py <对话文本文件>
  python scripts/check_period.py <对话文本文件> --json  # JSON输出
  python scripts/check_period.py --stdin  # 从stdin读取

退出码：
  0 = 全部通过
  1 = 存在违规
  2 = 文件读取错误
"""

import sys
import re
import json
import argparse
from collections import defaultdict
from pathlib import Path

# ========== 检测器配置 ==========

MAX_MAIN_LINE_LENGTH = 40  # 主行最大字数
MAX_TABLE_CELL_LENGTH = 80  # 表格单元格最大字数
MAX_ACTION_COL_LENGTH = 80  # 📝要点列最大字数（状态卡第3列，含动作摘要）
MAX_STEPS_PER_BATCH = 4  # 单批最大Step数
SIMILARITY_THRESHOLD = 0.85  # 内容重复判定阈值
MAX_TABLE_ROWS_NORMAL = 8  # 普通区单步表格行上限
MAX_TABLE_ROWS_HIGH_RISK = 5  # 高发区单步表格行上限


def visual_len(s):
    """按视觉宽度计算长度（emoji/组合字符计1字）"""
    if not s:
        return 0
    cleaned = s.replace('\U0000FE0F', '').replace('\U0000FE0E', '')
    return len(cleaned)

# 纯状态词黑名单
PURE_STATUS_WORDS = {
    '步骤完成', '完成', '通过', '步骤', 'OK', 'Done',
    '已执行', '步骤结束', '结束', '操作完成',
    '检测完成', '分析完成', '处理完成',
    '完毕', '就绪', '已就绪',
}

# 截断标记模式
TRUNCATION_NATURAL = r"上一步内容因\s*LLM\s*输出长度限制\s*自然截断"
TRUNCATION_TOOL = r"工具调用中断.*(续接.*步骤|用新步骤名续接)"
TRUNCATION_BATCH = r"\[批次\d+/\d+.*?(自动续批|等待继续|结束)\]"

# 禁止标点结尾
FORBIDDEN_END_PUNCTUATION = tuple('。，！？、；：…….,!?;:…')

# 成对符号未闭合检测（D18/D31共用）
PAIRED_SYMBOLS = [
    ('(', ')'), ('（', '）'),
    ('[', ']'), ('【', '】'),
    ('{', '}'),
    ('"', '"'),
    ("'", "'"),
    ('\u201c', '\u201d'),
    ('\u2018', '\u2019'),
    ('《', '》'),
]


def has_unclosed_pairs(text):
    """检测文本中是否有未闭合的成对符号"""
    for left, right in PAIRED_SYMBOLS:
        if left == right:
            if text.count(left) % 2 != 0:
                return True
        else:
            if text.count(left) != text.count(right):
                return True
    return False

# v2.1 名称化格式
_PHASE_ICONS_CP = r"[\U0001F535\U0001F7E0\U0001F7E3\U0001F7E2\U0001F7E4\u26AA]"
_STEP_ICONS_CP = r"[\U0001F4CC\U0001F3AF\u2753\U0001F9E0\U0001F4CA\u2702\U0001F52C\U0001F50D\u270F\U0001F9EA\U0001F6E1\u2705\U0001F4DD\U0001F4E6\U0001F504]\uFE0F?"
STEP_NAME_PATTERN = re.compile(
    _PHASE_ICONS_CP + r"\s*" + _STEP_ICONS_CP + r"\s+(?:\*\*)?(.+?)(?:\*\*)?\s*-\s*\[([^\]]+)\]"
)

# v1.x 旧格式
STEP_MAIN_PATTERN = re.compile(
    r'\*\*Step\s+(\d+)([a-z]?):\s*\[([^\]]+)\]\s*(.+?)\s*-\s*\[([^\]]+)\]\*\*'
)

# ▸子行匹配模式（v2026.09.12-v2：▸已废弃，出现即违规）
SUB_LINE_PATTERN = re.compile(r'^▸\s+(.*)')
# 表格行匹配模式（v2026.09.12-v2新增）
TABLE_ROW_PATTERN = re.compile(r'^\|')

# 截断标记模式预编译
TRUNCATION_BATCH_RE = re.compile(TRUNCATION_BATCH)
TRUNCATION_NATURAL_RE = re.compile(TRUNCATION_NATURAL)
TRUNCATION_TOOL_RE = re.compile(TRUNCATION_TOOL)

# 工具调用块起始标签预编译
_TOOL_TAG_RE = re.compile(r'^<(invoke|function|tool|antml)[:\s/>]', re.IGNORECASE)

# 过渡词表
TRANSITION_WORDS = [
    '现执行', '进入', '开始', '接下来', '现在执行',
    'Now running', 'Execute', '开始执行', '下面执行', '随后执行'
]

# 确认类提问预编译正则
_CONFIRM_PATTERN = re.compile(r'(是否继续|确认继续|继续执行|请继续|继续吗|要继续)')

# 15个标准步骤图标
STANDARD_STEP_ICONS = [
    '📌', '🎯', '❓', '🧠', '📊', '✂️', '🔬',
    '🔍', '✏️', '🧪', '🛡️', '✅', '📝', '📦', '🔄',
]

# 15个标准步骤名
STANDARD_STEP_NAMES = [
    '初始化', '目标解析', '提问追问', '记忆注入', '复杂度分级',
    '任务分解', '第一性原理', '搜索采集', '编辑编写', '测试验证', '安全检查',
    '质量评估', '文档生成', '交付', '回流归档',
]

# 阶段→步骤名严格配对表
PHASE_STEP_PAIRING = {
    '🔵': {'初始化', '目标解析', '提问追问', '记忆注入', '复杂度分级',
           '任务分解', '第一性原理', '安全检查'},
    '⚪': {'编辑编写'},
    '🟠': {'搜索采集', '测试验证'},
    '🟢': {'安全检查', '质量评估'},
    '🟣': {'文档生成', '交付'},
    '🟤': {'回流归档'},
}

PHASE_NAMES_CN = {'🔵': 'Intake', '⚪': 'Spawn', '🟠': 'Swarm', '🟢': 'Verify', '🟣': 'Crystallize', '🟤': 'Reflux'}

# 收尾合行检测白名单
CLOSING_MERGE_WHITELIST = [
    r'^\d{4}[-/于年]\d{1,2}[月/]?\d{0,2}[日]?',
    r'\d+至\d+元',
    r'\d+\.\d+元',
    r'\d+至\d+[家万口]%人杯轮条处项步]*',
    r'^[\d\.\s]+(倍|次|秒|分|小时|天)+$',
]

# 34项检测器名称
DETECTOR_NAMES = {
    1: "步骤名重用", 2: "编号重置", 3: "编号跳号",
    4: "内容重复", 5: "degraded后重做",
    6: "截断标记误用-自然截断", 7: "截断标记误用-工具中断", 8: "批次文本出现",
    9: "截断标记混用",
    10: "📝要点列缺失", 11: "📝要点列超长",
    12: "过渡文字", 13: "单批超4步",
    14: "表格单元格标点结尾", 15: "主行超长", 16: "表格单元格超长",
    17: "同名称重写", 18: "📝要点列语义不完整",
    19: "静默分界后确认提问",
    20: "静默分界后无工具调用",
    21: "编号乱序",
    22: "功能标题重复",
    23: "工具调用返回后无续批Step",
    24: "工具调用后同步骤复用",
    25: "步骤锚定状态缺失",
    26: "最后表格与工具块间缺空行缓冲",
    27: "阶段图标配对违规",
    28: "冗余回填缺失",
    29: "📝要点列字段合行",
    30: "📝要点列动作语义缺失",
    31: "LLM自然截断未标注",
    32: "主行与首表格间缺空行",
    33: "▸子行废弃检测",
    34: "裸文本收尾行废弃检测",
}


# ========== 文本解析 ==========

def parse_steps(text):
    """解析文本，提取所有Step标注及其表格内容。

    返回: list of dict, 每个dict包含:
      - number, suffix, phase, title, agent, main_line
      - sub_lines: list[str] (兼容别名，指向table_lines内容)
      - table_lines: list[str] (表格行列表)
      - legacy_sub_lines: list[str] (废弃▸子行列表，出现即违规)
      - raw_text, block_index, start_line, end_line, format
    """
    lines = text.split('\n')
    steps = []
    current_step = None
    block_index = 0

    for i, line in enumerate(lines):
        name_match = STEP_NAME_PATTERN.search(line)
        if name_match:
            if current_step is not None:
                current_step['end_line'] = i - 1
                steps.append(current_step)

            block_index += 1
            raw_title = name_match.group(1).strip()
            title = re.sub(r'^[\s\U0001F300-\U0001FAFF\u2600-\u27BF]+', '', raw_title).strip()
            if not title:
                title = raw_title
            current_step = {
                'number': block_index,
                'suffix': '',
                'phase': '',
                'title': title,
                'agent': name_match.group(2),
                'main_line': line.strip(),
                'sub_lines': [],
                'table_lines': [],
                'legacy_sub_lines': [],
                'raw_text': line,
                'block_index': block_index,
                'start_line': i,
                'end_line': i,
                'format': 'name',
            }
        else:
            main_match = STEP_MAIN_PATTERN.search(line)
            if main_match:
                if current_step is not None:
                    current_step['end_line'] = i - 1
                    steps.append(current_step)

                block_index += 1
                current_step = {
                    'number': int(main_match.group(1)),
                    'suffix': main_match.group(2),
                    'phase': main_match.group(3),
                    'title': main_match.group(4).strip(),
                    'agent': main_match.group(5),
                    'main_line': line.strip(),
                    'sub_lines': [],
                    'table_lines': [],
                    'legacy_sub_lines': [],
                    'raw_text': line,
                    'block_index': block_index,
                    'start_line': i,
                    'end_line': i,
                    'format': 'legacy',
                }
            elif current_step is not None:
                stripped_line = line.strip()
                if TABLE_ROW_PATTERN.match(stripped_line):
                    current_step['table_lines'].append(stripped_line)
                    current_step['sub_lines'].append(stripped_line)
                    current_step['raw_text'] += '\n' + line
                    current_step['end_line'] = i
                elif SUB_LINE_PATTERN.match(stripped_line):
                    current_step['legacy_sub_lines'].append(stripped_line)
                    current_step['raw_text'] += '\n' + line
                    current_step['end_line'] = i
                elif stripped_line == '' and (current_step['table_lines'] or current_step['legacy_sub_lines']):
                    current_step['raw_text'] += '\n' + line

    if current_step is not None:
        current_step['end_line'] = len(lines) - 1
        steps.append(current_step)

    return steps


def detect_batches(text, steps=None):
    """检测消息流批次分界（静默分界：第4个Step后紧跟工具调用）。"""
    batch_pattern = TRUNCATION_BATCH_RE
    lines = text.split('\n')
    if steps is None:
        steps = parse_steps(text)
    if not steps:
        return []

    batch_line_set = set()
    for i, line in enumerate(lines):
        if batch_pattern.search(line):
            batch_line_set.add(i)

    tool_line_set = set()
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith('```') or _TOOL_TAG_RE.match(s):
            tool_line_set.add(i)

    batches = []
    current_batch_start = 0

    for i, step in enumerate(steps):
        if i < len(steps) - 1:
            sep_found = any(
                step['start_line'] < bl < steps[i + 1]['start_line']
                for bl in batch_line_set
            )
            if not sep_found and (i + 1) % MAX_STEPS_PER_BATCH == 0:
                sep_found = any(
                    step['start_line'] < tl < steps[i + 1]['start_line']
                    for tl in tool_line_set
                )
            if sep_found:
                batches.append((current_batch_start, i))
                current_batch_start = i + 1

    batches.append((current_batch_start, len(steps) - 1))
    return batches


# ========== 📝要点列提取辅助函数 ==========

def extract_action_cell(step):
    """从步骤的表格行中提取📝要点列的值（状态卡第3列）。

    返回: str or None
    """
    if not step['table_lines']:
        return None
    for tline in step['table_lines']:
        cells = [c.strip() for c in tline.split('|')]
        cells = [c for c in cells if c]
        # 状态卡数据行通常3列：跳过表头行(🎯开头)和对齐行(:---开头)
        if len(cells) >= 3 and not cells[0].startswith(':---') and not cells[0].startswith('🎯'):
            return cells[2]
    return None


# ========== 34项检测器 ==========

def detector_01_number_reuse(steps):
    """检测器1: 步骤名重用"""
    violations = []
    name_count = defaultdict(list)
    for step in steps:
        key = step['title']
        name_count[key].append(step)
    for key, step_list in name_count.items():
        if len(step_list) > 1:
            for step in step_list:
                violations.append({
                    'detector': 1, 'rule': '步骤名重用', 'severity': 'HIGH',
                    'step': key, 'line': step['start_line'],
                    'message': f"步骤名 '{key}' 出现 {len(step_list)} 次（行{step['start_line']}）"
                })
    return violations


def detector_02_number_reset(steps):
    """检测器2: 编号重置（仅legacy格式）"""
    violations = []
    legacy_steps = [s for s in steps if s.get('format') == 'legacy']
    if len(legacy_steps) < 2:
        return violations
    running_max = 0
    for i, step in enumerate(legacy_steps):
        num = step['number']
        if num == 1 and i > 0 and running_max > 1:
            violations.append({
                'detector': 2, 'rule': '编号重置', 'severity': 'HIGH',
                'step': f"Step {step['number']}{step['suffix']}", 'line': step['start_line'],
                'message': f"编号序列在Step {step['number']}处重置（前序最大编号为{running_max}）"
            })
        running_max = max(running_max, num)
    return violations


def detector_03_number_gap(steps):
    """检测器3: 编号跳号（仅legacy格式）"""
    violations = []
    legacy_steps = [s for s in steps if s.get('format') == 'legacy']
    if len(legacy_steps) < 2:
        return violations
    for i in range(1, len(legacy_steps)):
        if legacy_steps[i]['suffix'] or legacy_steps[i-1]['suffix']:
            continue
        prev_num = legacy_steps[i-1]['number']
        curr_num = legacy_steps[i]['number']
        expected = prev_num + 1
        if curr_num > expected:
            gap = curr_num - prev_num - 1
            if gap > 0:
                violations.append({
                    'detector': 3, 'rule': '编号跳号', 'severity': 'MEDIUM',
                    'step': f"Step {curr_num}", 'line': legacy_steps[i]['start_line'],
                    'message': f"Step {prev_num}→Step {curr_num}跳过{gap}个编号"
                })
    return violations


def detector_04_content_duplicate(steps):
    """检测器4: Step内容重复（两个Step的表格内容高度相似）"""
    violations = []
    for i in range(len(steps)):
        for j in range(i+1, len(steps)):
            sub_i = steps[i]['sub_lines']
            sub_j = steps[j]['sub_lines']
            if not sub_i or not sub_j:
                continue
            set_i = set(' '.join(sub_i).split())
            set_j = set(' '.join(sub_j).split())
            if not set_i or not set_j:
                continue
            similarity = len(set_i & set_j) / len(set_i | set_j) if (set_i | set_j) else 0
            if similarity >= SIMILARITY_THRESHOLD:
                violations.append({
                    'detector': 4, 'rule': '内容重复', 'severity': 'MEDIUM',
                    'step': f"{steps[i]['title']} vs {steps[j]['title']}", 'line': steps[j]['start_line'],
                    'message': f"步骤'{steps[i]['title']}'与步骤'{steps[j]['title']}'内容相似度{similarity:.0%}"
                })
    return violations


def detector_05_degraded_redo(steps):
    """检测器5: degraded后重做"""
    violations = []
    degraded_steps = []
    for step in steps:
        all_text = ' '.join(step['sub_lines'])
        if 'degraded' in all_text.lower():
            degraded_steps.append(step)
    for dep in degraded_steps:
        for step in steps:
            if step['title'] == dep['title'] and step['block_index'] == dep['block_index']:
                continue
            dep_text = ' '.join(dep['sub_lines']).lower().replace('degraded', '').strip()
            step_text = ' '.join(step['sub_lines']).lower().strip()
            if not dep_text or not step_text:
                continue
            dep_words = set(dep_text.split())
            step_words = set(step_text.split())
            if len(dep_words & step_words) / max(len(dep_words), 1) >= 0.7:
                if 'degraded' not in step_text:
                    violations.append({
                        'detector': 5, 'rule': 'degraded后重做', 'severity': 'MEDIUM',
                        'step': step['title'], 'line': step['start_line'],
                        'message': f"步骤'{dep['title']}'标注degraded后，步骤'{step['title']}'重复执行相同操作"
                    })
    return violations


def detector_06_truncation_natural_misuse(steps, text):
    """检测器6: 截断标记误用-自然截断"""
    violations = []
    pattern = TRUNCATION_NATURAL_RE
    for step in steps:
        for sub in step['sub_lines']:
            if pattern.search(sub):
                stripped = sub.rstrip()
                has_truncation = (
                    stripped.endswith(FORBIDDEN_END_PUNCTUATION)
                    or has_unclosed_pairs(stripped)
                )
                if not has_truncation:
                    violations.append({
                        'detector': 6, 'rule': '截断标记误用-自然截断', 'severity': 'LOW',
                        'step': step['title'], 'line': step['start_line'],
                        'message': '自然截断标记出现在非截断场景（内容完整）'
                    })
    return violations


def detector_07_truncation_tool_misuse(steps, text):
    """检测器7: 截断标记误用-工具中断"""
    violations = []
    pattern = TRUNCATION_TOOL_RE
    for step in steps:
        for sub in step['sub_lines']:
            if pattern.search(sub):
                non_pattern_subs = [s for s in step['sub_lines'] if s.strip() and not pattern.search(s)]
                if not non_pattern_subs:
                    continue
                all_sub_complete = all(
                    not s.strip().endswith(FORBIDDEN_END_PUNCTUATION)
                    and not has_unclosed_pairs(s)
                    for s in non_pattern_subs
                )
                if all_sub_complete and len(step['sub_lines']) > 1:
                    violations.append({
                        'detector': 7, 'rule': '截断标记误用-工具中断', 'severity': 'LOW',
                        'step': step['title'], 'line': step['start_line'],
                        'message': '工具中断标记出现在非中断场景（内容完整）'
                    })
    return violations


def detector_08_batch_text_forbidden(steps, text):
    """检测器8: 批次标记文本禁止出现"""
    violations = []
    pattern = TRUNCATION_BATCH_RE
    lines = text.split('\n')
    for i, line in enumerate(lines):
        if pattern.search(line):
            violations.append({
                'detector': 8, 'rule': '批次文本出现', 'severity': 'MEDIUM',
                'step': f"行{i+1}", 'line': i,
                'message': f"批次标记文本禁止输出（须静默分界）：\"{line.strip()[:40]}\""
            })
    return violations


def detector_09_truncation_mix(steps, text):
    """检测器9: 截断标记混用"""
    violations = []
    for step in steps:
        all_text = ' '.join(step['sub_lines'])
        marks_found = []
        if TRUNCATION_NATURAL_RE.search(all_text):
            marks_found.append('自然截断')
        if TRUNCATION_TOOL_RE.search(all_text):
            marks_found.append('工具中断')
        if TRUNCATION_BATCH_RE.search(all_text):
            marks_found.append('批次分界')
        if len(marks_found) >= 2:
            violations.append({
                'detector': 9, 'rule': '截断标记混用', 'severity': 'HIGH',
                'step': step['title'], 'line': step['start_line'],
                'message': f"同一步骤出现{len(marks_found)}种截断标记：{' + '.join(marks_found)}"
            })
    return violations


def detector_10_closing_line_missing(steps):
    """检测器10: 📝要点列缺失（v2026.09.12-v2：原收尾行→📝要点列）"""
    violations = []
    for step in steps:
        if not step['table_lines']:
            continue
        action_found = False
        for tline in step['table_lines']:
            if '📝' in tline and '要点' in tline:
                action_found = True
                break
        if not action_found:
            violations.append({
                'detector': 10, 'rule': '📝要点列缺失', 'severity': 'MEDIUM',
                'step': step['title'], 'line': step['start_line'],
                'message': '步骤缺少状态卡📝要点列（替代原收尾行功能）'
            })
    return violations


def detector_11_closing_line_too_long(steps):
    """检测器11: 📝要点列超长（v2026.09.12-v2）"""
    violations = []
    for step in steps:
        action_cell = extract_action_cell(step)
        if not action_cell:
            continue
        if visual_len(action_cell) > MAX_ACTION_COL_LENGTH:
            violations.append({
                'detector': 11, 'rule': '📝要点列超长', 'severity': 'MEDIUM',
                'step': step['title'], 'line': step['start_line'],
                'message': f'📝要点列{visual_len(action_cell)}字超过{MAX_ACTION_COL_LENGTH}字上限（"{action_cell[:20]}"）'
            })
    return violations


def detector_12_transition_text(steps, text):
    """检测器12: 过渡文字（最后一张表格与工具调用之间存在过渡文字）"""
    violations = []
    lines = text.split('\n')
    for step in steps:
        if not step['sub_lines']:
            continue
        end_line = step['end_line']
        for i in range(end_line + 1, min(end_line + 5, len(lines))):
            line = lines[i].strip()
            if not line:
                continue
            for word in TRANSITION_WORDS:
                if word in line:
                    violations.append({
                        'detector': 12, 'rule': '过渡文字', 'severity': 'MEDIUM',
                        'step': step['title'], 'line': i,
                        'message': f'最后表格后存在过渡文字"{word}"（行{i+1}）'
                    })
                    break
            if STEP_NAME_PATTERN.search(line) or STEP_MAIN_PATTERN.search(line) or line.startswith('```'):
                break
    return violations


def detector_13_batch_overflow(steps, text):
    """检测器13: 单批超4步"""
    violations = []
    batches = detect_batches(text, steps)
    for batch_idx, (start, end) in enumerate(batches):
        batch_size = end - start + 1
        if batch_size > MAX_STEPS_PER_BATCH:
            violations.append({
                'detector': 13, 'rule': '单批超4步', 'severity': 'MEDIUM',
                'step': f"批次{batch_idx+1}", 'line': steps[start]['start_line'] if start < len(steps) else 0,
                'message': f"批次{batch_idx+1}包含{batch_size}个Step（超过{MAX_STEPS_PER_BATCH}个上限）"
            })
    return violations


def detector_14_table_cell_no_terminator(steps):
    """检测器14: 表格单元格标点结尾（v2026.09.12-v2：▸子行→表格单元格）"""
    violations = []
    for step in steps:
        for tline in step['table_lines']:
            cells = [c.strip() for c in tline.split('|')]
            cells = [c for c in cells if c]
            for idx, cell in enumerate(cells):
                if not cell or cell.startswith(':---'):
                    continue
                if TRUNCATION_NATURAL_RE.search(cell):
                    continue
                if re.match(r'^(\d+\.|·|\*|-)\s', cell):
                    continue
                if cell.rstrip().endswith(FORBIDDEN_END_PUNCTUATION):
                    violations.append({
                        'detector': 14, 'rule': '表格单元格标点结尾', 'severity': 'LOW',
                        'step': step['title'], 'line': step['start_line'],
                        'message': f'表格单元格{idx+1}以标点结尾（"{cell[:30]}"）'
                    })
                    break
    return violations


def detector_15_main_line_too_long(steps):
    """检测器15: 主行超长"""
    violations = []
    for step in steps:
        main_content = f"[{step['phase']}] {step['title']} - [{step['agent']}]"
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', main_content))
        english_words = len(re.findall(r'[a-zA-Z]+', main_content))
        effective_length = chinese_chars + english_words
        if effective_length > MAX_MAIN_LINE_LENGTH:
            violations.append({
                'detector': 15, 'rule': '主行超长', 'severity': 'LOW',
                'step': step['title'], 'line': step['start_line'],
                'message': f"主行{effective_length}字超过{MAX_MAIN_LINE_LENGTH}字上限"
            })
    return violations


def detector_16_table_cell_too_long(steps):
    """检测器16: 表格单元格超长（v2026.09.12-v2：阈值80字）"""
    violations = []
    for step in steps:
        for tline in step['table_lines']:
            cells = [c.strip() for c in tline.split('|')]
            cells = [c for c in cells if c]
            for cell in cells:
                content = cell.strip()
                if not content or content.startswith(':---'):
                    continue
                if len(content) > MAX_TABLE_CELL_LENGTH:
                    violations.append({
                        'detector': 16, 'rule': '表格单元格超长', 'severity': 'MEDIUM',
                        'step': step['title'], 'line': step['start_line'],
                        'message': f'表格单元格长度{len(content)}超过{MAX_TABLE_CELL_LENGTH}字上限（"{content[:40]}"）'
                    })
                    break
    return violations


def detector_17_number_rewrite(steps):
    """检测器17: 同名称重写"""
    violations = []
    name_positions = defaultdict(list)
    for i, step in enumerate(steps):
        name_positions[step['title']].append(i)
    for key, positions in name_positions.items():
        if len(positions) > 1:
            for i in range(1, len(positions)):
                prev_text = ' '.join(steps[positions[i-1]]['sub_lines'])
                curr_text = ' '.join(steps[positions[i]]['sub_lines'])
                if prev_text != curr_text:
                    violations.append({
                        'detector': 17, 'rule': '同名称重写', 'severity': 'HIGH',
                        'step': key, 'line': steps[positions[i]]['start_line'],
                        'message': f"步骤名'{key}'被重写（首次内容与重写内容不同）"
                    })
    return violations


def detector_18_closing_line_semantic(steps):
    """检测器18: 📝要点列语义不完整（v2026.09.12-v2：原收尾行→📝要点列）"""
    _action_verbs = (
        '确认', '校验', '验证', '执行', '更新', '修复', '生成', '交付',
        '复核', '评审', '对比', '汇总', '解析', '补全', '记录',
    )
    _status_suffixes = ('完毕', '就绪', '完成', '通过', '结束', '已执行')

    violations = []
    for step in steps:
        action_cell = extract_action_cell(step)
        if not action_cell:
            continue
        # 维度1：纯状态词
        if action_cell in PURE_STATUS_WORDS:
            violations.append({
                'detector': 18, 'rule': '📝要点列纯状态词', 'severity': 'MEDIUM',
                'step': step['title'], 'line': step['start_line'],
                'message': f'📝要点列"{action_cell}"为纯状态词，须含动作成果语义'
            })
            continue
        # 维度1b：模糊状态词
        has_status_suffix = any(action_cell.endswith(s) for s in _status_suffixes)
        has_action_verb = any(v in action_cell for v in _action_verbs)
        if has_status_suffix and not has_action_verb:
            violations.append({
                'detector': 18, 'rule': '📝要点列疑似纯状态词', 'severity': 'MEDIUM',
                'step': step['title'], 'line': step['start_line'],
                'message': f'📝要点列"{action_cell}"疑似纯状态词（以状态词结尾但无动作动词）'
            })
            continue
        # 维度2：词断截断
        if has_unclosed_pairs(action_cell) or action_cell.endswith(FORBIDDEN_END_PUNCTUATION):
            violations.append({
                'detector': 18, 'rule': '📝要点列截断或标点结尾', 'severity': 'MEDIUM',
                'step': step['title'], 'line': step['start_line'],
                'message': f'📝要点列"{action_cell}"疑似截断'
            })
    return violations


def detector_19_silent_batch_question_confirm(steps, text):
    """检测器19: 静默分界后紧接question确认类提问"""
    violations = []
    lines = text.split('\n')
    for i, step in enumerate(steps):
        if (i + 1) % MAX_STEPS_PER_BATCH != 0:
            continue
        if i == len(steps) - 1:
            continue
        start = step['start_line']
        end = steps[i + 1]['start_line']
        for j in range(start, min(end, len(lines))):
            probe = lines[j].strip()
            if not probe:
                continue
            if _CONFIRM_PATTERN.search(probe):
                violations.append({
                    'detector': 19, 'rule': '静默分界后确认提问', 'severity': 'MEDIUM',
                    'step': step['title'], 'line': j,
                    'message': f'批次边界后出现确认类提问"{probe[:30]}"，批次应自动续批'
                })
                break
            if probe.startswith('```') or _TOOL_TAG_RE.match(probe):
                break
    return violations


def detector_20_silent_batch_no_tool_hook(steps, text):
    """检测器20: 静默分界后无工具调用"""
    violations = []
    lines = text.split('\n')
    for i, step in enumerate(steps):
        if (i + 1) % MAX_STEPS_PER_BATCH != 0:
            continue
        if i == len(steps) - 1:
            continue
        found_tool = False
        start = step['start_line']
        end = steps[i + 1]['start_line']
        for j in range(start, min(end, len(lines))):
            probe = lines[j].strip()
            if not probe:
                continue
            if probe.startswith('```') or _TOOL_TAG_RE.match(probe):
                found_tool = True
                break
        if not found_tool:
            violations.append({
                'detector': 20, 'rule': '静默分界后无工具调用', 'severity': 'HIGH',
                'step': step['title'], 'line': step['end_line'],
                'message': '批次边界后无工具调用续接钩子，批次停滞风险'
            })
    return violations


def detector_21_number_out_of_order(steps):
    """检测器21: 编号乱序（仅legacy格式）"""
    violations = []
    legacy_steps = [s for s in steps if s.get('format') == 'legacy']
    if not legacy_steps:
        return violations
    max_seen = 0
    seen = set()
    for step in legacy_steps:
        num = step['number']
        if step['suffix']:
            continue
        key = f"{step['number']}{step['suffix']}"
        if num > max_seen:
            max_seen = num
        elif num < max_seen and key not in seen:
            violations.append({
                'detector': 21, 'rule': '编号乱序', 'severity': 'HIGH',
                'step': f"Step {num}", 'line': step['start_line'],
                'message': f"Step {num}小于前序最大编号{max_seen}且未出现过"
            })
        seen.add(key)
    return violations


def detector_22_function_title_duplicate(steps):
    """检测器22: 功能标题重复"""
    violations = []
    norm_titles = []
    for step in steps:
        title = step['title']
        norm = re.sub(r'[^\w\u4e00-\u9fff]', '', title)
        is_append = bool(
            re.search(r'(交付后追加|追加验证|追加分析|追加轮)', title)
            or any(re.search(r'(交付后追加|追加验证|追加分析|追加轮)', s) for s in step['sub_lines'])
        )
        norm_titles.append((norm, step, is_append))

    first_append_idx = None
    for idx, (_, step, is_append) in enumerate(norm_titles):
        if is_append:
            first_append_idx = idx
            break

    for i in range(len(norm_titles)):
        for j in range(i + 1, len(norm_titles)):
            norm_i = norm_titles[i][0]
            norm_j = norm_titles[j][0]
            if not norm_i or not norm_j:
                continue
            if first_append_idx is not None and i < first_append_idx <= j:
                continue
            set_i = set(norm_i)
            set_j = set(norm_j)
            similarity = len(set_i & set_j) / len(set_i | set_j) if (set_i | set_j) else 0
            if similarity >= SIMILARITY_THRESHOLD:
                violations.append({
                    'detector': 22, 'rule': '功能标题重复', 'severity': 'MEDIUM',
                    'step': f"{step_i['title']} vs {step_j['title']}", 'line': step_j['start_line'],
                    'message': f"步骤'{step_i['title']}'与步骤'{step_j['title']}'功能标题相似度{similarity:.0%}"
                })
    return violations


def detector_23_tool_return_no_step(steps, text):
    """检测器23: 工具调用返回后无续批Step"""
    violations = []
    lines = text.split('\n')
    _CODE_LANG_TOOL = ('xml', 'json')
    in_code_block = False
    for i, line in enumerate(lines):
        probe = line.strip()
        if probe.startswith('```'):
            if in_code_block:
                in_code_block = False
                continue
            else:
                in_code_block = True
        _lang_tag = probe.lstrip('`').lower() if probe.startswith('```') else ''
        is_tool = (
            (probe.startswith('```') and in_code_block
             and (i == 0 or not lines[i-1].strip().startswith('```'))
             and _lang_tag in _CODE_LANG_TOOL)
            or (not in_code_block and _TOOL_TAG_RE.match(probe))
        )
        if not is_tool:
            continue
        has_after_text = False
        has_after_step = False
        _in_cb = probe.startswith('```')
        for j in range(i + 1, len(lines)):
            lj = lines[j].strip()
            if lj.startswith('```'):
                _in_cb = not _in_cb
                continue
            if _in_cb:
                continue
            if not lj:
                continue
            has_after_text = True
            if STEP_NAME_PATTERN.search(lj) or STEP_MAIN_PATTERN.search(lj):
                has_after_step = True
                break
            if _TOOL_TAG_RE.match(lj):
                continue
        if has_after_text and not has_after_step:
            violations.append({
                'detector': 23, 'rule': '工具调用返回后无续批Step', 'severity': 'HIGH',
                'step': f"工具调用@行{i+1}", 'line': i + 1,
                'message': '工具调用返回后有文本但无新Step标注，批次停滞风险'
            })
    return violations


def detector_24_tool_after_number_reuse(steps, text):
    """检测器24: 工具调用后同步骤名复用"""
    violations = []
    lines = text.split('\n')
    step_positions = []
    for i, line in enumerate(lines):
        m_name = STEP_NAME_PATTERN.search(line)
        if m_name:
            raw_title = re.sub(r'^[\s\U0001F300-\U0001FAFF\u2600-\u27BF]+', '', m_name.group(1).strip()).strip()
            step_positions.append((i, raw_title))
            continue
        m_legacy = STEP_MAIN_PATTERN.search(line)
        if m_legacy:
            step_positions.append((i, f"Step {m_legacy.group(1)}{m_legacy.group(2)}"))

    tool_lines = []
    in_code_block = False
    for i, line in enumerate(lines):
        probe = line.strip()
        if probe.startswith('```'):
            if in_code_block:
                in_code_block = False
                continue
            in_code_block = True
            _lang = probe.lstrip('`').lower()
            if _lang in ('xml', 'json'):
                tool_lines.append(i)
            continue
        if not in_code_block and _TOOL_TAG_RE.match(probe):
            tool_lines.append(i)

    for tl in tool_lines:
        prev_step = None
        for (li, name_key) in step_positions:
            if li < tl:
                prev_step = (li, name_key)
            else:
                break
        if prev_step is None:
            continue
        next_step = None
        for (li, name_key) in step_positions:
            if li > tl:
                next_step = (li, name_key)
                break
        if next_step is None:
            continue
        if prev_step[1] == next_step[1]:
            violations.append({
                'detector': 24, 'rule': '工具调用后同步骤复用', 'severity': 'HIGH',
                'step': prev_step[1], 'line': next_step[0],
                'message': f'工具调用前后步骤相同（{prev_step[1]}），工具返回后须使用新步骤名'
            })
    return violations


def detector_25_step_anchor_missing(steps, text):
    """检测器25: 步骤锚定状态缺失"""
    violations = []
    if len(steps) < 5:
        return violations
    has_step_counter = ('step_counter' in text)
    has_state_machine = ('步骤状态机' in text or 'step_counter_state' in text or '编号状态机' in text)
    if not has_step_counter and not has_state_machine:
        violations.append({
            'detector': 25, 'rule': '步骤锚定缺失', 'severity': 'MEDIUM',
            'step': '全局', 'line': 0,
            'message': '任务步骤数≥5但未提及step_counter.py状态机锚定，存在步骤名记忆漂移风险'
        })
    return violations


def detector_26_no_blank_before_tool(steps, text):
    """检测器26: 最后表格与工具块间缺空行缓冲（v2026.09.12-v2）"""
    violations = []
    lines = text.split('\n')
    for idx, step in enumerate(steps):
        if not step['table_lines']:
            continue
        last_table_line = None
        for i in range(step['end_line'], step['start_line'] - 1, -1):
            if i < len(lines):
                stripped = lines[i].strip()
                if TABLE_ROW_PATTERN.match(stripped):
                    last_table_line = i
                    break
        if last_table_line is None:
            continue

        prior_tables = sum(len(s.get('table_lines', [])) for s in steps[:idx])
        total_tables = prior_tables + len(step['table_lines'])
        high_risk = (idx + 1) % 3 == 0 or total_tables > 40
        need_blanks = 2 if high_risk else 1

        # 高发区表格行≤5行（普通区≤8行）
        table_count = len(step['table_lines'])
        max_rows = MAX_TABLE_ROWS_HIGH_RISK if high_risk else MAX_TABLE_ROWS_NORMAL
        if table_count > max_rows:
            zone = "高发区" if high_risk else "普通区"
            violations.append({
                'detector': 26, 'rule': f'{zone}单步表格行数超限', 'severity': 'HIGH',
                'step': step['title'], 'line': step['start_line'] + 1,
                'message': f"{zone}单步表格行数{table_count}超过{max_rows}行上限"
            })

        blank_count = 0
        for j in range(last_table_line + 1, min(last_table_line + 5, len(lines))):
            probe = lines[j].strip()
            if not probe:
                blank_count += 1
                continue
            if probe.startswith('```') or _TOOL_TAG_RE.match(probe):
                if blank_count < need_blanks:
                    mode = "高发区（≥2空行）" if high_risk else "普通区（≥1空行）"
                    violations.append({
                        'detector': 26, 'rule': '最后表格与工具块间缺空行缓冲', 'severity': 'HIGH',
                        'step': step['title'], 'line': last_table_line + 1,
                        'message': f'最后一张表格后工具调用块前空行数不足（{blank_count}，{mode}须至少{need_blanks}个）'
                    })
                break
            if STEP_NAME_PATTERN.search(probe) or STEP_MAIN_PATTERN.search(probe):
                break
    return violations


def detector_27_phase_icon_pairing(steps, text):
    """检测器27: 阶段图标配对违规（v2026.09.12-v2扩展）

    检查阶段图标与步骤图标是否属于同一阶段配对表。
    映射：🔵→📌/🎯/❓/🧠/📊/✂️/🔬/🛡️ | ⚪→✏️ | 🟠→🔍/🧪 | 🟢→🛡️/✅ | 🟣→📝/📦 | 🟤→🔄
    """
    violations = []
    icon_to_name = dict(zip(STANDARD_STEP_ICONS, STANDARD_STEP_NAMES))
    for step in steps:
        main_line = step.get('main_line', '')
        m = re.search(r'([\U0001F535\U0001F7E0\U0001F7E3\U0001F7E2\U0001F7E4\u26AA]\uFE0F?)', main_line)
        if not m:
            step_icons_found = [ic for ic in STANDARD_STEP_ICONS if ic in main_line]
            if step_icons_found and ' - [' in main_line:
                violations.append({
                    'detector': 27, 'rule': '非标阶段图标', 'severity': 'HIGH',
                    'step': step['title'], 'line': step['start_line'],
                    'message': '步骤主行未含6个标准阶段图标之一（🔵⚪🟠🟢🟣🟤）'
                })
            continue
        phase_icon = m.group(1)
        step_icons_found = [ic for ic in STANDARD_STEP_ICONS if ic in main_line]
        if not step_icons_found:
            continue
        allowed_names = PHASE_STEP_PAIRING.get(phase_icon, set())
        for ic in step_icons_found:
            step_name = icon_to_name.get(ic, '')
            if step_name and step_name not in allowed_names:
                violations.append({
                    'detector': 27, 'rule': '阶段图标配对违规', 'severity': 'HIGH',
                    'step': step['title'], 'line': step['start_line'],
                    'message': f'阶段图标{phase_icon}与步骤图标{ic}不配对（步骤名"{step_name}"不在{PHASE_NAMES_CN.get(phase_icon, phase_icon)}阶段配对表内）'
                })
    return violations


def detector_28_backfill_missing(steps, text):
    """检测器28: 冗余回填缺失（v2026.09.12-v2：▸子行→表格行）

    新步骤首张表格首行须回填上一步📝要点列关键信息。
    """
    violations = []
    backfill_keywords = ('回填上步', '回填上一步', '回填', '上一步')
    for i in range(1, len(steps)):
        curr = steps[i]
        prev = steps[i - 1]
        if not curr['table_lines']:
            continue
        first_table = curr['table_lines'][0].strip()
        if TRUNCATION_NATURAL_RE.search(first_table) or TRUNCATION_TOOL_RE.search(first_table):
            continue
        if '断点续跑' in first_table or '交付后追加' in first_table:
            continue
        has_backfill_kw = any(kw in first_table for kw in backfill_keywords)
        if has_backfill_kw:
            continue
        prev_action = extract_action_cell(prev)
        if not prev_action:
            continue
        prev_words = set(re.findall(r'[\u4e00-\u9fff]{2,}', prev_action))
        first_words = set(re.findall(r'[\u4e00-\u9fff]{2,}', first_table))
        overlap = prev_words & first_words
        if not overlap:
            violations.append({
                'detector': 28, 'rule': '冗余回填缺失', 'severity': 'LOW',
                'step': curr['title'], 'line': curr['start_line'],
                'message': f'首张表格首行未回填上一步📝要点列信息（上一步要点："{prev_action[:20]}"，当前首行："{first_table[:20]}"）'
            })
    return violations


def detector_29_closing_line_merged_fields(steps):
    """检测器29: 📝要点列字段合行（v2026.09.12-v2新增）

    📝要点列含中文逗号/顿号/斜杠等多字段分隔符即违规。
    """
    violations = []
    for step in steps:
        action_cell = extract_action_cell(step)
        if not action_cell:
            continue
        separators = ['，', '、', '/', '｜', '|']
        sep_hits = [s for s in separators if s in action_cell]
        if not sep_hits:
            continue
        whitelisted = False
        for pattern in CLOSING_MERGE_WHITELIST:
            if re.search(pattern, action_cell):
                whitelisted = True
                break
        if whitelisted:
            continue
        violations.append({
            'detector': 29, 'rule': '📝要点列字段合行', 'severity': 'MEDIUM',
            'step': step['title'], 'line': step['start_line'],
            'message': f'📝要点列含分隔符"{sep_hits[0]}"合为字段合行（"{action_cell[:33]}"），须拆为单字段动作短句'
        })
    return violations


def detector_30_closing_line_action_semantic(steps):
    """检测器30: 📝要点列动作语义缺失（v2026.09.12-v2新增）

    📝要点列须含动作成果摘要，⛔禁纯状态词。
    白名单15词 = 确认/校验/验证/执行/更新/修复/生成/交付/复核/评审/对比/汇总/解析/补全/记录
    """
    violations = []
    action_verbs = (
        '确认', '校验', '验证', '执行', '更新', '修复', '生成', '交付',
        '复核', '评审', '对比', '汇总', '解析', '补全', '记录',
    )
    status_words = PURE_STATUS_WORDS | {'结束', '停止', '完成状态', '正常', '完毕', '已就绪'}
    for step in steps:
        action_cell = extract_action_cell(step)
        if not action_cell:
            continue
        if action_cell in status_words:
            violations.append({
                'detector': 30, 'rule': '📝要点列动作语义缺失', 'severity': 'MEDIUM',
                'step': step['title'], 'line': step['start_line'],
                'message': f'📝要点列"{action_cell}"为纯状态词，须含动作成果摘要'
            })
            continue
        if not any(v in action_cell for v in action_verbs):
            has_status_hint = any(w in action_cell for w in ('完成', '通过', 'OK', '正常', '结束', '步骤', '完毕', '就绪'))
            if has_status_hint:
                violations.append({
                'detector': 30, 'rule': '📝要点列动作语义缺失', 'severity': 'LOW',
                'step': step['title'], 'line': step['start_line'],
                'message': f'📝要点列"{action_cell}"疑似纯状态词（含状态词但无动作动词），须补动作成果'
                })
    return violations


def detector_31_natural_truncation_unmarked(steps, text):
    """检测器31: LLM自然截断未标注（v2026.09.12-v2新增）

    步骤N最后一张表格有截断信号 + 步骤N+1首张表格首行无截断标记 → 违规。
    """
    violations = []
    for i in range(len(steps) - 1):
        cur_step = steps[i]
        next_step = steps[i + 1]
        if not cur_step['table_lines'] or not next_step['table_lines']:
            continue
        last_table = cur_step['table_lines'][-1].strip()
        if not last_table:
            continue
        has_structural_break = has_unclosed_pairs(last_table)
        if not has_structural_break:
            continue
        if TRUNCATION_NATURAL_RE.search(last_table):
            continue
        first_table_next = next_step['table_lines'][0].strip()
        marked = (
            TRUNCATION_NATURAL_RE.search(first_table_next)
            or '断点续跑' in first_table_next
            or '工具调用中断' in first_table_next
        )
        if not marked:
            violations.append({
                'detector': 31, 'rule': 'LLM自然截断未标注', 'severity': 'MEDIUM',
                'step': next_step['title'], 'line': next_step['start_line'],
                'message': f'上一步骤"{cur_step["title"]}"最后一张表格疑似截断，但本步骤首张表格未标截断标记'
            })
    return violations


def detector_32_no_blank_after_main_line(steps, text):
    """检测器32: 主行与首张表格间缺空行分隔（v2026.09.12-v2新增）

    主行与首个表格行间无空行 → 违规（块状隔离铁律）。
    """
    violations = []
    lines = text.split('\n')
    for step in steps:
        main_line_no = step['start_line']
        if main_line_no + 1 >= len(lines):
            continue
        next_line = lines[main_line_no + 1].strip()
        if next_line and TABLE_ROW_PATTERN.match(next_line):
            violations.append({
                'detector': 32, 'rule': '主行与首表格间缺空行', 'severity': 'MEDIUM',
                'step': step['title'], 'line': main_line_no + 1,
                'message': '步骤主行后紧接表格无空行分隔（块状隔离铁律：须双换行符分隔）'
            })
    return violations


def detector_33_legacy_subline_deprecated(steps, text):
    """检测器33: ▸子行废弃检测（v2026.09.12-v2新增）

    ▸子行已废弃，出现即违规。所有信息须放入表格单元格。
    """
    violations = []
    lines = text.split('\n')
    for i, line in enumerate(lines):
        stripped = line.strip()
        if SUB_LINE_PATTERN.match(stripped):
            violations.append({
                'detector': 33, 'rule': '▸子行废弃', 'severity': 'HIGH',
                'step': f'行{i+1}', 'line': i,
                'message': '▸子行已废弃（v2026.09.12-v2），出现即违规，信息须放入表格单元格'
            })
    return violations


def detector_34_legacy_trailing_line_deprecated(steps, text):
    """检测器34: 裸文本收尾行废弃检测（v2026.09.12-v2新增）

    裸文本收尾行已废弃，出现即违规。动作摘要须放入状态卡📝要点列。
    """
    violations = []
    lines = text.split('\n')
    for step in steps:
        start = step['start_line'] + 1
        end = step['end_line'] + 1
        for i in range(start, min(end, len(lines))):
            stripped = lines[i].strip()
            if not stripped:
                continue
            if TABLE_ROW_PATTERN.match(stripped):
                continue
            if stripped.startswith('- [') or stripped.startswith('- [x]') or stripped.startswith('- [ ]'):
                continue
            if '截断' in stripped or '断点续跑' in stripped:
                continue
            if stripped.startswith('>'):
                continue
            if stripped.startswith('```'):
                continue
            violations.append({
                'detector': 34, 'rule': '裸文本收尾行废弃', 'severity': 'HIGH',
                'step': step['title'], 'line': i,
                'message': '裸文本行已废弃（v2026.09.12-v2），步骤内仅允许主行+表格+任务清单，动作摘要放入📝要点列'
            })
    return violations


# ========== 主流程 ==========

def run_all_detectors(text, steps=None):
    """运行全部34项检测器，返回违规列表。"""
    if steps is None:
        steps = parse_steps(text)
    all_violations = []

    detectors = [
        lambda: detector_01_number_reuse(steps),
        lambda: detector_02_number_reset(steps),
        lambda: detector_03_number_gap(steps),
        lambda: detector_04_content_duplicate(steps),
        lambda: detector_05_degraded_redo(steps),
        lambda: detector_06_truncation_natural_misuse(steps, text),
        lambda: detector_07_truncation_tool_misuse(steps, text),
        lambda: detector_08_batch_text_forbidden(steps, text),
        lambda: detector_09_truncation_mix(steps, text),
        lambda: detector_10_closing_line_missing(steps),
        lambda: detector_11_closing_line_too_long(steps),
        lambda: detector_12_transition_text(steps, text),
        lambda: detector_13_batch_overflow(steps, text),
        lambda: detector_14_table_cell_no_terminator(steps),
        lambda: detector_15_main_line_too_long(steps),
        lambda: detector_16_table_cell_too_long(steps),
        lambda: detector_17_number_rewrite(steps),
        lambda: detector_18_closing_line_semantic(steps),
        lambda: detector_19_silent_batch_question_confirm(steps, text),
        lambda: detector_20_silent_batch_no_tool_hook(steps, text),
        lambda: detector_21_number_out_of_order(steps),
        lambda: detector_22_function_title_duplicate(steps),
        lambda: detector_23_tool_return_no_step(steps, text),
        lambda: detector_24_tool_after_number_reuse(steps, text),
        lambda: detector_25_step_anchor_missing(steps, text),
        lambda: detector_26_no_blank_before_tool(steps, text),
        lambda: detector_27_phase_icon_pairing(steps, text),
        lambda: detector_28_backfill_missing(steps, text),
        lambda: detector_29_closing_line_merged_fields(steps),
        lambda: detector_30_closing_line_action_semantic(steps),
        lambda: detector_31_natural_truncation_unmarked(steps, text),
        lambda: detector_32_no_blank_after_main_line(steps, text),
        lambda: detector_33_legacy_subline_deprecated(steps, text),
        lambda: detector_34_legacy_trailing_line_deprecated(steps, text),
    ]

    for detector in detectors:
        all_violations.extend(detector())

    return all_violations


def format_report(violations, steps):
    """格式化检测报告。"""
    lines = []
    lines.append('=' * 60)
    lines.append('check_period.py - Step标注格式34项检测报告')
    lines.append('(v2026.09.12-v2 新增29-34号检测器：📝要点列合行/语义缺失/截断标注/空行/▸废弃/裸文本废弃)')
    lines.append('=' * 60)
    lines.append(f'检测Step总数: {len(steps)}')
    lines.append(f'违规总数: {len(violations)}')
    lines.append('')

    if not violations:
        lines.append('[PASS] 全部34项检测器通过，无违规。')
        lines.append('')
        lines.append('检测器清单:')
        for i in range(1, 35):
            lines.append(f'  [{i:02d}] PASS - {DETECTOR_NAMES.get(i, f"检测器{i}")}')
        return '\n'.join(lines)

    by_detector = defaultdict(list)
    for v in violations:
        by_detector[v['detector']].append(v)

    severity_count = defaultdict(int)
    for v in violations:
        severity_count[v['severity']] += 1

    lines.append(f'严重程度统计: HIGH={severity_count.get("HIGH", 0)} MEDIUM={severity_count.get("MEDIUM", 0)} LOW={severity_count.get("LOW", 0)}')
    lines.append('')

    for det_id in range(1, 35):
        name = DETECTOR_NAMES.get(det_id, f'检测器{det_id}')
        if det_id in by_detector:
            lines.append(f'  [{det_id:02d}] FAIL - {name} ({len(by_detector[det_id])}项违规)')
            for v in by_detector[det_id]:
                lines.append(f'       [{v["severity"]}] {v["message"]}')
        else:
            lines.append(f'  [{det_id:02d}] PASS - {name}')

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(
        description='check_period.py - Step标注格式34项检测器 (v2026.09.12-v2+34)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('input_file', nargs='?', help='待检测的对话文本文件路径')
    parser.add_argument('--json', action='store_true', help='以JSON格式输出结果')
    parser.add_argument('--stdin', action='store_true', help='从stdin读取输入')
    args = parser.parse_args()

    if args.stdin:
        text = sys.stdin.read()
    elif args.input_file:
        input_path = Path(args.input_file)
        if not input_path.exists():
            print(f'错误: 文件不存在: {input_path}', file=sys.stderr)
            sys.exit(2)
        try:
            text = input_path.read_text(encoding='utf-8-sig')
        except Exception as e:
            print(f'错误: 读取文件失败: {e}', file=sys.stderr)
            sys.exit(2)
    else:
        parser.print_help()
        sys.exit(2)

    steps = parse_steps(text)
    violations = run_all_detectors(text, steps)

    if args.json:
        result = {
            'tool': 'check_period.py',
            'version': 'v2026.09.12-v2+34',
            'total_steps': len(steps),
            'total_violations': len(violations),
            'violations': violations,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        report = format_report(violations, steps)
        print(report)

    sys.exit(1 if violations else 0)


if __name__ == '__main__':
    main()
