#!/usr/bin/env python3
"""
Skill 写入工具
负责创建同事的分身目录结构、元数据管理和版本控制
"""

import sys
import os
import json
import argparse
from pathlib import Path
from datetime import datetime

try:
    from pypinyin import lazy_pinyin
    HAS_PYPINYIN = True
except ImportError:
    HAS_PYPINYIN = False


def slugify(name: str) -> str:
    """
    中文姓名转拼音 slug
    "张三" → "zhang-san"
    "Big Mike" → "big-mike"
    """
    if HAS_PYPINYIN:
        if any('\u4e00' <= c <= '\u9fff' for c in name):
            pinyin_list = lazy_pinyin(name)
            return '-'.join(pinyin_list)

    # 回退方案：手动转小写
    import re
    return re.sub(r'\s+', '-', name.strip()).lower()


def create_colleague_dir(base_dir: str, name: str, force: bool = False) -> dict:
    """
    创建同事分身目录
    返回包含路径信息的字典
    """
    slug = slugify(name)
    colleague_dir = Path(base_dir) / slug

    if colleague_dir.exists() and not force:
        return {
            "status": "exists",
            "slug": slug,
            "dir": str(colleague_dir),
            "message": f"目录已存在: {colleague_dir}（使用 --force 覆盖）"
        }

    colleague_dir.mkdir(parents=True, exist_ok=True)
    versions_dir = colleague_dir / ".versions"
    versions_dir.mkdir(exist_ok=True)

    return {
        "status": "created",
        "slug": slug,
        "dir": str(colleague_dir),
        "versions_dir": str(versions_dir)
    }


def write_meta(colleague_dir: str, meta: dict):
    """写入 meta.json 元数据"""
    meta_path = Path(colleague_dir) / "meta.json"
    meta["updated_at"] = datetime.now().isoformat()
    if "created_at" not in meta:
        meta["created_at"] = meta["updated_at"]

    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


def read_meta(colleague_dir: str) -> dict:
    """读取 meta.json 元数据"""
    meta_path = Path(colleague_dir) / "meta.json"
    if not meta_path.exists():
        return {}
    with open(meta_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def write_skill_file(colleague_dir: str, file_type: str, content: str):
    """
    写入 skill 文件（work.md 或 persona.md）
    自动创建版本快照
    """
    filename = f"{file_type}.md"
    file_path = Path(colleague_dir) / filename

    # 如果文件已存在，创建版本快照
    if file_path.exists():
        snapshot_version(colleague_dir, file_type)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)


def snapshot_version(colleague_dir: str, file_type: str):
    """创建当前文件的版本快照"""
    versions_dir = Path(colleague_dir) / ".versions"
    versions_dir.mkdir(exist_ok=True)

    file_path = Path(colleague_dir) / f"{file_type}.md"
    if not file_path.exists():
        return

    # 生成版本号
    existing = sorted(versions_dir.glob(f"v*_{file_type}.md"))
    if existing:
        last_ver = existing[-1].name.split('_')[0]  # v1.2.0
        parts = last_ver[1:].split('.')
        parts[-1] = str(int(parts[-1]) + 1)
        version = f"v{'.'.join(parts)}"
    else:
        version = "v1.0.0"

    # 复制文件
    import shutil
    snapshot_path = versions_dir / f"{version}_{file_type}.md"
    shutil.copy2(file_path, snapshot_path)

    # 写入版本元数据
    version_meta = {
        "version": version,
        "timestamp": datetime.now().isoformat(),
        "file_type": file_type
    }
    version_meta_path = versions_dir / f"{version}_meta.json"
    with open(version_meta_path, 'w', encoding='utf-8') as f:
        json.dump(version_meta, f, ensure_ascii=False, indent=2)


def list_versions(colleague_dir: str) -> list:
    """列出所有版本"""
    versions_dir = Path(colleague_dir) / ".versions"
    if not versions_dir.exists():
        return []

    versions = []
    for meta_file in sorted(versions_dir.glob("v*_meta.json")):
        with open(meta_file, 'r', encoding='utf-8') as f:
            versions.append(json.load(f))
    return versions


def list_colleagues(base_dir: str) -> list:
    """列出所有已创建的同事分身"""
    base = Path(base_dir)
    if not base.exists():
        return []

    colleagues = []
    for d in sorted(base.iterdir()):
        if d.is_dir() and not d.name.startswith('.') and not d.name == '.versions':
            meta_path = d / "meta.json"
            if meta_path.exists():
                with open(meta_path, 'r', encoding='utf-8') as f:
                    meta = json.load(f)
                meta["dir"] = str(d)
                colleagues.append(meta)
            else:
                colleagues.append({
                    "name": d.name,
                    "slug": d.name,
                    "dir": str(d)
                })
    return colleagues


def main():
    parser = argparse.ArgumentParser(description="Skill 写入工具 - 同事蒸馏器")
    sub = parser.add_subparsers(dest="command")

    # create
    create_cmd = sub.add_parser("create", help="创建同事分身目录")
    create_cmd.add_argument("name", help="同事姓名")
    create_cmd.add_argument("--base-dir", default="colleagues", help="基础目录")
    create_cmd.add_argument("--force", action="store_true", help="覆盖已有目录")

    # write
    write_cmd = sub.add_parser("write", help="写入 skill 文件")
    write_cmd.add_argument("dir", help="同事分身目录路径")
    write_cmd.add_argument("--type", required=True, choices=["work", "persona"], help="文件类型")
    write_cmd.add_argument("--content", help="内容（或从 stdin 读取）")

    # meta
    meta_cmd = sub.add_parser("meta", help="写入/更新元数据")
    meta_cmd.add_argument("dir", help="同事分身目录路径")
    meta_cmd.add_argument("--name", help="姓名")
    meta_cmd.add_argument("--company", help="公司")
    meta_cmd.add_argument("--level", help="职级")
    meta_cmd.add_argument("--role", help="角色")
    meta_cmd.add_argument("--mbti", help="MBTI")
    meta_cmd.add_argument("--notes", help="备注")

    # list
    list_cmd = sub.add_parser("list", help="列出所有同事分身")
    list_cmd.add_argument("--base-dir", default="colleagues", help="基础目录")

    # versions
    ver_cmd = sub.add_parser("versions", help="列出版本历史")
    ver_cmd.add_argument("dir", help="同事分身目录路径")

    args = parser.parse_args()

    if args.command == "create":
        result = create_colleague_dir(args.base_dir, args.name, args.force)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.command == "write":
        content = args.content
        if not content:
            content = sys.stdin.read()
        write_skill_file(args.dir, args.type, content)
        print(f"已写入: {Path(args.dir) / f'{args.type}.md'}")

    elif args.command == "meta":
        meta = read_meta(args.dir)
        if args.name: meta["name"] = args.name
        if args.company: meta["company"] = args.company
        if args.level: meta["level"] = args.level
        if args.role: meta["role"] = args.role
        if args.mbti: meta["mbti"] = args.mbti
        if args.notes: meta["notes"] = args.notes
        write_meta(args.dir, meta)
        print(f"元数据已更新: {Path(args.dir) / 'meta.json'}")

    elif args.command == "list":
        colleagues = list_colleagues(args.base_dir)
        print(json.dumps(colleagues, ensure_ascii=False, indent=2))

    elif args.command == "versions":
        versions = list_versions(args.dir)
        print(json.dumps(versions, ensure_ascii=False, indent=2))

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
