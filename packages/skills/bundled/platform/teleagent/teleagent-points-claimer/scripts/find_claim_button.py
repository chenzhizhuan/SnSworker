# -*- coding: utf-8 -*-
"""定位 TeleAgent 客户端「积分福利社」中的领取按钮。

精确匹配「立即领取」或「今日已领」按钮（ButtonControl + 名称精确匹配），
避免误匹配侧边栏任务名等含「领取」二字的无关文本。

提供两种接口：
    - find_claim_control(): 返回控件对象，供 claim_points.py 点击用
    - main(): 命令行入口，输出坐标信息，供手动定位用

用法:
    python find_claim_button.py [--window-name TeleAgent]

输出:
    成功: CLAIM_BTN_RECT=(left,top,right,bottom) CENTER=(cx,cy) NAME=立即领取
    未找到: CLAIM_BTN_NOT_FOUND
    窗口不存在: NO_WINDOW
"""
import argparse
import sys
import io

# 禁止生成 .pyc / __pycache__（技能上架禁止 .pyc 扩展名）
sys.dont_write_bytecode = True

import uiautomation as auto

# 精确按钮名（优先级从高到低）
EXACT_NAMES = ('立即领取', '今日已领')


def find_window(name):
    for w in auto.GetRootControl().GetChildren():
        if w.Name == name:
            return w
    return None


def walk(el, depth=0, max_depth=40):
    """深度优先遍历，产出 (ControlTypeName, Name, left, top, right, bottom)。"""
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
    """精确匹配返回「立即领取」/「今日已领」按钮控件对象（而非坐标）。

    只匹配 EXACT_NAMES 中的精确名称，避免误匹配侧边栏任务名等含
    「领取」二字的无关文本。返回控件对象或 None。
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
        if name in EXACT_NAMES:
            matches.append(el)
    if not matches:
        return None
    # 优先「立即领取」，其次「今日已领」
    for kw in EXACT_NAMES:
        for el in matches:
            if el.Name == kw:
                return el
    return matches[0]


def main():
    # 修复 Windows 控制台中文编码问题
    if sys.stdout.encoding != 'utf-8':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

    parser = argparse.ArgumentParser()
    parser.add_argument('--window-name', default='TeleAgent')
    args = parser.parse_args()

    win = find_window(args.window_name)
    if win is None:
        print('NO_WINDOW')
        sys.exit(1)

    # 使用 find_claim_control 精确定位
    ctrl = find_claim_control(args.window_name)
    if ctrl is None:
        print('CLAIM_BTN_NOT_FOUND')
        sys.exit(2)

    r = ctrl.BoundingRectangle
    cx, cy = (r.left + r.right) // 2, (r.top + r.bottom) // 2
    print('CLAIM_BTN_RECT=(%d,%d,%d,%d) CENTER=(%d,%d) NAME=%s CT=%s'
          % (r.left, r.top, r.right, r.bottom, cx, cy, ctrl.Name, ctrl.ControlTypeName))
    sys.exit(0)


if __name__ == '__main__':
    main()
