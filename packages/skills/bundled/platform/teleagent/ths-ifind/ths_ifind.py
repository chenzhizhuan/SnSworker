#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ths_ifind - 同花顺iFinD金融数据查询 skill
基于 pywencai 库封装同花顺问财接口，支持股票/基金/港股/美股/可转债/指数/宏观等多类数据查询
"""

import os
import sys
import json
import csv
import re
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

# ============================================================
# 环境检测
# ============================================================

def check_environment():
    """检测运行环境是否满足要求"""
    errors = []

    # 检测 Python 版本
    if sys.version_info < (3, 8):
        errors.append(f"Python 版本过低: {sys.version}, 需要 3.8+")

    # 检测 pywencai
    try:
        import pywencai
    except ImportError:
        errors.append("pywencai 未安装, 请运行: pip install pywencai")

    # 检测 pandas
    try:
        import pandas
    except ImportError:
        errors.append("pandas 未安装, 请运行: pip install pandas")

    # 检测 Node.js
    try:
        import subprocess
        result = subprocess.run(['node', '--version'], capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            errors.append("Node.js 不可用, 请安装 Node.js v16+")
        else:
            version = result.stdout.strip().lstrip('v')
            major = int(version.split('.')[0]) if version else 0
            if major < 16:
                errors.append(f"Node.js 版本过低: {version}, 需要 v16+")
    except FileNotFoundError:
        errors.append("Node.js 未安装, 请安装 Node.js v16+ (pywencai 依赖)")
    except Exception as e:
        errors.append(f"Node.js 检测失败: {e}")

    return errors


def safe_filename(s: str, max_len: int = 80) -> str:
    """将查询文本转为安全文件名片段"""
    s = re.sub(r'[<>:"/\\|?*\n\r\t]', "_", s)
    s = s.strip().replace(" ", "_")[:max_len]
    return s or "query"


# ============================================================
# 核心查询类
# ============================================================

class THSQuery:
    """同花顺iFinD金融数据查询客户端"""

    # 支持的查询类型
    VALID_QUERY_TYPES = {
        'stock': '股票',
        'zhishu': '指数',
        'fund': '基金',
        'hkstock': '港股',
        'usstock': '美股',
        'conbond': '可转债',
        'insurance': '保险',
        'futures': '期货',
        'lccp': '理财',
        'foreign_exchange': '外汇',
    }

    def __init__(self, cookie: Optional[str] = None):
        """
        初始化客户端

        :param cookie: 同花顺问财 Cookie，不传则从环境变量 THS_COOKIE 读取
        """
        # 环境检测
        env_errors = check_environment()
        if env_errors:
            raise RuntimeError(
                "环境检测失败:\n" + "\n".join(f"  - {e}" for e in env_errors)
            )

        import pywencai

        self.pywencai = pywencai
        self.cookie = cookie or os.getenv("THS_COOKIE")
        if not self.cookie:
            raise ValueError(
                "Cookie 未配置。请通过以下方式之一设置:\n"
                "  1. 设置环境变量: $env:THS_COOKIE = 'your_cookie'\n"
                "  2. 初始化时传入: THSQuery(cookie='your_cookie')\n"
                "  3. 命令行传参: python ths_ifind.py 'query' --cookie 'your_cookie'\n\n"
                "获取 Cookie 方法:\n"
                "  浏览器打开 https://www.10jqka.com.cn/ 登录后,\n"
                "  F12 → Network → 找到请求 → 复制请求头中的 Cookie 值"
            )

    def query(
        self,
        query: str,
        query_type: str = 'stock',
        sort_key: Optional[str] = None,
        sort_order: str = 'desc',
        loop: Union[bool, int] = False,
        page: int = 1,
        perpage: int = 100,
        pro: bool = False,
        retry: int = 10,
        sleep: float = 0,
        find: Optional[List[str]] = None,
        no_detail: bool = False,
        log: bool = False,
    ) -> Union['pandas.DataFrame', Dict, None]:
        """
        查询同花顺问财数据

        :param query: 自然语言查询句
        :param query_type: 数据类型 (stock/zhishu/fund/hkstock/usstock/conbond/insurance/futures/lccp/foreign_exchange)
        :param sort_key: 排序字段 (返回结果的列名)
        :param sort_order: 排序规则 (asc/desc)
        :param loop: 循环分页 (True=全部, 数字=指定页数)
        :param page: 起始页号
        :param perpage: 每页条数 (最大100)
        :param pro: 付费版
        :param retry: 重试次数
        :param sleep: 请求间隔秒数
        :param find: 置顶指定标的列表
        :param no_detail: 不返回详情字典
        :param log: 打印日志
        :return: DataFrame (列表查询) / dict (详情查询) / None
        """
        if query_type not in self.VALID_QUERY_TYPES:
            raise ValueError(
                f"不支持的 query_type: {query_type}\n"
                f"支持的类型: {', '.join(f'{k}({v})' for k, v in self.VALID_QUERY_TYPES.items())}"
            )

        # 构建 kwargs
        kwargs = {
            'query': query,
            'query_type': query_type,
            'cookie': self.cookie,
            'retry': retry,
            'log': log,
        }

        if sort_key:
            kwargs['sort_key'] = sort_key
        if sort_order:
            kwargs['sort_order'] = sort_order
        if loop:
            kwargs['loop'] = loop
        if page > 1:
            kwargs['page'] = page
        if perpage != 100:
            kwargs['perpage'] = perpage
        if pro:
            kwargs['pro'] = pro
        if sleep > 0:
            kwargs['sleep'] = sleep
        if find:
            kwargs['find'] = find
        if no_detail:
            kwargs['no_detail'] = True

        try:
            result = self.pywencai.get(**kwargs)
            return result
        except Exception as e:
            raise RuntimeError(f"查询失败: {e}") from e

    def query_to_csv(
        self,
        query: str,
        output_dir: Optional[Union[str, Path]] = None,
        **kwargs
    ) -> Dict[str, str]:
        """
        查询并自动保存为 CSV/JSON

        :param query: 自然语言查询句
        :param output_dir: 输出目录
        :param kwargs: 传递给 query() 的额外参数
        :return: {'csv': path, 'json': path, 'desc': path} 或 {'json': path, 'desc': path}
        """
        result = self.query(query, **kwargs)

        output_dir = Path(output_dir) if output_dir else Path(__file__).parent / "output"
        output_dir.mkdir(parents=True, exist_ok=True)

        safe_name = safe_filename(query)
        desc_path = output_dir / f"ths_ifind_{safe_name}_description.txt"
        paths = {}

        query_type = kwargs.get('query_type', 'stock')

        # DataFrame → CSV
        try:
            import pandas as pd
            if isinstance(result, pd.DataFrame):
                if result.empty:
                    print("查询结果为空")
                    self._write_description(desc_path, query, 0, [], "空结果", query_type)
                    paths['desc'] = str(desc_path)
                    return paths

                csv_path = output_dir / f"ths_ifind_{safe_name}.csv"
                # 使用 UTF-8 BOM 编码，Excel 直接可读
                result.to_csv(csv_path, index=False, encoding='utf-8-sig')
                paths['csv'] = str(csv_path)

                col_names = list(result.columns)
                self._write_description(desc_path, query, len(result), col_names, "DataFrame", query_type)
                paths['desc'] = str(desc_path)

                print(f"CSV: {csv_path}")
                print(f"行数: {len(result)}, 列数: {len(col_names)}")
                print(f"列名: {', '.join(col_names[:20])}{'...' if len(col_names) > 20 else ''}")
                return paths

        except ImportError:
            pass

        # dict → JSON
        if isinstance(result, dict):
            json_path = output_dir / f"ths_ifind_{safe_name}_raw.json"
            # 处理不可序列化的对象
            def json_default(obj):
                try:
                    import pandas as pd
                    if isinstance(obj, pd.DataFrame):
                        return obj.to_dict(orient='records')
                except:
                    pass
                return str(obj)

            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2, default=json_default)
            paths['json'] = str(json_path)

            keys = list(result.keys()) if result else []
            self._write_description(desc_path, query, 1, keys, "Dict(详情)", query_type)
            paths['desc'] = str(desc_path)

            print(f"JSON: {json_path}")
            print(f"类型: 详情字典, 键: {', '.join(keys[:20])}{'...' if len(keys) > 20 else ''}")
            return paths

        # None
        if result is None:
            self._write_description(desc_path, query, 0, [], "None(无结果)", query_type)
            paths['desc'] = str(desc_path)
            print("查询返回 None (可能查询条件无法解析或无匹配数据)")
            return paths

        # 其他类型
        json_path = output_dir / f"ths_ifind_{safe_name}_raw.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(str(result), f, ensure_ascii=False, indent=2)
        paths['json'] = str(json_path)
        self._write_description(desc_path, query, 1, [], str(type(result)), query_type)
        paths['desc'] = str(desc_path)
        print(f"结果类型: {type(result)}, 已保存原始数据")
        return paths

    @staticmethod
    def _write_description(
        desc_path: Path,
        query: str,
        row_count: int,
        columns: List[str],
        data_type: str,
        query_type: str
    ):
        """写入查询描述文件"""
        type_name = THSQuery.VALID_QUERY_TYPES.get(query_type, query_type)
        lines = [
            "同花顺iFinD 查询结果说明",
            "=" * 50,
            f"查询内容: {query}",
            f"数据类型: {query_type} ({type_name})",
            f"结果类型: {data_type}",
            f"数据行数: {row_count}",
            f"列名/键名: {', '.join(columns) if columns else '(无)'}",
            "",
            f"查询时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "数据来源: 同花顺问财 (iwencai.com)",
            "",
            "说明: 数据来源于同花顺问财平台, 通过 pywencai 库获取。",
            "免责声明: 仅供参考, 不构成投资建议。",
        ]
        desc_path.write_text("\n".join(lines), encoding='utf-8')

    def save_csv(self, df, name: str, output_dir: Optional[Union[str, Path]] = None) -> str:
        """
        将 DataFrame 保存为 CSV

        :param df: pandas DataFrame
        :param name: 文件名标识
        :param output_dir: 输出目录
        :return: CSV 文件路径
        """
        output_dir = Path(output_dir) if output_dir else Path(__file__).parent / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        safe_name = safe_filename(name)
        csv_path = output_dir / f"ths_ifind_{safe_name}.csv"
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        print(f"CSV: {csv_path}")
        return str(csv_path)


# ============================================================
# 命令行入口
# ============================================================

def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description='同花顺iFinD金融数据查询 - 支持股票/基金/港股/美股/可转债/指数/宏观数据',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  ths_ifind.py \"贵州茅台最新价\"\n"
            "  ths_ifind.py \"今日涨幅大于2%的A股\"\n"
            "  ths_ifind.py --query-type fund \"近一年收益率大于20%的股票型基金\"\n"
            "  ths_ifind.py --query-type hkstock \"腾讯控股最新价\"\n"
            "  ths_ifind.py --query-type conbond \"双低值小于130的可转债\"\n"
            "  ths_ifind.py \"A股今日涨幅\" --sort-key \"涨跌幅\" --sort-order desc\n"
            "  ths_ifind.py \"市盈率小于30的股票\" --loop\n"
        )
    )

    parser.add_argument('query', nargs='?', help='自然语言查询句')
    parser.add_argument('--query', dest='query_opt', help='自然语言查询句 (显式参数)')

    parser.add_argument('--query-type', '-t', dest='query_type', default='stock',
                        choices=list(THSQuery.VALID_QUERY_TYPES.keys()),
                        help='数据类型 (默认: stock)')

    parser.add_argument('--sort-key', dest='sort_key', default=None,
                        help='排序字段 (返回结果的列名)')
    parser.add_argument('--sort-order', dest='sort_order', default='desc',
                        choices=['asc', 'desc'],
                        help='排序规则 (默认: desc)')

    parser.add_argument('--loop', nargs='?', const=True, default=False,
                        help='循环分页: 不带值=全部, 带数字=指定页数')
    parser.add_argument('--page', type=int, default=1,
                        help='起始页号 (默认: 1)')
    parser.add_argument('--perpage', type=int, default=100,
                        help='每页条数 (默认: 100, 最大: 100)')

    parser.add_argument('--pro', action='store_true',
                        help='付费版 (需付费版 cookie)')
    parser.add_argument('--retry', type=int, default=10,
                        help='重试次数 (默认: 10)')
    parser.add_argument('--sleep', type=float, default=0,
                        help='循环请求间隔秒数 (默认: 0)')

    parser.add_argument('--find', nargs='+', default=None,
                        help='置顶指定标的 (如: 600519 000010)')
    parser.add_argument('--no-detail', dest='no_detail', action='store_true',
                        help='不返回详情字典, 只返回 DataFrame')

    parser.add_argument('--cookie', default=None,
                        help='同花顺问财 Cookie (也可通过环境变量 THS_COOKIE 设置)')
    parser.add_argument('--output-dir', dest='output_dir', default=None,
                        help='输出目录 (默认: 脚本同级 output/ 目录)')
    parser.add_argument('--log', action='store_true',
                        help='打印调试日志')

    args = parser.parse_args()

    # 解析 query
    query = args.query_opt or args.query
    if not query:
        parser.print_help()
        sys.exit(1)

    # 解析 loop 参数
    loop = args.loop
    if isinstance(loop, str):
        try:
            loop = int(loop)
        except ValueError:
            loop = True

    try:
        ths = THSQuery(cookie=args.cookie)

        # 构建 query kwargs
        query_kwargs = {
            'query_type': args.query_type,
            'sort_key': args.sort_key,
            'sort_order': args.sort_order,
            'loop': loop,
            'page': args.page,
            'perpage': args.perpage,
            'pro': args.pro,
            'retry': args.retry,
            'sleep': args.sleep,
            'find': args.find,
            'no_detail': args.no_detail,
            'log': args.log,
        }

        # 移除 None 值
        query_kwargs = {k: v for k, v in query_kwargs.items() if v is not None and v is not False}

        paths = ths.query_to_csv(query, output_dir=args.output_dir, **query_kwargs)

        print(f"\n描述: {paths.get('desc', '')}")
        if 'csv' in paths:
            print(f"CSV:  {paths['csv']}")
        if 'json' in paths:
            print(f"JSON: {paths['json']}")

    except ValueError as e:
        print(f"配置错误: {e}", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as e:
        print(f"运行错误: {e}", file=sys.stderr)
        sys.exit(2)
    except KeyboardInterrupt:
        print("\n用户中断", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"未知错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
