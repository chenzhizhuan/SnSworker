#!/usr/bin/env python3
"""Validate a PPTX package before visual QA and delivery.

Checks ZIP integrity, required OOXML parts, relationship targets, slide-layout
links, content-type overrides, unresolved placeholder text, and optional native
edit baselines. This does not replace rendering or visual review.
"""

from __future__ import annotations

import argparse
import json
import posixpath
import re
import sys
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import unquote
from xml.etree import ElementTree as ET


REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
REQUIRED_PARTS = {
    "[Content_Types].xml",
    "_rels/.rels",
    "ppt/presentation.xml",
    "ppt/_rels/presentation.xml.rels",
}
PLACEHOLDER_RE = re.compile(
    r"\b(?:TODO|FIXME|TBD)\b|Lorem\s+ipsum|\{\{[^{}]+\}\}|\[\[[^\[\]]+\]\]|待补充|待确认",
    re.IGNORECASE,
)


def parse_xml(data: bytes, part: str, errors: list[str]) -> ET.Element | None:
    try:
        return ET.fromstring(data)
    except ET.ParseError as exc:
        errors.append(f"invalid XML in {part}: {exc}")
        return None


def relationship_source(rels_part: str) -> str:
    if rels_part == "_rels/.rels":
        return ""
    marker = "/_rels/"
    if marker not in rels_part or not rels_part.endswith(".rels"):
        return ""
    prefix, filename = rels_part.split(marker, 1)
    return posixpath.join(prefix, filename[:-5])


def relationship_target(rels_part: str, target: str) -> str | None:
    source = relationship_source(rels_part)
    decoded = unquote(target).replace("\\", "/")
    if decoded.startswith("/"):
        candidate = decoded.lstrip("/")
    else:
        candidate = posixpath.join(posixpath.dirname(source), decoded)
    normalized = posixpath.normpath(candidate)
    if normalized == ".." or normalized.startswith("../"):
        return None
    return normalized


