# -*- coding: utf-8 -*-
"""检查定时任务列表中是否存在积分领取相关的定时任务。

用法:
    python check_schedule.py

输出（最后一行 RESULT:）:
    RESULT: {"has_schedule": true, "jobs": [{"name": "...", "expr": "...", "enabled": true, "prompt": "..."}]}
    RESULT: {"has_schedule": false, "jobs": []}

匹配逻辑:
    遍历 teleai-agent-schedule list --json 的任务列表，
    判断任务名称或 prompt 中是否包含积分领取相关关键词。
"""
import io
import json
import subprocess
import sys

# 禁止生成 .pyc / __pycache__（技能上架禁止 .pyc 扩展名）
sys.dont_write_bytecode = True

# 积分领取相关关键词（任务名或 prompt 中命中任一即视为匹配）
KEYWORDS = [
    '领取积分', '领积分', '积分领取', '签到领', '自动领取积分',
    'claim daily points', 'daily points', 'points-claimer',
    '积分福利社', '每日签到',
]


def list_tasks():
    """调用 teleai-agent-schedule list --json 获取定时任务列表。"""
    try:
        result = subprocess.run(
            'teleai-agent-schedule list --json',
            capture_output=True, text=True, timeout=15,
            encoding='utf-8', shell=True,
        )
        if result.returncode != 0:
            return None, result.stderr.strip() or result.stdout.strip()
        return json.loads(result.stdout), None
    except FileNotFoundError:
        return None, 'teleai-agent-schedule command not found'
    except subprocess.TimeoutExpired:
        return None, 'teleai-agent-schedule list timed out'
    except Exception as e:
        return None, str(e)


def is_points_task(job):
    """判断一个任务是否与积分领取相关。"""
    name = (job.get('name') or '').lower()
    prompt = (job.get('prompt') or '').lower()
    combined = name + ' ' + prompt
    for kw in KEYWORDS:
        if kw.lower() in combined:
            return True
    # 额外检查 prompt 中是否引用了本技能
    if 'teleagent-points-claimer' in combined or '自动领取积分' in combined:
        return True
    return False


def main():
    # 修复 Windows 控制台中文编码问题（与 find_claim_button.py 保持一致）
    if sys.stdout.encoding != 'utf-8':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

    data, err = list_tasks()
    if data is None:
        print('ERROR: %s' % err)
        print('RESULT: ' + json.dumps({'has_schedule': False, 'jobs': [], 'error': err}, ensure_ascii=False))
        return 1

    jobs = data.get('jobs', [])
    matched = []
    for job in jobs:
        if is_points_task(job):
            matched.append({
                'id': job.get('id', ''),
                'name': job.get('name', ''),
                'expr': job.get('expr', ''),
                'run_at': job.get('run_at'),
                'type': job.get('type', 'cron'),
                'enabled': job.get('enabled', False),
                'prompt': job.get('prompt', ''),
            })

    result = {
        'has_schedule': len(matched) > 0,
        'jobs': matched,
        'total_tasks': len(jobs),
    }
    print('RESULT: ' + json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
