"""
Scrapling 官方测试一键自检 — 验证本地 Scrapling 安装是否正常
来源：Scrapling 官方 tests/parser/ 测试套件（94 项断言）
用法：python run_selftest.py

测试覆盖：
- CSS/XPath/文本/正则选择器
- 属性操作与 JSON 转换
- DOM 导航（父/子/兄弟/祖先）
- 自适应元素重定位
- 选择器过滤与高级特性
- 大 HTML 解析性能

依赖安装：pip install pytest pytest-asyncio
"""

import subprocess
import sys
import os
import shutil


def run_selftest():
    """运行官方 parser 测试套件，输出结果摘要"""

    test_dir = os.path.dirname(os.path.abspath(__file__))
    print("=" * 60)
    print("Scrapling 官方测试自检 (parser 模块, 94 项断言)")
    print("=" * 60)
    print(f"测试目录: {test_dir}")
    print()

    # 使用 pytest 运行测试
    result = subprocess.run(
        [sys.executable, "-m", "pytest", test_dir, "-v", "--tb=short"],
        capture_output=False,
        text=True
    )

    # 清理 pytest 生成的缓存
    for cache_name in ("__pycache__", ".pytest_cache"):
        for cache_dir in [
            os.path.join(test_dir, cache_name),
            os.path.join(test_dir, "selftest", cache_name),
        ]:
            if os.path.isdir(cache_dir):
                shutil.rmtree(cache_dir, ignore_errors=True)

    return result.returncode == 0


if __name__ == "__main__":
    success = run_selftest()
    print()
    if success:
        print("✅ 全部测试通过! Scrapling 安装正常。")
    else:
        print("❌ 部分测试未通过，请检查 Scrapling 安装。")
    sys.exit(0 if success else 1)
