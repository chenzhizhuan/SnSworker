# -*- coding: utf-8 -*-
"""TeleAgent 每日积分自动领取一键脚本（单文件版，无跨文件 import）。

设计变更（2026-08-24）：
    彻底消除 .pyc 生成问题。原版通过 `from shot_window import ...` 和
    `from find_claim_button import ...` 跨文件引用，Python 会在
    scripts/__pycache__/ 下生成 .pyc 缓存，导致技能上架被拒
    （「存在恶意扩展名文件 .pyc」）。

    本版将所有依赖函数内联为单文件，无任何本地 import，
    从根本上避免 __pycache__ 生成。

核心流程:
    1. 确认 TeleAgent 主窗口存在，置前
    2. 尝试精确定位「立即领取」/「今日已领」按钮（菜单可能已打开）
    3. 若按钮未找到 → 打开账户菜单（uiautomation 定位「肖洋」或兜底坐标）
    4. 「立即领取」→ 用 ctrl.Click() 点击（Electron 兼容）
    5. 点击后重新打开菜单验证按钮是否变为「今日已领」
    6. 截图留档 + 输出结构化结果 JSON

依赖: pip install uiautomation psutil pillow pywin32
用法:
    python claim_points.py [--output-dir D:\\temp\\points] [--window-name TeleAgent]

输出（最后一行 RESULT:）:
    RESULT: {"status": "claimed|already_claimed|failed_missing_button|failed_no_window|failed_verify",
             "days": 11, "points": 1100, "verified": true, "screenshot": "..."}
"""
import argparse
import ctypes
import ctypes.wintypes
import json
import os
import re
import sys
import time

import uiautomation as auto
from PIL import ImageGrab

# 禁止生成 .pyc / __pycache__（双重保险）
sys.dont_write_bytecode = True

user32 = ctypes.windll.user32
WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

# 精确按钮名（仅匹配这两种，避免误匹配侧边栏任务名）
EXACT_BUTTON_NAMES = ('立即领取', '今日已领')

# 账户入口相对主窗口的近似位置（宽比例, 高比例）——兜底用
ACCOUNT_ENTRY_REL = (0.043, 0.94)

# 账户用户名（用于 uiautomation 定位账户入口）
ACCOUNT_USERNAME = '肖洋'


# ===== 以下函数原属 shot_window.py / find_claim_button.py，现内联 =====

def find_main_hwnd(proc_name):
    """按进程名枚举窗口，返回面积最大的可见主窗口句柄；无则返回 None。

    Electron 应用有多进程（主进程 + GPU + 渲染进程等），窗口可能
    属于任一子进程而非最小 PID 进程。收集所有同名进程的窗口，
    按面积排序选最大者；同时跳过最小化窗口。
    """
    import psutil

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


def find_window(name):
    """通过 uiautomation 按窗口标题查找控件。"""
    for w in auto.GetRootControl().GetChildren():
        if w.Name == name:
            return w
    return None


def walk(el, depth=0, max_depth=40):
    """深度优先遍历 UI 树，产出 (ControlTypeName, Name, left, top, right, bottom)。"""
    if depth > max_depth:
        return
    try:
        r = el.BoundingRectangle
        if r.left >= 0 and r.top >= 0:
            yield (el.ControlTypeName, el.Name, r.left, r.top, r.right, r.bottom)
    except Exception:
        pass
    for child in el.GetChildren():
        yield from walk(child, depth + 1, max_depth)


def iter_controls(el, depth=0, max_depth=40):
    """深度优先遍历，产出控件对象本身（用于控件级操作如 Click()）。"""
    if depth > max_depth:
        return
    yield el
    for child in el.GetChildren():
        yield from iter_controls(child, depth + 1, max_depth)


def find_claim_control(window_name='TeleAgent'):
    """精确匹配返回「立即领取」/「今日已领」按钮控件对象。

    只匹配 EXACT_BUTTON_NAMES 中的精确名称，避免误匹配侧边栏任务名。
    返回控件对象或 None。
    """
    win = find_window(window_name)
    if win is None:
        return None
    matches = []
    for el in iter_controls(win):
        try:
            name = el.Name
        except Exception:
            continue
        if not name:
            continue
        if name in EXACT_BUTTON_NAMES:
            matches.append(el)
    if not matches:
        return None
    # 优先「立即领取」，其次「今日已领」
    for kw in EXACT_BUTTON_NAMES:
        for el in matches:
            if el.Name == kw:
                return el
    return matches[0]


