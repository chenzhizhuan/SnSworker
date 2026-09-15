#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
依赖自动安装脚本 - 首次运行时自动安装所需Python包，之后无需重复安装
"""
import subprocess, sys

REQUIRED_PACKAGES = [
    "akshare",
    "pandas",
    "numpy",
]

def check_and_install():
    missing = []
    for pkg in REQUIRED_PACKAGES:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)

    if not missing:
        print("所有依赖已就绪，无需安装。")
        return True

    print(f"检测到缺失依赖: {missing}")
    print("正在自动安装...")
    pip_cmd = [sys.executable, "-m", "pip", "install"] + missing
    result = subprocess.run(pip_cmd, capture_output=True, text=True)

    if result.returncode == 0:
        print("依赖安装成功!")
        for pkg in missing:
            try:
                __import__(pkg)
            except ImportError:
                print(f"警告: {pkg} 安装后仍无法导入，请手动检查")
                return False
        return True
    else:
        print(f"安装失败: {result.stderr[:500]}")
        return False

if __name__ == "__main__":
    success = check_and_install()
    if success:
        print("环境检查完成，可以运行 zt_scanner.py")
    sys.exit(0 if success else 1)
