#!/usr/bin/env python3
"""磁盘垃圾文件清理脚本 - 根据用户确认的类别执行删除"""

import os
import sys
import json
import shutil
import argparse
import glob
from pathlib import Path
from datetime import datetime


def format_size(size_bytes):
    """将字节转换为可读格式"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def safe_remove_file(filepath):
    """安全删除单个文件"""
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            return True, None
    except (OSError, PermissionError) as e:
        return False, str(e)
    return False, "File not found"


def safe_remove_dir(dirpath):
    """安全删除目录内容（保留目录本身）"""
    removed = 0
    failed = 0
    errors = []

    if not os.path.exists(dirpath):
        return removed, failed, errors

    for dirpath_curr, dirnames, filenames in os.walk(dirpath, topdown=False):
        for f in filenames:
            fp = os.path.join(dirpath_curr, f)
            try:
                os.remove(fp)
                removed += 1
            except (OSError, PermissionError) as e:
                failed += 1
                errors.append(f"{fp}: {e}")

        for d in dirnames:
            dp = os.path.join(dirpath_curr, d)
            try:
                os.rmdir(dp)  # 仅删除空目录
            except (OSError, PermissionError):
                pass  # 非空目录不强制删除

    return removed, failed, errors


def clean_path(path_pattern, is_pattern=False):
    """清理指定路径或路径模式"""
    result = {
        "path": path_pattern,
        "removed_count": 0,
        "failed_count": 0,
        "freed_bytes": 0,
        "errors": []
    }

    if is_pattern or '*' in path_pattern:
        # 通配符模式
        for fp in glob.glob(path_pattern, recursive=True):
            if os.path.isfile(fp):
                try:
                    size = os.path.getsize(fp)
                    os.remove(fp)
                    result["removed_count"] += 1
                    result["freed_bytes"] += size
                except (OSError, PermissionError) as e:
                    result["failed_count"] += 1
                    result["errors"].append(f"{fp}: {e}")
    else:
        if os.path.isfile(path_pattern):
            try:
                size = os.path.getsize(path_pattern)
                os.remove(path_pattern)
                result["removed_count"] = 1
                result["freed_bytes"] = size
            except (OSError, PermissionError) as e:
                result["failed_count"] = 1
                result["errors"].append(f"{path_pattern}: {e}")
        elif os.path.isdir(path_pattern):
            # 先统计大小
            total_size = 0
            for dirpath, dirnames, filenames in os.walk(path_pattern):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    try:
                        total_size += os.path.getsize(fp)
                    except (OSError, PermissionError):
                        pass

            removed, failed, errors = safe_remove_dir(path_pattern)
            result["removed_count"] = removed
            result["failed_count"] = failed
            result["freed_bytes"] = total_size
            result["errors"] = errors

    result["freed_readable"] = format_size(result["freed_bytes"])
    return result


def clean_recycle_bin(drive_letter):
    """清空回收站（使用 Windows API）"""
    result = {
        "path": f"{drive_letter}\\$Recycle.Bin",
        "removed_count": 0,
        "failed_count": 0,
        "freed_bytes": 0,
        "errors": []
    }

    recycle_dir = os.path.join(drive_letter, "$Recycle.Bin")
    if os.path.exists(recycle_dir):
        removed, failed, errors = safe_remove_dir(recycle_dir)
        result["removed_count"] = removed
        result["failed_count"] = failed
        result["errors"] = errors

    result["freed_readable"] = format_size(result["freed_bytes"])
    return result


def main():
    parser = argparse.ArgumentParser(description='磁盘垃圾文件清理工具')
    parser.add_argument('--paths', nargs='*', default=[],
                        help='要清理的路径列表')
    parser.add_argument('--json', type=str, default=None,
                        help='从 JSON 文件读取清理路径')
    parser.add_argument('--categories', nargs='*', default=None,
                        help='指定清理类别 (同 disk_scan.py 的类别)')
    parser.add_argument('--drive', default='C', help='盘符')
    args = parser.parse_args()

    results = {
        "clean_time": datetime.now().isoformat(),
        "total_freed_bytes": 0,
        "total_removed": 0,
        "total_failed": 0,
        "items": []
    }

    paths_to_clean = []

    # 从 JSON 文件加载路径
    if args.json:
        try:
            with open(args.json, 'r', encoding='utf-8') as f:
                scan_data = json.load(f)
            for cat_key, cat_data in scan_data.get("categories", {}).items():
                for item in cat_data.get("items", []):
                    paths_to_clean.append({
                        "path": item["path"],
                        "is_pattern": '*' in item["path"]
                    })
        except Exception as e:
            print(json.dumps({"error": f"读取 JSON 文件失败: {e}"}, ensure_ascii=False))
            sys.exit(1)

    # 从命令行参数添加路径
    for p in args.paths:
        paths_to_clean.append({"path": p, "is_pattern": '*' in p})

    # 执行清理
    for item in paths_to_clean:
        path = item["path"]
        is_pattern = item.get("is_pattern", False)

        # 特殊处理回收站
        if '$Recycle.Bin' in path:
            drive = path[:2]
            r = clean_recycle_bin(drive)
        else:
            r = clean_path(path, is_pattern)

        results["items"].append(r)
        results["total_freed_bytes"] += r["freed_bytes"]
        results["total_removed"] += r["removed_count"]
        results["total_failed"] += r["failed_count"]

    results["total_freed_readable"] = format_size(results["total_freed_bytes"])

    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