# ===== 以下为 claim_points.py 自身逻辑 =====

def get_win_rect(proc_name='TeleAgent'):
    """返回 (left, top, right, bottom) 或 None。"""
    hwnd = find_main_hwnd(proc_name)
    if hwnd is None:
        return None
    r = ctypes.wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    return (r.left, r.top, r.right, r.bottom)


def bring_to_front(proc_name='TeleAgent'):
    """置前 TeleAgent 窗口。"""
    hwnd = find_main_hwnd(proc_name)
    if hwnd is None:
        return False
    user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.5)
    return True


def click_xy(x, y):
    """在屏幕坐标 (x, y) 执行一次鼠标左键点击（兜底方案）。"""
    import win32api
    import win32con
    win32api.SetCursorPos((x, y))
    time.sleep(0.15)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.06)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    print('clicked %d,%d' % (x, y))


def click_control(ctrl):
    """通过 uiautomation 控件级 Click() 点击，避免坐标点击被 Electron 窗口拦截。

    优先使用控件自身的 Click() 模式；失败时退回坐标点击。
    """
    try:
        ctrl.SetFocus()
        time.sleep(0.1)
        ctrl.Click()
        print('clicked control: %s' % ctrl.Name)
        return True
    except Exception as e:
        print('control click failed (%s), fallback to xy click' % e)
        try:
            r = ctrl.BoundingRectangle
            click_xy((r.left + r.right) // 2, (r.top + r.bottom) // 2)
            return True
        except Exception as e2:
            print('xy click also failed: %s' % e2)
            return False


def open_account_menu(rect, window_name='TeleAgent'):
    """打开左下角账户菜单。

    方案1: uiautomation 定位含「肖洋」的控件并 Click()
    方案2: 兜底坐标点击 (0.043*W, 0.94*H)
    返回 True/False 表示菜单是否打开（通过 find_claim_control 验证）。
    """
    win = find_window(window_name)

    if win:
        def _find_account(ctrl, depth=0, max_depth=15):
            if depth > max_depth:
                return None
            name = ctrl.Name
            if name and ACCOUNT_USERNAME in name:
                return ctrl
            for child in ctrl.GetChildren():
                result = _find_account(child, depth + 1, max_depth)
                if result:
                    return result
            return None

        account_ctrl = _find_account(win)
        if account_ctrl:
            try:
                account_ctrl.Click()
                time.sleep(1.5)
                if find_claim_control(window_name):
                    return True
            except Exception:
                pass

    # 方案2：兜底坐标点击
    left, top, right, bottom = rect
    ax = int(left + (right - left) * ACCOUNT_ENTRY_REL[0])
    ay = int(top + (bottom - top) * ACCOUNT_ENTRY_REL[1])
    click_xy(ax, ay)
    time.sleep(1.5)

    return find_claim_control(window_name) is not None


def parse_days_points(window_name='TeleAgent'):
    """从 UI 树中解析「已领X天」「累计X积分」。返回 (days, points)，未知为 None。"""
    win = find_window(window_name)
    if win is None:
        return None, None

    days = points = None
    for el in walk(win):
        name = el[1]
        if not name:
            continue
        m = re.search(r'已领\s*(\d+)\s*天', name)
        if m:
            days = int(m.group(1))
        m = re.search(r'累计\s*(\d+)\s*积分', name)
        if m:
            points = int(m.group(1))
    return days, points


def shot(rect, path):
    """按主窗口矩形截图。"""
    left, top, right, bottom = rect
    img = ImageGrab.grab(bbox=(left, top, right, bottom))
    img.save(path)
    return path


def verify_claimed(window_name='TeleAgent', rect=None):
    """点击后验证领取是否成功：重新打开菜单检查按钮是否变为「今日已领」。

    点击后菜单通常会关闭，需要重新打开。
    返回 True/False。
    """
    # 先检查按钮是否可直接找到（菜单可能仍开着）
    ctrl = find_claim_control(window_name)
    if ctrl is not None:
        return '今日已领' in ctrl.Name

    # 菜单已关闭，重新打开
    if rect:
        open_account_menu(rect, window_name)
        time.sleep(1)
        ctrl = find_claim_control(window_name)
        if ctrl is not None:
            return '今日已领' in ctrl.Name

    return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-dir', default=r'D:\TeleClaw的工作空间\.temp\teleagent-points')
    parser.add_argument('--window-name', default='TeleAgent')
    parser.add_argument('--proc-name', default='TeleAgent')
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    # 1. 确认窗口并置前
    if not bring_to_front(args.proc_name):
        print('RESULT: ' + json.dumps({'status': 'failed_no_window'}, ensure_ascii=False))
        return 1

    rect = get_win_rect(args.proc_name)
    if rect is None:
        print('RESULT: ' + json.dumps({'status': 'failed_no_window'}, ensure_ascii=False))
        return 1

    # 2. 尝试直接定位按钮（菜单可能已打开）
    ctrl = find_claim_control(args.window_name)
    btn_info = None
    if ctrl is not None:
        try:
            r = ctrl.BoundingRectangle
            btn_info = ((r.left + r.right) // 2, (r.top + r.bottom) // 2, ctrl.Name)
        except Exception:
            btn_info = None

    # 3. 按钮未找到 → 打开账户菜单
    if btn_info is None:
        if not open_account_menu(rect, args.window_name):
            shot(rect, os.path.join(args.output_dir, 'claim_fail.png'))
            print('RESULT: ' + json.dumps({'status': 'failed_missing_button'}, ensure_ascii=False))
            return 2
        # 菜单已打开，重新定位按钮
        ctrl = find_claim_control(args.window_name)
        if ctrl is not None:
            try:
                r = ctrl.BoundingRectangle
                btn_info = ((r.left + r.right) // 2, (r.top + r.bottom) // 2, ctrl.Name)
            except Exception:
                btn_info = None

    if btn_info is None:
        shot(rect, os.path.join(args.output_dir, 'claim_fail.png'))
        print('RESULT: ' + json.dumps({'status': 'failed_missing_button'}, ensure_ascii=False))
        return 2

    cx, cy, name = btn_info
    print('BUTTON: %s at (%d,%d)' % (name, cx, cy))

    # 4. 已领取
    if '今日已领' in name:
        shot(rect, os.path.join(args.output_dir, 'claim_already.png'))
        days, points = parse_days_points(args.window_name)
        print('RESULT: ' + json.dumps({'status': 'already_claimed', 'days': days,
                                       'points': points}, ensure_ascii=False))
        return 0

    # 5. 解析领取前的天数/积分
    days_before, points_before = parse_days_points(args.window_name)

    # 6. 用 uiautomation Click() 点击（Electron 兼容）
    if ctrl is not None:
        clicked = click_control(ctrl)
    else:
        click_xy(cx, cy)
        clicked = True

    if not clicked:
        shot(rect, os.path.join(args.output_dir, 'claim_fail.png'))
        print('RESULT: ' + json.dumps({'status': 'failed_missing_button'}, ensure_ascii=False))
        return 2

    time.sleep(2)

    # 7. 验证：重新打开菜单检查按钮状态
    is_verified = verify_claimed(args.window_name, rect)

    # 最终截图（确保菜单打开状态截取）
    if not is_verified:
        open_account_menu(rect, args.window_name)
        time.sleep(1)
        # 再次检查
        ctrl_check = find_claim_control(args.window_name)
        if ctrl_check is not None and '今日已领' in ctrl_check.Name:
            is_verified = True

    shot_path = shot(rect, os.path.join(args.output_dir, 'claim_result.png'))

    if not is_verified:
        # 点击后未能确认按钮变为「今日已领」，视为失败而非成功，避免误报
        print('RESULT: ' + json.dumps({'status': 'failed_verify',
                                       'days_before': days_before,
                                       'points_before': points_before,
                                       'screenshot': shot_path}, ensure_ascii=False))
        return 2

    days_after, points_after = parse_days_points(args.window_name)

    result = {
        'status': 'claimed',
        'days': days_after,
        'points': points_after,
        'days_before': days_before,
        'points_before': points_before,
        'verified': is_verified,
        'screenshot': shot_path,
    }
    print('RESULT: ' + json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
