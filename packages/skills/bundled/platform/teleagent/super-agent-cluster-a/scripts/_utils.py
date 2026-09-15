"""共享工具函数模块（v3.6.2新增）。

提取 step_counter.py / rule_shield.py 中的重复逻辑，消除手动同步需求。

包含：
  - atomic_write_json: 原子写入JSON文件（先写.tmp再os.replace）
"""

import json
import os


def atomic_write_json(path, data):
    """原子写入JSON文件：先写.tmp再os.replace，避免进程中断损坏。

    Args:
        path: 目标文件路径
        data: 要写入的dict/list数据

    Raises:
        OSError/TypeError/ValueError: 写入失败时抛出，.tmp文件已清理
    """
    dir_path = os.path.dirname(path)
    if dir_path:
        os.makedirs(dir_path, exist_ok=True)
    tmp_path = path + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
    except (OSError, TypeError, ValueError):
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except OSError:
            pass
        raise
