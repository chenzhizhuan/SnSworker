# -*- coding: utf-8 -*-
"""截取指定进程主窗口画面并置前窗口，用于确认积分领取结果。

依赖: pip install psutil pillow pywin32
用法:
    python shot_window.py --proc-name TeleAgent --out D:\\path\\to\\shot.png
输出:
    成功: saved <path> size WxH
    未找到主窗口: NO MAIN WINDOW
"""
import argparse
import ctypes
import ctypes.wintypes
import sys
import time

# 禁止生成 .pyc / __pycache__（技能上架禁止 .pyc 扩展名）
sys.dont_write_bytecode = True

import psutil
from PIL import ImageGrab

user32 = ctypes.windll.user32
WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)


def find_main_hwnd(proc_name):
    """按进程名枚举窗口，返回面积最大的可见主窗口句柄；无则返回 None。

    优化（自检修 2026-08-24）：
        Electron 应用有多进程（主进程 + GPU + 渲染进程等），窗口可能
        属于任一子进程而非最小 PID 进程。因此收集所有同名进程的窗口，
        按面积排序选最大者；同时跳过最小化窗口以避免选中不可见窗口。
    """
    target_pids = set()
    proc_name_lower = proc_name.lower().replace('.exe', '')
    for p in psutil.process_iter(['pid', 'name']):
        try:
            name = (p.info['name'] or '').lower().replace('.exe', '')
            if name == proc_name_lower:
                target_pids.add(p.info['pid'])
        except Exception:
            pass
    if not target_pids:
        return None

    found = []

    def _enum(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        if user32.IsIconic(hwnd):  # 跳过最小化窗口
            return True
        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value in target_pids:
            found.append(hwnd)
        return True

    user32.EnumWindows(WNDENUMPROC(_enum), 0)
    if not found:
        return None

    best, best_area = None, 0
    for hwnd in found:
        r = ctypes.wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(r))
        area = (r.right - r.left) * (r.bottom - r.top)
        if area > best_area:
            best_area = area
            best = hwnd
    return best


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--proc-name', default='TeleAgent')
    parser.add_argument('--out', required=True)
    args = parser.parse_args()

    hwnd = find_main_hwnd(args.proc_name)
    if hwnd is None:
        print('NO MAIN WINDOW')
        return 1

    user32.SetForegroundWindow(hwnd)
    time.sleep(0.4)
    r = ctypes.wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    left, top, right, bottom = r.left, r.top, r.right, r.bottom
    w, h = right - left, bottom - top
    img = ImageGrab.grab(bbox=(left, top, right, bottom))
    img.save(args.out)
    print('saved %s size %dx%d' % (args.out, w, h))
    return 0


if __name__ == '__main__':
    sys.exit(main())