def package_summary(path: Path) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    try:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            name_set = set(names)
            duplicate_names = sorted(name for name, count in Counter(names).items() if count > 1)
            if duplicate_names:
                errors.append(f"duplicate ZIP part names: {duplicate_names}")
            corrupt = archive.testzip()
            if corrupt:
                errors.append(f"corrupt ZIP member: {corrupt}")
            missing_required = sorted(REQUIRED_PARTS - name_set)
            if missing_required:
                errors.append(f"missing required OOXML parts: {missing_required}")

            xml_roots: dict[str, ET.Element] = {}
            for name in names:
                if name.lower().endswith((".xml", ".rels")):
                    root = parse_xml(archive.read(name), name, errors)
                    if root is not None:
                        xml_roots[name] = root

            for rels_part, root in xml_roots.items():
                if not rels_part.endswith(".rels"):
                    continue
                for rel in root.findall(f"{{{REL_NS}}}Relationship"):
                    if rel.get("TargetMode") == "External":
                        continue
                    raw_target = rel.get("Target")
                    if not raw_target:
                        errors.append(f"empty relationship target in {rels_part}")
                        continue
                    target = relationship_target(rels_part, raw_target)
                    if target is None:
                        errors.append(f"relationship escapes package in {rels_part}: {raw_target}")
                    elif target not in name_set:
                        errors.append(f"missing relationship target from {rels_part}: {target}")

            content_types = xml_roots.get("[Content_Types].xml")
            if content_types is not None:
                for override in content_types.findall(f"{{{CT_NS}}}Override"):
                    part_name = (override.get("PartName") or "").lstrip("/")
                    if part_name and part_name not in name_set:
                        errors.append(f"content-type override points to missing part: {part_name}")

            slide_parts = sorted(
                (name for name in name_set if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)),
                key=lambda value: int(re.search(r"\d+", posixpath.basename(value)).group()),
            )
            if not slide_parts:
                errors.append("presentation contains no slide parts")

            for slide_part in slide_parts:
                filename = posixpath.basename(slide_part)
                rels_part = posixpath.join(posixpath.dirname(slide_part), "_rels", f"{filename}.rels")
                rels_root = xml_roots.get(rels_part)
                if rels_root is None:
                    errors.append(f"slide is missing relationships: {slide_part}")
                    continue
                layout_links = [
                    rel for rel in rels_root.findall(f"{{{REL_NS}}}Relationship")
                    if (rel.get("Type") or "").endswith("/slideLayout")
                ]
                if len(layout_links) != 1:
                    errors.append(f"slide must have exactly one layout relationship: {slide_part}")

            placeholder_hits: list[dict[str, str]] = []
            for slide_part in slide_parts:
                root = xml_roots.get(slide_part)
                if root is None:
                    continue
                text = " ".join(node.text or "" for node in root.iter() if node.tag.endswith("}t"))
                for match in PLACEHOLDER_RE.finditer(text):
                    placeholder_hits.append({"part": slide_part, "text": match.group(0)})
            if placeholder_hits:
                errors.append(f"unresolved placeholder text: {placeholder_hits}")

            presentation = xml_roots.get("ppt/presentation.xml")
            declared_slides = None
            if presentation is not None:
                slide_list = presentation.find(f"{{{P_NS}}}sldIdLst")
                declared_slides = len(list(slide_list)) if slide_list is not None else 0
                if declared_slides != len(slide_parts):
                    errors.append(
                        f"presentation slide list has {declared_slides}, package has {len(slide_parts)} slide parts"
                    )

            summary = {
                "path": str(path.resolve()),
                "size_bytes": path.stat().st_size,
                "slide_count": len(slide_parts),
                "slide_master_count": sum(bool(re.fullmatch(r"ppt/slideMasters/slideMaster\d+\.xml", name)) for name in name_set),
                "slide_layout_count": sum(bool(re.fullmatch(r"ppt/slideLayouts/slideLayout\d+\.xml", name)) for name in name_set),
                "notes_count": sum(bool(re.fullmatch(r"ppt/notesSlides/notesSlide\d+\.xml", name)) for name in name_set),
                "media_count": sum(name.startswith("ppt/media/") and not name.endswith("/") for name in name_set),
                "errors": errors,
                "warnings": warnings,
            }
            return summary
    except FileNotFoundError:
        return {"path": str(path), "errors": [f"file not found: {path}"], "warnings": []}
    except (OSError, zipfile.BadZipFile) as exc:
        return {"path": str(path), "errors": [f"cannot open PPTX package: {exc}"], "warnings": []}


def compare_baseline(
    current: dict[str, Any],
    original: dict[str, Any],
    *,
    allow_slide_count_change: bool,
    allow_structure_loss: bool,
) -> list[str]:
    errors: list[str] = []
    if original.get("errors"):
        errors.append("original baseline is invalid; cannot compare safely")
        return errors
    if not allow_slide_count_change and current.get("slide_count") != original.get("slide_count"):
        errors.append(
            f"slide count changed: original={original.get('slide_count')} output={current.get('slide_count')}"
        )
    if not allow_structure_loss:
        for field in ("slide_master_count", "slide_layout_count", "notes_count"):
            if current.get(field, 0) < original.get(field, 0):
                errors.append(
                    f"native structure decreased for {field}: original={original.get(field)} output={current.get(field)}"
                )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a generated or edited PPTX package")
    parser.add_argument("pptx", type=Path)
    parser.add_argument("--original", type=Path, help="Optional baseline PPTX for native-edit preservation checks")
    parser.add_argument("--allow-slide-count-change", action="store_true")
    parser.add_argument("--allow-structure-loss", action="store_true")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable result")
    args = parser.parse_args()

    result = package_summary(args.pptx)
    if args.original:
        baseline = package_summary(args.original)
        result["baseline"] = baseline
        result.setdefault("errors", []).extend(
            compare_baseline(
                result,
                baseline,
                allow_slide_count_change=args.allow_slide_count_change,
                allow_structure_loss=args.allow_structure_loss,
            )
        )

    result["status"] = "pass" if not result.get("errors") else "fail"
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif result["status"] == "pass":
        print(
            "PPTX_VALID "
            f"(slides={result.get('slide_count')}, layouts={result.get('slide_layout_count')}, "
            f"masters={result.get('slide_master_count')})"
        )
    else:
        print("PPTX_INVALID")
        for error in result.get("errors", []):
            print(f"- {error}")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
