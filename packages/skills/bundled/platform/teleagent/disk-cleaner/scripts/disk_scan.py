#!/usr/bin/env python3
"""磁盘垃圾文件扫描脚本 - 扫描指定磁盘的各类垃圾文件并输出分类报告"""

import os
import sys
import json
import glob
import shutil
import argparse
from pathlib import Path
from datetime import datetime


def get_dir_size(path):
    """获取目录/文件大小（字节），无法访问返回0"""
    total = 0
    try:
        if os.path.isfile(path):
            total = os.path.getsize(path)
        elif os.path.isdir(path):
            for dirpath, dirnames, filenames in os.walk(path):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    try:
                        total += os.path.getsize(fp)
                    except (OSError, PermissionError):
                        pass
    except (OSError, PermissionError):
        pass
    return total


def count_files_in_dir(path):
    """统计目录下的文件数量"""
    count = 0
    try:
        if os.path.isfile(path):
            return 1
        for dirpath, dirnames, filenames in os.walk(path):
            count += len(filenames)
    except (OSError, PermissionError):
        pass
    return count


def format_size(size_bytes):
    """将字节转换为可读格式"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def scan_temp_files(drive):
    """扫描临时文件"""
    items = []

    # 用户临时目录
    user_temp = os.environ.get('TEMP', '')
    if user_temp and user_temp.startswith(drive):
        size = get_dir_size(user_temp)
        items.append({
            "path": user_temp,
            "description": "用户临时目录 (%TEMP%)",
            "size_bytes": size,
            "size_readable": format_size(size),
            "file_count": count_files_in_dir(user_temp),
            "safe_to_delete": True
        })

    # Windows 临时目录
    win_temp = os.path.join(drive, "Windows", "Temp")
    if os.path.exists(win_temp):
        size = get_dir_size(win_temp)
        items.append({
            "path": win_temp,
            "description": "Windows 临时目录",
            "size_bytes": size,
            "size_readable": format_size(size),
            "file_count": count_files_in_dir(win_temp),
            "safe_to_delete": True
        })

    return items


def scan_cache_files(drive):
    """扫描缓存文件"""
    items = []

    # 缩略图缓存
    thumbcache_dir = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'Windows', 'Explorer')
    if thumbcache_dir and os.path.exists(thumbcache_dir) and thumbcache_dir.startswith(drive):
        thumb_size = 0
        thumb_count = 0
        for f in os.listdir(thumbcache_dir):
            if f.lower().startswith('thumbcache'):
                fp = os.path.join(thumbcache_dir, f)
                try:
                    thumb_size += os.path.getsize(fp)
                    thumb_count += 1
                except (OSError, PermissionError):
                    pass
        if thumb_size > 0:
            items.append({
                "path": thumbcache_dir,
                "description": "缩略图缓存 (thumbcache_*)",
                "size_bytes": thumb_size,
                "size_readable": format_size(thumb_size),
                "file_count": thumb_count,
                "safe_to_delete": True
            })

    # pip 缓存
    pip_cache = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'pip', 'Cache')
    if pip_cache and os.path.exists(pip_cache) and pip_cache.startswith(drive):
        size = get_dir_size(pip_cache)
        if size > 0:
            items.append({
                "path": pip_cache,
                "description": "pip 缓存",
                "size_bytes": size,
                "size_readable": format_size(size),
                "file_count": count_files_in_dir(pip_cache),
                "safe_to_delete": True
            })

    # npm 缓存
    npm_cache = os.path.join(os.environ.get('APPDATA', ''), 'npm-cache')
    if npm_cache and os.path.exists(npm_cache) and npm_cache.startswith(drive):
        size = get_dir_size(npm_cache)
        if size > 0:
            items.append({
                "path": npm_cache,
                "description": "npm 缓存",
                "size_bytes": size,
                "size_readable": format_size(size),
                "file_count": count_files_in_dir(npm_cache),
                "safe_to_delete": True
            })

    # nuget 缓存
    nuget_cache = os.path.join(os.environ.get('USERPROFILE', ''), '.nuget', 'packages')
    if nuget_cache and os.path.exists(nuget_cache) and nuget_cache.startswith(drive):
        size = get_dir_size(nuget_cache)
        if size > 0:
            items.append({
                "path": nuget_cache,
                "description": "NuGet 包缓存",
                "size_bytes": size,
                "size_readable": format_size(size),
                "file_count": count_files_in_dir(nuget_cache),
                "safe_to_delete": True
            })

    # Windows 字体缓存
    fontcache_dir = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'Windows', 'FontCache')
    if fontcache_dir and os.path.exists(fontcache_dir) and fontcache_dir.startswith(drive):
        size = get_dir_size(fontcache_dir)
        if size > 0:
            items.append({
                "path": fontcache_dir,
                "description": "Windows 字体缓存",
                "size_bytes": size,
                "size_readable": format_size(size),
                "file_count": count_files_in_dir(fontcache_dir),
                "safe_to_delete": True
            })

    return items


def scan_log_files(drive):
    """扫描日志文件"""
    items = []

    # Windows 日志
    logs_dir = os.path.join(drive, "Windows", "Logs")
    if os.path.exists(logs_dir):
        size = get_dir_size(logs_dir)
        if size > 0:
            items.append({
                "path": logs_dir,
                "description": "Windows 系统日志",
                "size_bytes": size,
                "size_readable": format_size(size),
                "file_count": count_files_in_dir(logs_dir),
                "safe_to_delete": True
            })

    # 应用事件日志（受限，通常不大但可报告）
    winevt_logs = os.path.join(drive, "Windows", "System32", "winevt", "Logs")
    if os.path.exists(winevt_logs):
        size = get_dir_size(winevt_logs)
        if size > 0:
            items.append({
                "path": winevt_logs,
                "description": "Windows 事件日志",
                "size_bytes": size,
                "size_readable": format_size(size),
                "file_count": count_files_in_dir(winevt_logs),
                "safe_to_delete": False  # 不建议删除事件日志
            })

    # 用户 AppData 日志
    for root_name in ['Local', 'Roaming']:
        appdata_dir = os.environ.get(f'{root_name.upper()}APPDATA', '')
        if not appdata_dir:
            continue
        # 搜索常见日志子目录
        for log_candidate in ['Logs', 'log']:
            log_dir = os.path.join(appdata_dir, log_candidate)
            if os.path.exists(log_dir) and log_dir.startswith(drive):
                size = get_dir_size(log_dir)
                if size > 0:
                    items.append({
                        "path": log_dir,
                        "description": f"应用日志 ({root_name}\\{log_candidate})",
                        "size_bytes": size,
                        "size_readable": format_size(size),
                        "file_count": count_files_in_dir(log_dir),
                        "safe_to_delete": True
                    })

    # 扫描 *.log 文件在用户目录下的常见位置
    user_profile = os.environ.get('USERPROFILE', '')
    if user_profile and user_profile.startswith(drive):
        log_size = 0
        log_count = 0
        for pattern in [os.path.join(user_profile, '*.log'),
                        os.path.join(user_profile, 'AppData', '**', '*.log')]:
            for f in glob.glob(pattern, recursive=True):
                try:
                    log_size += os.path.getsize(f)
                    log_count += 1
                except (OSError, PermissionError):
                    pass
        if log_count > 0:
            items.append({
                "path": os.path.join(user_profile, '*.log'),
                "description": f"用户目录下的 .log 文件 ({log_count}个)",
                "size_bytes": log_size,
                "size_readable": format_size(log_size),
                "file_count": log_count,
                "safe_to_delete": True
            })

    return items


def scan_recycle_bin(drive):
    """扫描回收站"""
    items = []
    # Windows 回收站路径
    recycle_paths = [os.path.join(drive, '$Recycle.Bin')]
    for rp in recycle_paths:
        if os.path.exists(rp):
            size = get_dir_size(rp)
            if size > 0:
                items.append({
                    "path": rp,
                    "description": "回收站",
                    "size_bytes": size,
                    "size_readable": format_size(size),
                    "file_count": count_files_in_dir(rp),
                    "safe_to_delete": True
                })
    return items


def scan_windows_update_cache(drive):
    """扫描 Windows 更新缓存"""
    items = []
    ws_dir = os.path.join(drive, "Windows", "SoftwareDistribution", "Download")
    if os.path.exists(ws_dir):
        size = get_dir_size(ws_dir)
        if size > 0:
            items.append({
                "path": ws_dir,
                "description": "Windows 更新下载缓存",
                "size_bytes": size,
                "size_readable": format_size(size),
                "file_count": count_files_in_dir(ws_dir),
                "safe_to_delete": True
            })

    # Windows 旧安装文件
    win_old = os.path.join(drive, "Windows.old")
    if os.path.exists(win_old):
        size = get_dir_size(win_old)
        if size > 0:
            items.append({
                "path": win_old,
                "description": "Windows 旧系统文件 (Windows.old)",
                "size_bytes": size,
                "size_readable": format_size(size),
                "file_count": count_files_in_dir(win_old),
                "safe_to_delete": False  # 不自动删除，需用户明确确认
            })
    return items


def scan_error_reports(drive):
    """扫描系统错误报告"""
    items = []

    # WER (Windows Error Reporting)
    wer_dir = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'Windows', 'WER')
    if wer_dir and os.path.exists(wer_dir) and wer_dir.startswith(drive):
        size = get_dir_size(wer_dir)
        if size > 0:
            items.append({
                "path": wer_dir,
                "description": "Windows 错误报告 (WER)",
                "size_bytes": size,
                "size_readable": format_size(size),
                "file_count": count_files_in_dir(wer_dir),
                "safe_to_delete": True
            })

    # PCHealth
    pchealth = os.path.join(drive, "Windows", "PCHealth")
    if os.path.exists(pchealth):
        size = get_dir_size(pchealth)
        if size > 0:
            items.append({
                "path": pchealth,
                "description": "Windows 健康报告",
                "size_bytes": size,
                "size_readable": format_size(size),
                "file_count": count_files_in_dir(pchealth),
                "safe_to_delete": True
            })

    return items


def scan_prefetch(drive):
    """扫描预读取文件"""
    items = []
    prefetch_dir = os.path.join(drive, "Windows", "Prefetch")
    if os.path.exists(prefetch_dir):
        size = get_dir_size(prefetch_dir)
        if size > 0:
            items.append({
                "path": prefetch_dir,
                "description": "Windows 预读取文件 (Prefetch)",
                "size_bytes": size,
                "size_readable": format_size(size),
                "file_count": count_files_in_dir(prefetch_dir),
                "safe_to_delete": True
            })
    return items


def scan_crash_dumps(drive):
    """扫描崩溃转储文件"""
    items = []

    # 系统崩溃转储
    dump_dir = os.path.join(drive, "Windows", "Minidump")
    if os.path.exists(dump_dir):
        size = get_dir_size(dump_dir)
        if size > 0:
            items.append({
                "path": dump_dir,
                "description": "系统崩溃转储 (Minidump)",
                "size_bytes": size,
                "size_readable": format_size(size),
                "file_count": count_files_in_dir(dump_dir),
                "safe_to_delete": True
            })

    # 用户模式转储
    local_appdata = os.environ.get('LOCALAPPDATA', '')
    if local_appdata:
        crash_dir = os.path.join(local_appdata, 'CrashDumps')
        if os.path.exists(crash_dir) and crash_dir.startswith(drive):
            size = get_dir_size(crash_dir)
            if size > 0:
                items.append({
                    "path": crash_dir,
                    "description": "用户模式崩溃转储",
                    "size_bytes": size,
                    "size_readable": format_size(size),
                    "file_count": count_files_in_dir(crash_dir),
                    "safe_to_delete": True
                })

    return items


def scan_browser_cache(drive):
    """扫描浏览器缓存"""
    items = []
    local_appdata = os.environ.get('LOCALAPPDATA', '')

    browsers = {
        'Chrome': os.path.join(local_appdata, 'Google', 'Chrome', 'User Data', 'Default', 'Cache'),
        'Edge': os.path.join(local_appdata, 'Microsoft', 'Edge', 'User Data', 'Default', 'Cache'),
        'Firefox': os.path.join(local_appdata, 'Mozilla', 'Firefox', 'Profiles'),
    }

    for name, cache_path in browsers.items():
        if cache_path and os.path.exists(cache_path) and cache_path.startswith(drive):
            size = get_dir_size(cache_path)
            if size > 0:
                items.append({
                    "path": cache_path,
                    "description": f"{name} 浏览器缓存",
                    "size_bytes": size,
                    "size_readable": format_size(size),
                    "file_count": count_files_in_dir(cache_path),
                    "safe_to_delete": True
                })

    return items


def get_disk_usage(drive):
    """获取磁盘使用情况"""
    try:
        usage = shutil.disk_usage(drive + "\\")
        return {
            "total": usage.total,
            "used": usage.used,
            "free": usage.free,
            "total_readable": format_size(usage.total),
            "used_readable": format_size(usage.used),
            "free_readable": format_size(usage.free),
            "usage_percent": round(usage.used / usage.total * 100, 1)
        }
    except Exception as e:
        return {"error": str(e)}


def main():
    parser = argparse.ArgumentParser(description='磁盘垃圾文件扫描工具')
    parser.add_argument('drive', nargs='?', default='C', help='要扫描的盘符 (如 C, D, E)')
    parser.add_argument('--categories', nargs='*', default=None,
                        help='指定扫描类别: temp, cache, log, recycle, update, error_report, prefetch, crash_dump, browser_cache')
    args = parser.parse_args()

    drive = args.drive.upper().strip(':\\')
    drive_letter = f"{drive}:"

    # 验证盘符
    if not os.path.exists(drive_letter + "\\"):
        print(json.dumps({"error": f"驱动器 {drive_letter} 不存在"}, ensure_ascii=False))
        sys.exit(1)

    all_categories = {
        'temp': ('临时文件', scan_temp_files),
        'cache': ('缓存文件', scan_cache_files),
        'log': ('日志文件', scan_log_files),
        'recycle': ('回收站', scan_recycle_bin),
        'update': ('更新缓存', scan_windows_update_cache),
        'error_report': ('错误报告', scan_error_reports),
        'prefetch': ('预读取文件', scan_prefetch),
        'crash_dump': ('崩溃转储', scan_crash_dumps),
        'browser_cache': ('浏览器缓存', scan_browser_cache),
    }

    categories = args.categories if args.categories else list(all_categories.keys())

    report = {
        "scan_time": datetime.now().isoformat(),
        "drive": drive_letter,
        "disk_usage": get_disk_usage(drive_letter),
        "categories": {},
        "summary": {
            "total_size_bytes": 0,
            "total_size_readable": "0 B",
            "total_items": 0,
            "safe_total_bytes": 0,
            "safe_total_readable": "0 B"
        }
    }

    for cat_key in categories:
        if cat_key not in all_categories:
            continue
        cat_name, scan_func = all_categories[cat_key]
        items = scan_func(drive_letter)
        cat_size = sum(i['size_bytes'] for i in items)
        safe_size = sum(i['size_bytes'] for i in items if i['safe_to_delete'])

        report["categories"][cat_key] = {
            "name": cat_name,
            "items": items,
            "category_size_bytes": cat_size,
            "category_size_readable": format_size(cat_size),
            "item_count": len(items)
        }
        report["summary"]["total_size_bytes"] += cat_size
        report["summary"]["safe_total_bytes"] += safe_size
        report["summary"]["total_items"] += len(items)

    report["summary"]["total_size_readable"] = format_size(report["summary"]["total_size_bytes"])
    report["summary"]["safe_total_readable"] = format_size(report["summary"]["safe_total_bytes"])

    # 输出为 JSON
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
