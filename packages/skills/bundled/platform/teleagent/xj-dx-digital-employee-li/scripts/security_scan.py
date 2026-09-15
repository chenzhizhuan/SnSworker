#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安全漏洞扫描脚本
扫描 Java/Python 项目代码，检测 OWASP Top 10 常见漏洞模式。
输出结构化报告，包含风险等级、文件位置、代码片段和修复建议。

用法:
    python security_scan.py <项目路径> [--lang java|python|auto] [--format text|json] [-o 输出文件]
"""

import os
import re
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path


# === 漏洞检测规则 ===

RULES = [
    {
        "id": "SQL_INJECTION",
        "name": "SQL注入",
        "severity": "high",
        "description": "检测到字符串拼接SQL语句，可能导致SQL注入",
        "fix": "使用参数化查询或ORM的占位符（MyBatis用#{}而非${}）",
        "patterns": [
            # Java 字符串拼接 SQL
            (r'"(?:SELECT|INSERT|UPDATE|DELETE|select|insert|update|delete)\b[^"]*"\s*\+', "java"),
            # Python f-string SQL
            (r'f"(?:SELECT|INSERT|UPDATE|DELETE|select|insert|update|delete)\b[^"]*\{', "python"),
            # Python format SQL
            (r'"(?:SELECT|INSERT|UPDATE|DELETE|select|insert|update|delete)\b[^"]*"\s*\.format\(', "python"),
            # Python % 格式化 SQL
            (r'"(?:SELECT|INSERT|UPDATE|DELETE|select|insert|update|delete)\b[^"]*"\s*%\s*\(', "python"),
            # MyBatis ${} 占位符
            (r'\$\{[^}]+\}', "xml"),
        ],
    },
    {
        "id": "XSS",
        "name": "XSS跨站脚本",
        "severity": "high",
        "description": "检测到未转义的输出，可能导致XSS攻击",
        "fix": "对输出进行HTML转义，前端使用v-text而非v-html",
        "patterns": [
            (r'innerHTML\s*=\s*[^;]+', "javascript"),
            (r'document\.write\s*\(', "javascript"),
            (r'v-html\s*=', "vue"),
        ],
    },
    {
        "id": "COMMAND_INJECTION",
        "name": "命令注入",
        "severity": "high",
        "description": "检测到命令执行函数，可能存在命令注入风险",
        "fix": "使用参数列表形式调用subprocess，避免shell=True",
        "patterns": [
            (r'os\.system\s*\(', "python"),
            (r'subprocess\.(call|run|Popen)\s*\(.*shell\s*=\s*True', "python"),
            (r'Runtime\.getRuntime\(\)\.exec\s*\(', "java"),
            (r'ProcessBuilder\s*\(', "java"),
        ],
    },
    {
        "id": "HARDCODED_SECRET",
        "name": "硬编码敏感信息",
        "severity": "medium",
        "description": "检测到代码中硬编码的密码、密钥或凭证",
        "fix": "使用环境变量、配置中心或密钥管理服务",
        "patterns": [
            (r'(?:password|passwd|pwd)\s*=\s*["\'][^"\']{3,}["\']', "config"),
            (r'(?:secret|api_key|apikey|access_key|access_token|private_key)\s*=\s*["\'][^"\']{8,}["\']', "config"),
            (r'(?:password|passwd|pwd)\s*:\s*["\'][^"\']{3,}["\']', "yaml"),
            (r'(?:secret|api_key|apikey|access_key)\s*:\s*["\'][^"\']{8,}["\']', "yaml"),
            (r'jdbc:[a-z]+://[^;]+;\s*password\s*=\s*[^;\s]+', "config"),
        ],
    },
    {
        "id": "DESERIALIZATION",
        "name": "反序列化漏洞",
        "severity": "high",
        "description": "检测到不安全的反序列化操作",
        "fix": "使用安全的反序列化方式，Python用yaml.safe_load代替yaml.load",
        "patterns": [
            (r'ObjectInputStream', "java"),
            (r'\.readObject\s*\(', "java"),
            (r'pickle\.loads?\s*\(', "python"),
            (r'yaml\.load\s*\((?!.*Loader)', "python"),
            (r'marshal\.loads?\s*\(', "python"),
        ],
    },
    {
        "id": "PATH_TRAVERSAL",
        "name": "路径遍历",
        "severity": "medium",
        "description": "检测到文件路径可能包含用户输入，存在路径遍历风险",
        "fix": "对用户输入的文件路径进行校验和白名单过滤",
        "patterns": [
            (r'new\s+File\s*\([^)]*(?:request|param|args|input)', "java"),
            (r'open\s*\([^)]*(?:request|param|input|args)', "python"),
            (r'Paths\.get\s*\([^)]*(?:request|param|args|input)', "java"),
        ],
    },
    {
        "id": "INFO_LEAK",
        "name": "信息泄露",
        "severity": "low",
        "description": "异常信息直接返回客户端，可能泄露技术栈信息",
        "fix": "记录完整异常到日志，返回通用错误提示",
        "patterns": [
            (r'return\s+.*e\.getMessage\(\)', "java"),
            (r'return.*str\(e\)', "python"),
            (r'return.*traceback', "python"),
            (r'e\.printStackTrace\s*\(\)', "java"),
        ],
    },
    {
        "id": "WEAK_CRYPTO",
        "name": "弱加密算法",
        "severity": "medium",
        "description": "检测到不安全的加密算法",
        "fix": "使用AES-256、RSA-2048等安全算法，避免MD5/DES",
        "patterns": [
            (r'MessageDigest\.getInstance\s*\(\s*["\']MD5["\']', "java"),
            (r'MessageDigest\.getInstance\s*\(\s*["\']SHA-?1["\']', "java"),
            (r'Cipher\.getInstance\s*\(\s*["\']DES["\']', "java"),
            (r'hashlib\.md5\s*\(', "python"),
            (r'hashlib\.sha1\s*\(', "python"),
        ],
    },
    {
        "id": "DEBUG_ENABLED",
        "name": "调试模式未关闭",
        "severity": "low",
        "description": "生产环境开启了调试模式，可能暴露调试信息",
        "fix": "生产环境关闭debug模式",
        "patterns": [
            (r'app\.run\s*\([^)]*debug\s*=\s*True', "python"),
            (r'DEBUG\s*=\s*True', "python"),
            (r'debug:\s*true', "yaml"),
        ],
    },
]

# 文件扩展名到语言映射
EXT_LANG_MAP = {
    ".java": "java",
    ".py": "python",
    ".xml": "xml",
    ".js": "javascript",
    ".vue": "vue",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".properties": "config",
    ".conf": "config",
    ".html": "html",
}

# 跳过的目录
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".idea", ".vscode",
             "target", "build", "dist", ".temp", "venv", "env", ".venv"}

# 跳过的文件
SKIP_FILES = {".DS_Store", "Thumbs.db"}


def scan_file(filepath, rules, lang_filter="auto"):
    """扫描单个文件，返回发现的问题列表"""
    issues = []
    ext = Path(filepath).suffix.lower()
    file_lang = EXT_LANG_MAP.get(ext)

    if not file_lang:
        return issues

    if lang_filter != "auto" and file_lang not in (lang_filter, "config", "yaml", "xml", "javascript", "vue"):
        # 当指定语言时，配置类文件仍然扫描
        if file_lang not in ("config", "yaml"):
            return issues

    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except (IOError, PermissionError):
        return issues

    for rule in rules:
        for pattern, rule_lang in rule["patterns"]:
            # 语言过滤
            if lang_filter != "auto":
                if rule_lang not in (lang_filter, "config", "yaml", "xml", "javascript", "vue"):
                    continue

            if rule_lang != file_lang:
                continue

            compiled = re.compile(pattern, re.IGNORECASE)
            for i, line in enumerate(lines, 1):
                if compiled.search(line):
                    # 排除注释行
                    stripped = line.strip()
                    if stripped.startswith("//") or stripped.startswith("#") or stripped.startswith("/*") or stripped.startswith("*"):
                        continue
                    issues.append({
                        "id": rule["id"],
                        "name": rule["name"],
                        "severity": rule["severity"],
                        "description": rule["description"],
                        "fix": rule["fix"],
                        "file": filepath,
                        "line": i,
                        "code": stripped[:200],
                    })
                    break  # 每条规则每行只报一次

    return issues


def scan_project(project_path, lang_filter="auto"):
    """扫描整个项目"""
    all_issues = []
    file_count = 0
    scanned_langs = set()

    for root, dirs, files in os.walk(project_path):
        # 跳过不需要扫描的目录
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

        for filename in files:
            if filename in SKIP_FILES:
                continue

            filepath = os.path.join(root, filename)
            ext = Path(filename).suffix.lower()

            if ext in EXT_LANG_MAP:
                file_count += 1
                lang = EXT_LANG_MAP[ext]
                if lang in ("java", "python"):
                    scanned_langs.add(lang)

                issues = scan_file(filepath, RULES, lang_filter)
                all_issues.extend(issues)

    return all_issues, file_count, scanned_langs


def format_text_report(issues, project_path, file_count, scanned_langs):
    """生成文本格式报告"""
    lines = []
    lines.append("=" * 50)
    lines.append("安全扫描报告")
    lines.append("=" * 50)
    lines.append("")
    lines.append(f"扫描目标: {project_path}")
    lines.append(f"扫描时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    langs = ", ".join(sorted(scanned_langs)) if scanned_langs else "未知"
    lines.append(f"项目语言: {langs}")
    lines.append(f"扫描文件数: {file_count}")
    lines.append("")

    if not issues:
        lines.append("未发现安全问题。")
        lines.append("")
        lines.append("=" * 50)
        return "\n".join(lines)

    severity_order = {"high": 0, "medium": 1, "low": 2}
    issues_sorted = sorted(issues, key=lambda x: (severity_order.get(x["severity"], 9), x["file"], x["line"]))

    high_count = sum(1 for i in issues if i["severity"] == "high")
    medium_count = sum(1 for i in issues if i["severity"] == "medium")
    low_count = sum(1 for i in issues if i["severity"] == "low")

    lines.append(f"--- 发现 {len(issues)} 个安全问题 (高危:{high_count} 中危:{medium_count} 低危:{low_count}) ---")
    lines.append("")

    for idx, issue in enumerate(issues_sorted, 1):
        severity_label = {"high": "高危", "medium": "中危", "low": "低危"}.get(issue["severity"], "未知")
        lines.append(f"[{severity_label}] {issue['name']}")
        lines.append(f"  文件: {issue['file']}:{issue['line']}")
        lines.append(f"  描述: {issue['description']}")
        lines.append(f"  代码: {issue['code']}")
        lines.append(f"  修复: {issue['fix']}")
        lines.append("")

    lines.append("=" * 50)
    return "\n".join(lines)


def format_json_report(issues, project_path, file_count, scanned_langs):
    """生成JSON格式报告"""
    return json.dumps({
        "scan_target": project_path,
        "scan_time": datetime.now().isoformat(),
        "project_languages": sorted(list(scanned_langs)),
        "file_count": file_count,
        "total_issues": len(issues),
        "summary": {
            "high": sum(1 for i in issues if i["severity"] == "high"),
            "medium": sum(1 for i in issues if i["severity"] == "medium"),
            "low": sum(1 for i in issues if i["severity"] == "low"),
        },
        "issues": issues,
    }, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser(description="代码安全漏洞扫描工具")
    parser.add_argument("project_path", help="要扫描的项目路径")
    parser.add_argument("--lang", default="auto", choices=["auto", "java", "python"],
                        help="扫描语言 (默认auto自动检测)")
    parser.add_argument("--format", default="text", choices=["text", "json"],
                        help="报告格式 (默认text)")
    parser.add_argument("-o", "--output", help="输出到文件路径")

    args = parser.parse_args()

    project_path = os.path.abspath(args.project_path)
    if not os.path.exists(project_path):
        print(f"错误: 路径不存在: {project_path}")
        sys.exit(1)

    if os.path.isfile(project_path):
        print(f"错误: 请指定项目目录而非文件")
        sys.exit(1)

    print(f"正在扫描: {project_path}")
    issues, file_count, scanned_langs = scan_project(project_path, args.lang)

    if args.format == "json":
        report = format_json_report(issues, project_path, file_count, scanned_langs)
    else:
        report = format_text_report(issues, project_path, file_count, scanned_langs)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"报告已保存到: {args.output}")
    else:
        print(report)

    # 有高危问题则退出码为1
    if any(i["severity"] == "high" for i in issues):
        sys.exit(1)


if __name__ == "__main__":
    main()
