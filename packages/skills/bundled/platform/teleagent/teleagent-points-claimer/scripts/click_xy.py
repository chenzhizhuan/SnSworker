# -*- coding: utf-8 -*-
"""在屏幕指定坐标执行一次鼠标左键点击。

用法:
    python click_xy.py --x 150 --y 770
输出:
    成功: clicked X,Y
"""
import argparse
import ctypes
import sys
import time

# 禁止生成 .pyc / __pycache__（技能上架禁止 .pyc 扩展名）
sys.dont_write_bytecode = True

import win32api
import win32con


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--x', type=int, required=True)
    parser.add_argument('--y', type=int, required=True)
    args = parser.parse_args()

    # 先移动光标到目标位置再点击，提高可靠性
    win32api.SetCursorPos((args.x, args.y))
    time.sleep(0.15)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.06)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    print('clicked %d,%d' % (args.x, args.y))
    return 0


if __name__ == '__main__':
    sys.exit(main())