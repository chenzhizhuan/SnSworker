#!/usr/bin/env python3
"""TeleAI Xingchen document parser CLI.

Submit local files or public URLs to the authenticated TeleAI Xingchen
Document Parse async API, poll results in Pull mode, save Markdown plus raw
JSON, and expose batch manifests for agent workflows.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import importlib.util
import json
import os
import re
import sys
import tempfile
import time
import uuid
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

__version__ = "0.5.0"

DEFAULT_BASE_URL = "https://openapi.teleagi.cn"
DEFAULT_REGION = "QG"
DEFAULT_AUTH_EXPIRATION = 43200
DEFAULT_CALLBACK_URL = "http://127.0.0.1/unused"
TASK_PATH = "/aipaas/ocr/v1/xingchenOcr/multimodal"
QUERY_PATH = "/aipaas/lm/v1/asyncResult/query"
DEFAULT_TIMEOUT = 300
DEFAULT_POLL_INTERVAL = 3.0
DEFAULT_WORKERS = 4
DEFAULT_GROUP_SIZE = 10
DEFAULT_PAGES_PER_TASK = 8
DEFAULT_SPLIT_THRESHOLD = 8
RETRY_HTTP_STATUSES = {408, 429, 500, 502, 503, 504}
SUPPORTED_SUFFIXES = {
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".bmp",
    ".gif",
    ".webp",
    ".tif",
    ".tiff",
}
SUCCESS_CODES = {"10000"}
PENDING_CODES = {"990003"}
XINGCHEN_ERROR_CODES = {
    "10000": "调用成功",
    "990003": "任务处理中",
}


class XingchenError(Exception):
    """Raised for API or local validation failures."""


@dataclass
class ParseResult:
    name: str
    source: str
    state: str
    index: int = 1
    filename: Optional[str] = None
    request_id: Optional[str] = None
    markdown_path: Optional[str] = None
    json_path: Optional[str] = None
    total_page_number: Optional[int] = None
    time_second: Optional[float] = None
    markdown: Optional[str] = None
    raw_response: Optional[dict[str, Any]] = None
    error: Optional[str] = None

    def to_status(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "name": self.name,
            "filename": self.filename or display_name(self.source),
            "source": self.source,
            "state": self.state,
            "request_id": self.request_id,
            "markdown_path": self.markdown_path,
            "json_path": self.json_path,
            "total_page_number": self.total_page_number,
            "time_second": self.time_second,
            "error": self.error,
        }


def _ensure_utf8_stdout() -> None:
    """Reconfigure stdout/stderr to UTF-8 to avoid Chinese garbling on Windows.

    Windows terminals often default to GBK/CP936 encoding.  Python's
    print() encodes through the stream encoding, so large Chinese text
    gets mojibake.  Reconfiguring to UTF-8 fixes this for all stdout/stderr
    output.  Safe no-op on macOS/Linux where UTF-8 is already the default.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, Exception):
            pass


def eprint(message: str, quiet: bool = False) -> None:
    if not quiet:
        print(message, file=sys.stderr)


def is_url(value: str) -> bool:
    return value.startswith("http://") or value.startswith("https://")


def safe_name(source: str) -> str:
    parsed = urllib.parse.urlparse(source)
    if parsed.scheme in {"http", "https"}:
        name = Path(parsed.path).name or parsed.netloc
    else:
        name = Path(source.replace("\\", "/")).stem
    name = re.sub(r"[^\w.\-\u4e00-\u9fff]+", "_", name, flags=re.UNICODE).strip("._")
    return name or f"document_{int(time.time())}"


def display_name(source: str) -> str:
    if is_url(source):
        parsed = urllib.parse.urlparse(source)
        return Path(parsed.path).name or source
    return Path(source).name


def is_supported_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES


def discover_inputs(inputs: list[str], recursive: bool = False) -> list[str]:
    discovered: list[str] = []
    for item in inputs:
        if is_url(item):
            discovered.append(item)
            continue
        path = Path(item)
        if path.is_dir():
            iterator = path.rglob("*") if recursive else path.iterdir()
            discovered.extend(str(p) for p in sorted(iterator, key=lambda p: str(p).lower()) if is_supported_file(p))
        else:
            discovered.append(item)
    return discovered


def default_artifact_paths(output: Path, name: str) -> tuple[Path, Path]:
    if output.suffix:
        if output.suffix.lower() == ".json":
            return output.with_suffix(".md"), output
        return output, output.with_suffix(".json")
    doc_dir = output / name
    return doc_dir / f"{name}.md", doc_dir / "result.json"


def batch_artifact_paths(batch_dir: Path, index: int, name: str) -> tuple[Path, Path]:
    doc_dir = batch_dir / f"{index:03d}_{name}"
    return doc_dir / f"{name}.md", doc_dir / "result.json"


def normalize_base_url(base_url: Optional[str]) -> str:
    return (
        base_url
        or os.environ.get("TELEAI_BASE_URL")
        or os.environ.get("XINGCHEN_BASE_URL")
        or DEFAULT_BASE_URL
    ).rstrip("/")


def api_url(base_url: str, path: str) -> str:
    return normalize_base_url(base_url) + path


def validate_local_file(source: str) -> Path:
    path = Path(source)
    if not path.exists():
        raise XingchenError(f"File not found: {source}")
    if not path.is_file():
        raise XingchenError(f"Input is not a file: {source}")
    if path.suffix.lower() not in SUPPORTED_SUFFIXES:
        raise XingchenError(f"Unsupported file type: {path.suffix}")
    return path


def ascii_path_fallback(source: str, args: argparse.Namespace) -> str:
    """Return an ASCII-safe copy path for a local file whose path contains
    non-ASCII characters (Chinese, spaces, special symbols, etc.).

    Some environments (older Windows code pages, mis-configured consoles,
    or shell wrappers) fail to read files whose path contains non-ASCII
    characters. Copying the file into a temporary all-ASCII directory with
    an ASCII-only filename avoids the problem while the parser reads the
    copied file. The original path is preserved for display via
    ParseResult.source.
    """
    if is_url(source):
        return source
    path = Path(source)
    if path.suffix.lower() not in SUPPORTED_SUFFIXES:
        return source
    try:
        if str(path).isascii():
            return source
    except Exception:
        pass
    try:
        temp_root = Path(getattr(args, "temp_dir", None) or tempfile.gettempdir())
        temp_root.mkdir(parents=True, exist_ok=True)
        name = path.stem
        ascii_stem = re.sub(r"[^A-Za-z0-9_.\-]+", "_", name).strip("._") or "doc"
        dest = temp_root / f"{ascii_stem}_{int(time.time() * 1000)}{path.suffix.lower()}"
        dest.write_bytes(path.read_bytes())
        return str(dest)
    except Exception as exc:
        # Fallback to the original path; let the normal error path report it.
        eprint(f"[warn] ASCII path fallback failed ({exc}); using original path", getattr(args, "quiet", False))
        return source


# ---------------------------------------------------------------------------
# PDF split-page support (lazy-loaded PyMuPDF)
# ---------------------------------------------------------------------------

_fitz_module: Any = None


def _fitz():
    """Lazy-load PyMuPDF. Raises XingchenError with install hint on failure."""
    global _fitz_module
    if _fitz_module is not None:
        return _fitz_module
    try:
        import pymupdf
        _fitz_module = pymupdf
        return _fitz_module
    except ImportError:
        raise XingchenError(
            "PyMuPDF is required for PDF splitting. Install it with: pip install PyMuPDF"
        )


def pymupdf_available() -> bool:
    """Return True when PyMuPDF can be imported right now."""
    try:
        _fitz()
        return True
    except XingchenError:
        return False


# ---------------------------------------------------------------------------
# Generic third-party dependency preflight
# ---------------------------------------------------------------------------

# Maps import module name -> pip install package name.
# All third-party (non-stdlib) dependencies used by this script.
THIRD_PARTY_DEPS: dict[str, str] = {
    "pymupdf": "PyMuPDF",
    "cryptography": "cryptography",
}


def check_module_available(module_name: str) -> bool:
    """Return True if a module can be imported right now."""
    try:
        spec = importlib.util.find_spec(module_name)
        return spec is not None
    except (ImportError, ValueError):
        return False


def pip_install_package(package_name: str, quiet: bool = False) -> bool:
    """Try to install a package via pip (or pip3 as fallback).

    Returns True when pip exits 0. Never raises; callers decide how to
    proceed on failure.
    """
    import subprocess

    candidates = [
        [sys.executable, "-m", "pip", "install", "--upgrade", package_name],
        [sys.executable, "-m", "pip", "install", package_name],
    ]
    if not sys.executable or not Path(sys.executable).is_file():
        candidates = [
            ["pip", "install", "--upgrade", package_name],
            ["pip3", "install", "--upgrade", package_name],
        ]
    last_error: Optional[Exception] = None
    for cmd in candidates:
        try:
            eprint(f"[deps] running: {' '.join(cmd)}", quiet)
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            if proc.returncode == 0:
                eprint(f"[deps] {package_name} installed successfully", quiet)
                return True
            last_error = RuntimeError(
                f"pip exited {proc.returncode}: {(proc.stderr or proc.stdout or '').strip()[:400]}"
            )
        except (OSError, subprocess.SubprocessError, subprocess.TimeoutExpired) as exc:
            last_error = exc
            eprint(f"[deps] install attempt failed: {exc}", quiet)
    if last_error is not None:
        eprint(f"[deps] all install attempts for {package_name} failed: {last_error}", quiet)
    return False


def ensure_all_dependencies(quiet: bool = False, auto_install: bool = True) -> bool:
    """Check all third-party dependencies and auto-install missing ones.

    This is the top-level dependency preflight entry point. It checks every
    package listed in THIRD_PARTY_DEPS, installs missing ones (when
    auto_install is True), and returns True only when all are available.
    When auto_install is False it only probes (for --doctor).
    """
    all_ok = True
    for module_name, pip_name in THIRD_PARTY_DEPS.items():
        if check_module_available(module_name):
            continue
        eprint(f"[deps] missing: {module_name} (pip package: {pip_name})", quiet)
        if not auto_install:
            all_ok = False
            continue
        if pip_install_package(pip_name, quiet=quiet):
            # Verify the module is importable after install.
            if not check_module_available(module_name):
                eprint(
                    f"[deps] {pip_name} installed but {module_name} still not importable",
                    quiet,
                )
                all_ok = False
        else:
            all_ok = False
    return all_ok


def pip_install_pymupdf(quiet: bool = False) -> bool:
    """Try to install PyMuPDF via pip. Delegates to the generic installer.

    Returns True when the install succeeded AND PyMuPDF becomes importable
    afterwards. Never raises; callers decide how to proceed on failure.
    """
    if pip_install_package("PyMuPDF", quiet=quiet):
        return pymupdf_available()
    return False


def ensure_pymupdf(quiet: bool = False, auto_install: bool = True) -> bool:
    """Make sure PyMuPDF is importable before splitting a large PDF.

    This is the single entry point for dependency preflight. It never raises;
    it returns True when PyMuPDF is available, False when it is not (after an
    optional automatic install attempt). When auto_install is False it only
    probes, so `--doctor` can report status without side effects.

    Rationale: a large PDF must be split locally before submission, otherwise
    the whole document would be uploaded as one base64 payload and very likely
    time out on the backend. So a missing PyMuPDF must never end up in a
    full-document submission — either install it (auto_install) or stop early
    (caller reports and refuses to submit).
    """
    if pymupdf_available():
        return True
    if auto_install and pip_install_pymupdf(quiet=quiet):
        return True
    return False


def pdf_page_count(pdf_bytes: bytes) -> int:
    """Return the number of pages in a PDF byte string."""
    fitz = _fitz()
    with fitz.open("pdf", pdf_bytes) as doc:
        return doc.page_count


def should_split_pdf(source: str, args: argparse.Namespace) -> bool:
    """Decide whether to split a PDF into page-chunk sub-tasks."""
    if not getattr(args, "split_pages", False):
        return False
    if is_url(source):
        return False  # URL inputs are not split; the service handles them as-is
    path = Path(source)
    if path.suffix.lower() != ".pdf":
        return False  # images are never split
    try:
        pdf_bytes = path.read_bytes()
        pages = pdf_page_count(pdf_bytes)
        threshold = getattr(args, "split_threshold", DEFAULT_SPLIT_THRESHOLD)
        return pages > threshold
    except Exception:
        return False  # if we cannot read the PDF, let the normal path handle it


def split_pdf_to_chunks(pdf_bytes: bytes, pages_per_task: int) -> list[tuple[int, int, bytes]]:
    """Split a PDF into chunks of *pages_per_task* pages.

    Returns a list of (start_page_1based, end_page_1based, pdf_bytes) tuples.
    """
    fitz = _fitz()
    chunks: list[tuple[int, int, bytes]] = []
    with fitz.open("pdf", pdf_bytes) as src:
        total = src.page_count
        for start in range(1, total + 1, pages_per_task):
            end = min(start + pages_per_task - 1, total)
            out = fitz.open()
            for p in range(start - 1, end):
                out.insert_pdf(src, from_page=p, to_page=p)
            chunks.append((start, end, out.tobytes()))
            out.close()
    return chunks


def submit_pdf_bytes(args: argparse.Namespace, pdf_bytes: bytes, seqid: str) -> tuple[str, Optional[str]]:
    """Submit raw PDF bytes as base64 to the API and return (request_id, result_url)."""
    payload: dict[str, Any] = {
        "seqid": seqid,
        "return_mode": 1,
        "html_escape": bool(getattr(args, "html_escape", False)),
        "image_type": 1,
        "image": base64.b64encode(pdf_bytes).decode("ascii"),
        "callback_url": get_callback_url(args),
    }
    if getattr(args, "password", None):
        payload["password"] = args.password
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    url = api_url(args.base_url, TASK_PATH)
    response = request_json_with_retry(
        "POST",
        url,
        body=body,
        headers=build_auth_headers(args, method="POST", path=TASK_PATH, include_content_type=True),
        timeout=args.timeout,
    )
    if not is_success_response(response):
        code = str(response.get("code", ""))
        message = api_message(response) or XINGCHEN_ERROR_CODES.get(code) or "unknown"
        raise XingchenError(f"Submit failed: code={code}, message={message}")
    request_id = response.get("requestId") or response.get("seqid")
    if not request_id:
        data = response.get("data")
        if isinstance(data, dict):
            request_id = data.get("requestId") or data.get("seqid")
    if not request_id:
        raise XingchenError(f"Submit response missing requestId: {response}")
    result_url = response.get("resultUrl")
    return str(request_id), str(result_url) if result_url else None


def poll_result(args: argparse.Namespace, request_id: str, result_url: Optional[str]) -> tuple[Optional[dict[str, Any]], Optional[dict[str, Any]], float]:
    """Poll until the result is ready or timeout.

    Returns (raw_result_or_None, last_response, elapsed_seconds).
    """
    start_time = time.time()
    deadline = start_time + args.timeout
    last_response: Optional[dict[str, Any]] = None
    poll_count = 0
    while time.time() < deadline:
        poll_count += 1
        last_response = query_result(args, request_id, result_url)
        raw_result = completed_payload(last_response)
        if raw_result is not None:
            return raw_result, last_response, time.time() - start_time
        time.sleep(args.poll_interval)
    return None, last_response, time.time() - start_time


def parse_one_split(args: argparse.Namespace) -> ParseResult:
    """Parse a large PDF by splitting it into page-chunk sub-tasks, then merge results."""
    source = args.input
    display_source = getattr(args, "original_source", None) or source
    index = getattr(args, "index", 1)
    name = safe_name(display_source)
    result = ParseResult(
        name=name,
        source=display_source,
        state="running",
        index=index,
        filename=display_name(display_source),
    )
    try:
        # If the path contains non-ASCII characters, parse an ASCII copy
        # instead of the original path to avoid encoding-related read errors.
        read_source = ascii_path_fallback(source, args)
        if read_source != source:
            eprint(f"[path] non-ASCII path detected; using ASCII copy: {read_source}", args.quiet)
        output = Path(args.output)
        if getattr(args, "batch_dir", None):
            markdown_path, json_path = batch_artifact_paths(Path(args.batch_dir), index, name)
        else:
            markdown_path, json_path = default_artifact_paths(output, name)

        # Resume: if the merged Markdown and a split manifest already exist, skip.
        split_manifest_path = markdown_path.parent / "split_manifest.json"
        if args.resume and markdown_path.exists() and split_manifest_path.exists():
            result.state = "skipped"
            result.markdown_path = str(markdown_path)
            result.json_path = str(json_path)
            result.markdown = markdown_path.read_text(encoding="utf-8")
            return result

        pdf_bytes = Path(read_source).read_bytes()
        total_pages = pdf_page_count(pdf_bytes)
        pages_per_task = max(1, getattr(args, "pages_per_task", DEFAULT_PAGES_PER_TASK))
        chunks = split_pdf_to_chunks(pdf_bytes, pages_per_task)
        eprint(f"[split] {source}: {total_pages} pages -> {len(chunks)} tasks ({pages_per_task} pages/task)", args.quiet)

        sub_results: list[dict[str, Any]] = []
        merged_parts: list[str] = []
        all_raw: list[dict[str, Any]] = []
        any_failed = False

        def run_chunk(chunk_idx: int, start: int, end: int, chunk_bytes: bytes) -> dict[str, Any]:
            """Submit and poll one page chunk; return a per-chunk result dict."""
            seqid = f"REQ_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}_{chunk_idx}"
            eprint(f"[split-submit] pages {start}-{end} ({chunk_idx}/{len(chunks)})", args.quiet)
            try:
                request_id, result_url = submit_pdf_bytes(args, chunk_bytes, seqid)
                raw_result, last_response, elapsed = poll_result(args, request_id, result_url)
                if raw_result is None:
                    eprint(f"[split-fail] pages {start}-{end}: timeout ({elapsed:.0f}s)", args.quiet)
                    return {"pages": f"{start}-{end}", "state": "timeout", "request_id": request_id, "elapsed": round(elapsed, 1)}
                md = markdown_from_raw_result(raw_result)
                eprint(f"[split-done] pages {start}-{end}: {elapsed:.0f}s", args.quiet)
                return {"pages": f"{start}-{end}", "state": "done", "request_id": request_id, "elapsed": round(elapsed, 1), "markdown": md, "raw": raw_result}
            except Exception as exc:
                eprint(f"[split-fail] pages {start}-{end}: {exc}", args.quiet)
                return {"pages": f"{start}-{end}", "state": "failed", "error": str(exc)}

        chunk_results: dict[int, dict[str, Any]] = {}
        if len(chunks) > 3:
            # More than 3 chunks: run them with 3 parallel workers.
            with ThreadPoolExecutor(max_workers=3) as executor:
                future_map = {
                    executor.submit(run_chunk, chunk_idx, start, end, chunk_bytes): chunk_idx
                    for chunk_idx, (start, end, chunk_bytes) in enumerate(chunks, start=1)
                }
                for future in as_completed(future_map):
                    chunk_idx = future_map[future]
                    chunk_results[chunk_idx] = future.result()
        else:
            # 3 or fewer chunks: keep serial order for deterministic output.
            for chunk_idx, (start, end, chunk_bytes) in enumerate(chunks, start=1):
                chunk_results[chunk_idx] = run_chunk(chunk_idx, start, end, chunk_bytes)

        # Merge in page order regardless of completion order.
        for chunk_idx in sorted(chunk_results):
            chunk_result = chunk_results[chunk_idx]
            sub_results.append({k: v for k, v in chunk_result.items() if k not in ("markdown", "raw")})
            if chunk_result["state"] == "done":
                merged_parts.append(f"<!-- pages {chunk_result['pages']} -->\n\n{chunk_result['markdown']}")
                all_raw.append(chunk_result["raw"])
            else:
                any_failed = True

        merged_markdown = "\n\n---\n\n".join(merged_parts) if merged_parts else "# OCR Result\n\nAll page chunks failed. See split_manifest.json for details.\n"
        merged_raw = {"split_mode": True, "total_pages": total_pages, "pages_per_task": pages_per_task, "chunks": sub_results, "raw_results": all_raw}

        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_path.write_text(merged_markdown, encoding="utf-8")
        json_path.write_text(json.dumps(merged_raw, ensure_ascii=False, indent=2), encoding="utf-8")

        # Write split manifest for resume support
        split_manifest = {
            "source": source,
            "total_pages": total_pages,
            "pages_per_task": pages_per_task,
            "chunk_count": len(chunks),
            "chunks": sub_results,
        }
        split_manifest_path.write_text(json.dumps(split_manifest, ensure_ascii=False, indent=2), encoding="utf-8")

        if getattr(args, "download_images", False):
            for raw in all_raw:
                download_image_assets(raw, markdown_path.parent, normalize_base_url(args.base_url), args.quiet)

        result.state = "failed" if any_failed and not merged_parts else "partial" if any_failed else "done"
        result.markdown_path = str(markdown_path)
        result.json_path = str(json_path)
        result.markdown = merged_markdown
        result.raw_response = merged_raw
        result.total_page_number = total_pages
        return result
    except Exception as exc:
        result.state = "failed"
        result.error = str(exc)
        return result


def env_first(*names: str) -> Optional[str]:
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return None



_SCRIPT_DIR = Path(__file__).resolve().parent
_CONFIG_DIR = _SCRIPT_DIR.parent / "config"
_CONFIG_ENC_PATH = _CONFIG_DIR / "config.json.enc"
_CONFIG_JSON_PATH = _CONFIG_DIR / "config.json"
_CONFIG_CACHE: Optional[dict[str, str]] = None


def packaged_config() -> dict[str, str]:
    """Load encrypted credentials, then optional plain JSON fallback."""
    global _CONFIG_CACHE
    if _CONFIG_CACHE is not None:
        return _CONFIG_CACHE

    data: dict[str, Any] = {}
    if _CONFIG_ENC_PATH.is_file():
        crypt_path = _SCRIPT_DIR / "config_crypt.py"
        try:
            spec = importlib.util.spec_from_file_location("xingchen_config_crypt", crypt_path)
            if spec is None or spec.loader is None:
                raise ImportError(f"Cannot load config cryptor: {crypt_path}")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            data = module.ConfigCryptor().decrypt_file_to_dict(_CONFIG_ENC_PATH)
        except Exception as exc:
            raise XingchenError(f"Encrypted config load failed: {exc}") from exc
    elif _CONFIG_JSON_PATH.is_file():
        try:
            loaded = json.loads(_CONFIG_JSON_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise XingchenError(f"Plain config load failed: {exc}") from exc
        if isinstance(loaded, dict):
            data = loaded

    _CONFIG_CACHE = {
        key: value
        for key, value in data.items()
        if key in {"app_id", "app_key", "authorization"} and isinstance(value, str)
    }
    return _CONFIG_CACHE

def short_fingerprint(value: Optional[str]) -> str:
    if not value:
        return "none"
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:8]


def get_app_id(args: argparse.Namespace) -> Optional[str]:
    return (
        getattr(args, "app_id", None)
        or getattr(args, "appid", None)
        or env_first("TELEAI_X_APP_ID", "XINGCHEN_APP_ID", "XINGCHEN_X_APP_ID", "X_APP_ID")
        or packaged_config().get("app_id")
    )


def get_api_key(args: argparse.Namespace) -> Optional[str]:
    return (
        getattr(args, "key", None)
        or env_first("XINGCHEN_API_KEY", "TELEAI_X_APP_KEY", "XINGCHEN_APP_KEY")
        or packaged_config().get("app_key")
    )


def get_authorization(args: argparse.Namespace) -> Optional[str]:
    external = getattr(args, "authorization", None) or env_first(
        "TELEAI_AUTHORIZATION",
        "XINGCHEN_AUTHORIZATION",
        "TELEAI_CLOUD_AUTHORIZATION",
    )
    if external:
        return external
    if getattr(args, "key", None) or env_first("XINGCHEN_API_KEY", "TELEAI_X_APP_KEY", "XINGCHEN_APP_KEY"):
        return None
    return packaged_config().get("authorization")


def get_region(args: argparse.Namespace) -> str:
    return getattr(args, "region", None) or env_first("XINGCHEN_REGION", "TELEAI_REGION") or DEFAULT_REGION


def get_auth_expiration(args: argparse.Namespace) -> int:
    value = getattr(args, "auth_expiration", None) or env_first("XINGCHEN_AUTH_EXPIRATION", "TELEAI_AUTH_EXPIRATION")
    return int(value or DEFAULT_AUTH_EXPIRATION)


def hmac_sha256_hex(key: bytes, message: str) -> str:
    return hmac.new(key, message.encode("utf-8"), hashlib.sha256).hexdigest()


def canonical_query(params: dict[str, str]) -> str:
    if not params:
        return ""
    return urllib.parse.urlencode(sorted(params.items()), safe="-_.~")


def make_authorization(
    app_id: str,
    app_key: str,
    method: str,
    path: str,
    query_params: Optional[dict[str, str]] = None,
    *,
    region: str = DEFAULT_REGION,
    expiration: int = DEFAULT_AUTH_EXPIRATION,
    timestamp: Optional[int] = None,
) -> str:
    timestamp = timestamp or int(time.time())
    origin_name = "teleai-cloud-auth-v1"
    signed_headers = "x-app-id"
    auth_prefix = f"{origin_name}/{app_id}/{region}/{timestamp}/{expiration}"
    signing_key = hmac_sha256_hex(app_key.encode("utf-8"), auth_prefix)
    canonical_headers = f"x-app-id:{app_id}"
    canonical_request = "\n".join(
        [
            method.upper(),
            path,
            canonical_query(query_params or {}),
            canonical_headers,
        ]
    )
    signature = hmac_sha256_hex(signing_key.encode("utf-8"), canonical_request)
    return f"{auth_prefix}/{signed_headers}/{signature}"


def get_callback_url(args: argparse.Namespace) -> str:
    return getattr(args, "callback_url", None) or env_first("TELEAI_CALLBACK_URL", "XINGCHEN_CALLBACK_URL") or DEFAULT_CALLBACK_URL


def build_auth_headers(
    args: argparse.Namespace,
    *,
    method: str,
    path: str,
    query_params: Optional[dict[str, str]] = None,
    include_content_type: bool = False,
) -> dict[str, str]:
    app_id = get_app_id(args)
    authorization = get_authorization(args)
    if not app_id:
        raise XingchenError("Missing X-APP-ID. Restore config/config.json.enc, pass --app-id, or set TELEAI_X_APP_ID.")
    if not authorization:
        app_key = get_api_key(args)
        if not app_key:
            raise XingchenError("Missing AppKey/Authorization. Restore config/config.json.enc, pass --key, set XINGCHEN_API_KEY, or set TELEAI_AUTHORIZATION.")
        authorization = make_authorization(
            app_id,
            app_key,
            method,
            path,
            query_params,
            region=get_region(args),
            expiration=get_auth_expiration(args),
        )
    headers = {
        "X-APP-ID": app_id,
        "Authorization": authorization,
    }
    if include_content_type:
        headers["Content-Type"] = "application/json"
    return headers


def build_auth_headers_for_url(
    args: argparse.Namespace,
    method: str,
    url: str,
    *,
    include_content_type: bool = False,
) -> dict[str, str]:
    parsed = urllib.parse.urlparse(url)
    query_params = dict(urllib.parse.parse_qsl(parsed.query, keep_blank_values=True))
    return build_auth_headers(
        args,
        method=method,
        path=parsed.path,
        query_params=query_params,
        include_content_type=include_content_type,
    )


def make_seqid(args: argparse.Namespace, index: int) -> str:
    if args.seqid and int(getattr(args, "input_count", 1)) == 1:
        return args.seqid
    if args.seqid:
        return f"{args.seqid}_{index}"
    return f"REQ_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"


def build_json_payload(args: argparse.Namespace, source: str, index: int) -> dict[str, Any]:
    if args.input_mode == "auto":
        mode = "url" if is_url(source) else "base64"
    else:
        mode = args.input_mode

    payload: dict[str, Any] = {
        "seqid": make_seqid(args, index),
        "return_mode": 1,
        "html_escape": bool(args.html_escape),
    }
    if getattr(args, "page_range", None):
        payload["page_range"] = args.page_range
    if getattr(args, "password", None):
        payload["password"] = args.password

    if mode == "url":
        if not is_url(source):
            raise XingchenError("--input-mode url requires an http(s) URL")
        payload["image_type"] = 0
        payload["image"] = source
    elif mode in {"base64", "file"}:
        if is_url(source):
            raise XingchenError(f"--input-mode {mode} requires a local file")
        path = validate_local_file(source)
        payload["image_type"] = 1
        payload["image"] = base64.b64encode(path.read_bytes()).decode("ascii")
    else:
        raise XingchenError(f"Unsupported input mode: {args.input_mode}")

    callback_url = get_callback_url(args)
    # The API document marks callback_url as required even in Pull mode.
    # Keep this explicit instead of inventing a fake public callback.
    if not callback_url:
        raise XingchenError("Missing callback_url (--callback-url or TELEAI_CALLBACK_URL)")
    payload["callback_url"] = callback_url

    return payload


def request_json(
    method: str,
    url: str,
    *,
    body: Optional[bytes] = None,
    headers: Optional[dict[str, str]] = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    req = urllib.request.Request(url=url, data=body, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise XingchenError(f"HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise XingchenError(f"Network error: {exc.reason}") from exc
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise XingchenError(f"Invalid JSON response: {raw[:500]}") from exc


def request_json_with_retry(
    method: str,
    url: str,
    *,
    body: Optional[bytes] = None,
    headers: Optional[dict[str, str]] = None,
    timeout: int = DEFAULT_TIMEOUT,
    attempts: int = 3,
) -> dict[str, Any]:
    last_error: Optional[Exception] = None
    for attempt in range(1, attempts + 1):
        try:
            return request_json(method, url, body=body, headers=headers, timeout=timeout)
        except XingchenError as exc:
            last_error = exc
            message = str(exc)
            retryable = any(f"HTTP {status}" in message for status in RETRY_HTTP_STATUSES)
            if not retryable or attempt == attempts:
                raise
            time.sleep(min(2**attempt, 8))
    raise last_error or XingchenError("Request failed")


def is_success_response(response: dict[str, Any]) -> bool:
    return str(response.get("code", "")) in SUCCESS_CODES


def api_message(response: dict[str, Any]) -> str:
    return str(response.get("message") or response.get("msg") or "unknown")


def looks_like_result(value: Any) -> bool:
    """Return True when a query response appears to contain a completed OCR payload.

    TeleAI gateway responses are not fully stable across environments. Some
    deployments put the parsed result at data.words_result, some nest it deeper,
    and some return only markdown/pages. Use a recursive detector so a completed
    result is not mistaken for a pending task.
    """
    if isinstance(value, dict):
        words_result = value.get("words_result")
        if isinstance(words_result, list) and words_result:
            return True
        pages = value.get("pages")
        if isinstance(pages, list) and pages:
            return True
        for key in ("markdown", "md", "plain_text", "full_text"):
            item = value.get(key)
            if isinstance(item, str) and item.strip():
                return True
        for item in value.values():
            if looks_like_result(item):
                return True
    elif isinstance(value, list):
        return any(looks_like_result(item) for item in value)
    elif isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith("{") or stripped.startswith("["):
            try:
                return looks_like_result(json.loads(stripped))
            except json.JSONDecodeError:
                return False
    return False


def submit_task(args: argparse.Namespace, source: str, index: int) -> tuple[str, Optional[str]]:
    payload = build_json_payload(args, source, index)
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    url = api_url(args.base_url, TASK_PATH)
    response = request_json_with_retry(
        "POST",
        url,
        body=body,
        headers=build_auth_headers(args, method="POST", path=TASK_PATH, include_content_type=True),
        timeout=args.timeout,
    )
    if not is_success_response(response):
        code = str(response.get("code", ""))
        message = api_message(response) or XINGCHEN_ERROR_CODES.get(code) or "unknown"
        raise XingchenError(f"Submit failed: code={code}, message={message}")
    request_id = response.get("requestId") or response.get("seqid")
    if not request_id:
        data = response.get("data")
        if isinstance(data, dict):
            request_id = data.get("requestId") or data.get("seqid")
    if not request_id:
        raise XingchenError(f"Submit response missing requestId: {response}")
    result_url = response.get("resultUrl")
    return str(request_id), str(result_url) if result_url else None


def append_query_param(url: str, name: str, value: str) -> str:
    parsed = urllib.parse.urlparse(url)
    params = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    params = [(k, v) for k, v in params if k != name]
    params.append((name, value))
    return urllib.parse.urlunparse(parsed._replace(query=urllib.parse.urlencode(params)))


def query_result(args: argparse.Namespace, request_id: str, result_url: Optional[str] = None) -> dict[str, Any]:
    if result_url:
        base_query_url = result_url
    else:
        base_query_url = api_url(args.base_url, QUERY_PATH)
    url = append_query_param(base_query_url, "requestId", request_id)
    return request_json_with_retry(
        "GET",
        url,
        headers=build_auth_headers_for_url(args, "GET", url, include_content_type=False),
        timeout=min(30, args.timeout),
        attempts=2,
    )


def completed_payload(response: dict[str, Any]) -> Optional[dict[str, Any]]:
    code = str(response.get("code", ""))
    if code in PENDING_CODES:
        return None
    if not is_success_response(response):
        raise XingchenError(f"Query failed: code={code}, message={api_message(response)}")

    data = response.get("data")
    if looks_like_result(data):
        return data if isinstance(data, dict) else response
    if looks_like_result(response):
        return response

    flag = response.get("flag")
    message = api_message(response).lower()
    if str(flag) in {"0", "2"} or any(token in message for token in ["processing", "处理中", "执行中", "running"]):
        return None

    # A successful query without a usable result is normally not ready yet.
    return None


def write_timeout_status(
    path: Path,
    *,
    source: str,
    request_id: str,
    elapsed_second: float,
    timeout_second: int,
    last_response: Optional[dict[str, Any]],
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "state": "timeout",
        "source": source,
        "request_id": request_id,
        "elapsed_second": round(elapsed_second, 3),
        "timeout_second": timeout_second,
        "last_response": last_response,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path

def find_first_key(value: Any, keys: set[str]) -> Optional[Any]:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in keys and item not in (None, ""):
                return item
        for item in value.values():
            found = find_first_key(item, keys)
            if found not in (None, ""):
                return found
    elif isinstance(value, list):
        for item in value:
            found = find_first_key(item, keys)
            if found not in (None, ""):
                return found
    return None


def collect_text_blocks(value: Any, lines: list[str]) -> None:
    if isinstance(value, dict):
        text = value.get("text") or value.get("content") or value.get("value")
        if isinstance(text, str) and text.strip():
            lines.append(text.strip())
        html = value.get("html")
        if isinstance(html, str) and html.strip():
            lines.append(html.strip())
        for item in value.values():
            if isinstance(item, (dict, list)):
                collect_text_blocks(item, lines)
    elif isinstance(value, list):
        for item in value:
            collect_text_blocks(item, lines)


def _reflow_long_lines(text: str, max_len: int = 1900) -> str:
    """Re-flow unnaturally long lines in parsed Markdown.

    The cloud parser sometimes returns an entire page as one single line
    (thousands of characters without newlines). Such lines get truncated by
    file readers at 2000 chars, which caused "line truncated" notices and
    forced workarounds (reading raw JSON). This post-processor splits long
    lines at sentence boundaries while preserving existing structure:

    - existing newlines, headings (#), list markers and blank lines are kept
    - long runs are broken at Chinese sentence enders, then at separators
    - line length is capped at max_len (1900 by default, safely below the
      2000-char display cap but keeps sentences intact)
    """
    if not text:
        return text

    import re as _re

    out_lines: list[str] = []
    for raw_line in text.split("\n"):
        line = raw_line.rstrip()
        if not line.strip():
            out_lines.append("")
            continue
        # Never touch headings / list items / code fences / table rows.
        stripped = line.lstrip()
        if (
            stripped.startswith("#")
            or stripped.startswith(("- ", "* ", "+ ", "> ", "|", "```"))
            or _re.match(r"^\d+[.、)]\s", stripped)
        ):
            out_lines.append(line)
            continue

        # Break long plain paragraphs at Chinese/English sentence enders.
        if len(line) <= max_len:
            out_lines.append(line)
            continue

        # Split at sentence enders first, then at separators as fallback.
        ender_parts = _re.split(r"(?<=[。！？；])", line)
        buf = ""
        for part in ender_parts:
            if not part:
                continue
            if len(buf) + len(part) > max_len:
                if buf:
                    out_lines.append(buf.rstrip())
                    buf = ""
                # A single part itself is still too long: break at separators.
                if len(part) > max_len:
                    sep_parts = _re.split(r"(?<=[，、：])", part)
                    buf2 = ""
                    for sp in sep_parts:
                        if len(buf2) + len(sp) > max_len:
                            if buf2:
                                out_lines.append(buf2.rstrip())
                                buf2 = ""
                            # Rare: single token over max_len, hard-slice.
                            while len(sp) > max_len:
                                out_lines.append(sp[:max_len])
                                sp = sp[max_len:]
                        buf2 += sp
                    if buf2:
                        out_lines.append(buf2.rstrip())
                    buf = ""
                else:
                    buf = part
            else:
                buf += part
        if buf:
            out_lines.append(buf.rstrip())

    return "\n".join(out_lines)


def _md_from_structured_pages(raw_result: dict[str, Any]) -> Optional[str]:
    """Rebuild Markdown from the structured per-page content blocks.

    The cloud API returns per-page `content` blocks with a `type` field
    ("title" / "text" / ...). Using those blocks produces natural paragraph
    breaks and heading markers, avoiding the single-line mega-paragraphs that
    caused file-reader truncation. Returns None if no usable structure exists.
    """
    pages = find_first_key(raw_result, {"pages"})
    if not isinstance(pages, list) or not pages:
        return None

    import re as _re

    lines: list[str] = []
    for page in pages:
        if not isinstance(page, dict):
            continue
        content = page.get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            text = block.get("text")
            if not isinstance(text, str) or not text.strip():
                continue
            text = text.strip()
            btype = str(block.get("type") or "").lower()
            if btype == "title":
                # Collapse multiple consecutive '#' runs already present.
                text = _re.sub(r"\s*#+\s*", " ", text).strip()
                lines.append(f"# {text}")
            elif btype in {"table", "form"}:
                lines.append(text)
            elif btype == "image":
                lines.append(f"![{text}]({text})")
            else:
                lines.append(text)
            lines.append("")

    # Trim trailing blank lines, keep single blank between blocks.
    while lines and lines[-1] == "":
        lines.pop()
    if not lines:
        return None

    out = []
    prev_blank = False
    for ln in lines:
        if ln == "":
            if prev_blank:
                continue
            prev_blank = True
        else:
            prev_blank = False
        out.append(ln)
    return "\n".join(out)


def markdown_from_raw_result(raw_result: dict[str, Any]) -> str:
    structured = _md_from_structured_pages(raw_result)
    if structured:
        return structured

    direct = find_first_key(raw_result, {"markdown", "md"})
    if isinstance(direct, str) and direct.strip():
        return _reflow_long_lines(direct)

    text = find_first_key(raw_result, {"plain_text", "full_text"})
    if isinstance(text, str) and text.strip():
        return _reflow_long_lines(text)

    lines: list[str] = []
    collect_text_blocks(raw_result, lines)
    if lines:
        deduped: list[str] = []
        seen: set[str] = set()
        for line in lines:
            if line not in seen:
                seen.add(line)
                deduped.append(line)
        return _reflow_long_lines("\n\n".join(deduped))

    return "# OCR Result\n\nNo Markdown or text field was detected. Raw JSON is preserved in `result.json`.\n"


def total_pages_from_raw(raw_result: dict[str, Any]) -> Optional[int]:
    value = find_first_key(raw_result, {"total_page_number", "total_pages", "page_count"})
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    pages = find_first_key(raw_result, {"pages"})
    if isinstance(pages, list):
        return len(pages)
    return None


def time_second_from_response(response: dict[str, Any]) -> Optional[float]:
    value = find_first_key(response, {"timeSecond", "time_second", "elapsed"})
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None



def collect_image_urls(value: Any, urls: list[str]) -> None:
    if isinstance(value, dict):
        image_url = value.get("image_url")
        if isinstance(image_url, str) and image_url.strip() and image_url != "http://error.com":
            urls.append(image_url.strip())
        for item in value.values():
            if isinstance(item, (dict, list)):
                collect_image_urls(item, urls)
    elif isinstance(value, list):
        for item in value:
            collect_image_urls(item, urls)


def guess_image_extension(url: str, content_type: Optional[str] = None) -> str:
    path = urllib.parse.urlparse(url).path
    suffix = Path(path).suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tif", ".tiff"}:
        return suffix
    if content_type:
        if "png" in content_type:
            return ".png"
        if "gif" in content_type:
            return ".gif"
        if "webp" in content_type:
            return ".webp"
        if "tiff" in content_type or "tif" in content_type:
            return ".tif"
    return ".jpg"


def download_image_assets(raw_response: dict[str, Any], target_dir: Path, base_url: str, quiet: bool = False) -> list[str]:
    urls: list[str] = []
    collect_image_urls(raw_response, urls)
    deduped: list[str] = []
    seen: set[str] = set()
    for url in urls:
        if url not in seen:
            seen.add(url)
            deduped.append(url)
    if not deduped:
        return []
    images_dir = target_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    saved: list[str] = []
    for idx, url in enumerate(deduped, start=1):
        full_url = urllib.parse.urljoin(base_url.rstrip("/") + "/", url)
        try:
            req = urllib.request.Request(full_url, headers={"User-Agent": "xc-doc-parser/0.4"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = resp.read()
                content_type = resp.headers.get("Content-Type")
            suffix = guess_image_extension(full_url, content_type)
            path = images_dir / f"image_{idx:03d}{suffix}"
            path.write_bytes(data)
            saved.append(str(path))
        except Exception as exc:
            eprint(f"[image-skip] {url}: {exc}", quiet)
    return saved


def save_outputs(
    output: Path,
    name: str,
    markdown: str,
    raw_response: dict[str, Any],
) -> tuple[Path, Path]:
    if output.suffix:
        output.parent.mkdir(parents=True, exist_ok=True)
        if output.suffix.lower() == ".json":
            json_path = output
            markdown_path = output.with_suffix(".md")
        else:
            markdown_path = output
            json_path = output.with_suffix(".json")
        markdown_path.write_text(markdown, encoding="utf-8")
        json_path.write_text(json.dumps(raw_response, ensure_ascii=False, indent=2), encoding="utf-8")
        return markdown_path, json_path

    doc_dir = output / name
    doc_dir.mkdir(parents=True, exist_ok=True)
    markdown_path = doc_dir / f"{name}.md"
    json_path = doc_dir / "result.json"
    markdown_path.write_text(markdown, encoding="utf-8")
    json_path.write_text(json.dumps(raw_response, ensure_ascii=False, indent=2), encoding="utf-8")
    return markdown_path, json_path


def parse_one(args: argparse.Namespace) -> ParseResult:
    source = args.input
    display_source = getattr(args, "original_source", None) or source
    index = getattr(args, "index", 1)
    name = safe_name(display_source)
    result = ParseResult(
        name=name,
        source=display_source,
        state="running",
        index=index,
        filename=display_name(display_source),
    )
    try:
        output = Path(args.output)
        if getattr(args, "batch_dir", None):
            markdown_path, json_path = batch_artifact_paths(Path(args.batch_dir), index, name)
        else:
            markdown_path, json_path = default_artifact_paths(output, name)
        if args.resume and markdown_path.exists() and json_path.exists():
            result.state = "skipped"
            result.markdown_path = str(markdown_path)
            result.json_path = str(json_path)
            try:
                result.markdown = markdown_path.read_text(encoding="utf-8")
                result.raw_response = json.loads(json_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                result.markdown = ""
            return result

        eprint(f"[submit] {source}", args.quiet)
        request_id, result_url = submit_task(args, source, index)
        result.request_id = request_id
        start_time = time.time()
        deadline = start_time + args.timeout
        raw_response: Optional[dict[str, Any]] = None
        raw_result: Optional[dict[str, Any]] = None
        poll_count = 0
        while time.time() < deadline:
            poll_count += 1
            raw_response = query_result(args, request_id, result_url)
            elapsed = time.time() - start_time
            code = str(raw_response.get("code", ""))
            message = api_message(raw_response)
            eprint(
                f"[poll] requestId={request_id} count={poll_count} elapsed={elapsed:.0f}s code={code} message={message}",
                args.quiet,
            )
            raw_result = completed_payload(raw_response)
            if raw_result is not None:
                break
            time.sleep(args.poll_interval)
        if raw_result is None or raw_response is None:
            timeout_path = json_path.parent / "timeout_status.json"
            write_timeout_status(
                timeout_path,
                source=source,
                request_id=request_id,
                elapsed_second=time.time() - start_time,
                timeout_second=args.timeout,
                last_response=raw_response,
            )
            result.state = "failed"
            result.json_path = str(timeout_path)
            result.error = f"Timed out waiting for result: {request_id}. Last response saved to {timeout_path}"
            return result

        markdown = markdown_from_raw_result(raw_result)
        if getattr(args, "batch_dir", None):
            markdown_path.parent.mkdir(parents=True, exist_ok=True)
            markdown_path.write_text(markdown, encoding="utf-8")
            json_path.write_text(json.dumps(raw_response, ensure_ascii=False, indent=2), encoding="utf-8")
        else:
            markdown_path, json_path = save_outputs(output, name, markdown, raw_response)
        if getattr(args, "download_images", False):
            download_image_assets(raw_response, markdown_path.parent, normalize_base_url(args.base_url), args.quiet)
        result.state = "done"
        result.markdown_path = str(markdown_path)
        result.json_path = str(json_path)
        result.total_page_number = total_pages_from_raw(raw_result)
        result.time_second = time_second_from_response(raw_response)
        result.markdown = markdown
        result.raw_response = raw_response
        return result
    except Exception as exc:
        result.state = "failed"
        result.error = str(exc)
        return result


def make_batch_id() -> str:
    return time.strftime("batch_%Y%m%d_%H%M%S")


def batch_dir_for(output: Path, batch_id: str) -> Path:
    return output / batch_id


def write_manifest(batch_dir: Path, batch_id: str, results: list[ParseResult]) -> Path:
    ordered = sorted(results, key=lambda item: item.index)
    completed = sum(1 for result in ordered if result.state in {"done", "skipped"})
    failed = sum(1 for result in ordered if result.state == "failed")
    manifest = {
        "batch_id": batch_id,
        "total": len(ordered),
        "completed": completed,
        "failed": failed,
        "documents": [result.to_status() for result in ordered],
    }
    batch_dir.mkdir(parents=True, exist_ok=True)
    path = batch_dir / "manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def print_batch_summary(manifest_path: Path, results: list[ParseResult]) -> None:
    ordered = sorted(results, key=lambda item: item.index)
    completed = sum(1 for result in ordered if result.state in {"done", "skipped"})
    failed = sum(1 for result in ordered if result.state == "failed")
    summary = {
        "state": "completed" if failed == 0 else "partial_failed",
        "total": len(ordered),
        "completed": completed,
        "failed": failed,
        "manifest_path": str(manifest_path),
        "documents": [result.to_status() for result in ordered],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def load_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise XingchenError(f"Manifest not found: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise XingchenError(f"Invalid manifest JSON: {path}") from exc


def parse_index_list(value: str) -> set[int]:
    indexes: set[int] = set()
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start, end = part.split("-", 1)
            indexes.update(range(int(start), int(end) + 1))
        else:
            indexes.add(int(part))
    return indexes


def selected_documents(args: argparse.Namespace, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    documents = manifest.get("documents")
    if not isinstance(documents, list):
        raise XingchenError("Manifest missing documents list")
    ordered = sorted((doc for doc in documents if isinstance(doc, dict)), key=lambda item: int(item.get("index", 0)))
    if args.list:
        return ordered
    if args.index:
        wanted = parse_index_list(args.index)
        return [doc for doc in ordered if int(doc.get("index", 0)) in wanted]
    if args.group is not None:
        group_size = max(1, int(args.group_size))
        start = (int(args.group) - 1) * group_size
        end = start + group_size
        return ordered[start:end]
    return ordered


def read_command(args: argparse.Namespace) -> int:
    try:
        manifest_path = Path(args.batch)
        manifest = load_manifest(manifest_path)
        docs = selected_documents(args, manifest)
        if args.list:
            rows = [
                {
                    "index": doc.get("index"),
                    "filename": doc.get("filename") or doc.get("name"),
                    "state": doc.get("state"),
                    "request_id": doc.get("request_id"),
                    "markdown_path": doc.get("markdown_path"),
                    "json_path": doc.get("json_path"),
                    "error": doc.get("error"),
                }
                for doc in docs
            ]
            print(json.dumps(rows, ensure_ascii=False, indent=2))
            return 0
        chunks: list[str] = []
        for doc in docs:
            markdown_path = doc.get("markdown_path")
            if not markdown_path:
                continue
            path = Path(str(markdown_path))
            if not path.exists():
                chunks.append(
                    f"## Document {doc.get('index')}: {doc.get('filename') or doc.get('name')}\n\n"
                    f"requestId: {doc.get('request_id')}\n\n"
                    f"source: {doc.get('source')}\n\n"
                    f"markdown_path: {markdown_path}\n\n"
                    f"error: markdown file not found\n"
                )
                continue
            chunks.append(
                f"## Document {doc.get('index')}: {doc.get('filename') or doc.get('name')}\n\n"
                f"requestId: {doc.get('request_id')}\n\n"
                f"source: {doc.get('source')}\n\n"
                f"markdown_path: {markdown_path}\n\n"
                f"{path.read_text(encoding='utf-8')}\n"
            )
        print("\n---\n\n".join(chunks))
        return 0
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def credential_source(args: argparse.Namespace) -> str:
    if getattr(args, "authorization", None) or env_first("TELEAI_AUTHORIZATION", "XINGCHEN_AUTHORIZATION", "TELEAI_CLOUD_AUTHORIZATION"):
        return "external_authorization"
    if getattr(args, "app_id", None) or getattr(args, "appid", None) or getattr(args, "key", None):
        return "cli"
    if env_first("TELEAI_X_APP_ID", "XINGCHEN_APP_ID", "XINGCHEN_X_APP_ID", "X_APP_ID", "XINGCHEN_API_KEY", "TELEAI_X_APP_KEY", "XINGCHEN_APP_KEY"):
        return "env"
    config = packaged_config()
    if config.get("app_id") and (config.get("app_key") or config.get("authorization")):
        return "encrypted_config" if _CONFIG_ENC_PATH.is_file() else "plain_config"
    return "missing"


def doctor(args: argparse.Namespace) -> int:
    base_url = normalize_base_url(args.base_url)
    output = Path(args.output)
    target = output if not output.suffix else output.parent
    try:
        target.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(f"failed: output is not writable: {exc}")
        return 1
    app_id = get_app_id(args)
    authorization = get_authorization(args)
    app_key = get_api_key(args) if not authorization else None
    print(f"xc-doc-parser {__version__}")
    print("mode: teleai_xingchen_cloud")
    print("auth: teleai-cloud-auth-v1")
    print(f"credential_source: {credential_source(args)}")
    print(f"app_id_configured: {bool(app_id)}")
    print(f"app_id_fingerprint: {short_fingerprint(app_id)}")
    print(f"app_key_configured: {bool(app_key)}")
    print(f"authorization_configured: {bool(authorization)}")
    print(f"callback_url_configured: {bool(get_callback_url(args))}")
    print(f"base_url: {base_url}")
    print(f"submit_endpoint: {base_url}{TASK_PATH}")
    print(f"query_endpoint: {base_url}{QUERY_PATH}?requestId={{requestId}}")
    print(f"region: {get_region(args)}")
    print(f"auth_expiration: {get_auth_expiration(args)}")
    print(f"output_writable: {target}")
    # Dependency preflight: report ALL third-party dependency availability
    # without installing. --doctor is a read-only probe; auto-install only
    # happens during a real parse in main().
    all_deps_ok = ensure_all_dependencies(quiet=True, auto_install=False)
    for module_name, pip_name in THIRD_PARTY_DEPS.items():
        print(f"{module_name}_available: {check_module_available(module_name)}")
    print(f"all_dependencies_available: {all_deps_ok}")
    return 0 if app_id and (authorization or app_key) and all_deps_ok else 1


def build_query_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Query one TeleAI Xingchen async requestId once and print raw JSON.")
    parser.add_argument("--request-id", required=True, help="requestId returned by submit endpoint")
    parser.add_argument("--result-url", help="Optional resultUrl returned by submit endpoint")
    parser.add_argument("--base-url", help=f"TeleAI API base URL (default {DEFAULT_BASE_URL})")
    parser.add_argument("--app-id", help="TeleAI X-APP-ID header; or set TELEAI_X_APP_ID")
    parser.add_argument("--appid", help="Compatibility alias for --app-id")
    parser.add_argument("--key", help="TeleAI X-APP-KEY; or set XINGCHEN_API_KEY")
    parser.add_argument("--authorization", help="Complete TeleAI Authorization header; or set TELEAI_AUTHORIZATION")
    parser.add_argument("--region", help=f"Authorization region (default {DEFAULT_REGION})")
    parser.add_argument("--auth-expiration", type=int, help="Authorization expiration seconds")
    parser.add_argument("--timeout", type=int, default=30, help="HTTP request timeout seconds")
    return parser


def query_command(args: argparse.Namespace) -> int:
    try:
        args.base_url = normalize_base_url(args.base_url)
        response = query_result(args, args.request_id, args.result_url)
        print(json.dumps(response, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def build_read_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read parsed documents from a batch manifest.")
    parser.add_argument("--batch", required=True, help="Path to manifest.json")
    parser.add_argument("--list", action="store_true", help="List documents in the manifest")
    parser.add_argument("--index", help="Document indexes to read, e.g. 1,3,5 or 1-5")
    parser.add_argument("--group", type=int, help="1-based group number to read")
    parser.add_argument("--group-size", type=int, default=DEFAULT_GROUP_SIZE, help="Documents per group")
    return parser


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Parse documents with the TeleAI Xingchen async API.")
    parser.add_argument("inputs", nargs="*", help="Local file(s), directory, or public http(s) URL")
    parser.add_argument("--output", "-o", default="./output", help="Output file or directory")
    parser.add_argument("--base-url", help=f"TeleAI API base URL (default {DEFAULT_BASE_URL})")
    parser.add_argument("--app-id", help="TeleAI X-APP-ID header; or set TELEAI_X_APP_ID")
    parser.add_argument("--appid", help="Compatibility alias for --app-id")
    parser.add_argument("--key", help="TeleAI X-APP-KEY; or set XINGCHEN_API_KEY")
    parser.add_argument("--authorization", help="Complete TeleAI Authorization header; or set TELEAI_AUTHORIZATION")
    parser.add_argument("--region", help=f"Authorization region (default {DEFAULT_REGION})")
    parser.add_argument("--auth-expiration", type=int, help="Authorization expiration seconds")
    parser.add_argument("--callback-url", help=f"callback_url field (default {DEFAULT_CALLBACK_URL})")
    parser.add_argument("--seqid", help="Optional request seqid. In batch mode, _<index> is appended.")
    parser.add_argument(
        "--input-mode",
        choices=["auto", "url", "base64", "file"],
        default="auto",
        help="auto maps URLs to image_type=0 and local files to base64 image_type=1; file is an alias of base64",
    )
    parser.add_argument(
        "--html-escape",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Send html_escape true/false. Default false so Markdown/HTML remain readable.",
    )
    parser.add_argument("--page-range", help="Optional page range passthrough, e.g. 1-5")
    parser.add_argument("--password", help="Password passthrough for encrypted PDFs")
    parser.add_argument("--download-images", action="store_true", help="Download image_url assets returned in result JSON")
    parser.add_argument("--recursive", action="store_true", help="Recurse into input directories")
    parser.add_argument("--workers", "-w", type=int, default=DEFAULT_WORKERS, help="Parallel workers")
    parser.add_argument("--resume", action="store_true", help="Skip outputs already present")
    parser.add_argument(
        "--split-pages",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Split large PDFs into page-chunk sub-tasks to avoid timeout (default: on)",
    )
    parser.add_argument(
        "--pages-per-task",
        type=int,
        default=DEFAULT_PAGES_PER_TASK,
        help=f"Pages per sub-task when splitting (default {DEFAULT_PAGES_PER_TASK}, max 8)",
    )
    parser.add_argument(
        "--split-threshold",
        type=int,
        default=DEFAULT_SPLIT_THRESHOLD,
        help=f"Minimum page count to trigger splitting (default {DEFAULT_SPLIT_THRESHOLD})",
    )
    parser.add_argument(
        "--view",
        choices=["markdown", "json"],
        default=None,
        help="Output view: markdown content or raw result JSON",
    )
    parser.add_argument("--stdout", action="store_true", help="Print Markdown to stdout for single input (use --view markdown instead; default is JSON status summary to avoid terminal encoding issues)")
    parser.add_argument("--json", dest="as_json", action="store_true", help="Print raw result JSON or status JSON")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="Task timeout seconds")
    parser.add_argument("--poll-interval", type=float, default=DEFAULT_POLL_INTERVAL, help="Polling interval seconds")
    parser.add_argument("--doctor", action="store_true", help="Check configuration and exit")
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress progress logs")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    _ensure_utf8_stdout()

    # ------------------------------------------------------------------
    # Dependency preflight: check ALL third-party dependencies before any
    # work begins. Auto-install missing ones so the script can proceed
    # without manual intervention. This covers PyMuPDF (PDF splitting)
    # and cryptography (credential decryption).
    # ------------------------------------------------------------------
    if not ensure_all_dependencies(auto_install=True):
        print(
            "error: one or more required third-party dependencies are missing "
            "and could not be auto-installed. See [deps] messages above.",
            file=sys.stderr,
        )
        return 1

    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "read":
        read_parser = build_read_parser()
        return read_command(read_parser.parse_args(argv[1:]))
    if argv and argv[0] == "query":
        query_parser = build_query_parser()
        return query_command(query_parser.parse_args(argv[1:]))

    parser = build_parser()
    args = parser.parse_args(argv)
    args.base_url = normalize_base_url(args.base_url)
    if args.view == "json":
        args.as_json = True
    if args.view == "markdown":
        args.stdout = True
    if args.doctor:
        return doctor(args)
    if not args.inputs:
        parser.error("input is required unless --doctor is used")

    discovered = discover_inputs(args.inputs, recursive=args.recursive)
    if not discovered:
        print("error: no supported inputs found", file=sys.stderr)
        return 1
    if len(discovered) > 1 and Path(args.output).suffix:
        print("error: --output must be a directory when parsing multiple inputs", file=sys.stderr)
        return 1

    # NOTE: All third-party dependency checks (including PyMuPDF) are already
    # handled by ensure_all_dependencies() at the top of main(). The old
    # per-PDF PyMuPDF preflight is no longer needed here.

    args.input_count = len(discovered)
    output = Path(args.output)
    is_batch = len(discovered) > 1
    batch_id = make_batch_id() if is_batch else ""
    batch_dir = batch_dir_for(output, batch_id) if is_batch else None
    results: list[ParseResult] = []

    def run_one(index_source: tuple[int, str]) -> ParseResult:
        index, source = index_source
        local_args = argparse.Namespace(**vars(args))
        local_args.input = source
        local_args.index = index
        local_args.batch_dir = str(batch_dir) if batch_dir else None
        # If the path contains non-ASCII characters, parse an ASCII copy
        # instead of the original path to avoid encoding-related read errors.
        normalized_source = ascii_path_fallback(source, local_args)
        if normalized_source != source:
            eprint(f"[path] non-ASCII path detected; using ASCII copy: {normalized_source}", args.quiet)
            # Keep the original path for display, use the ASCII copy for reading.
            local_args.original_source = source
        local_args.input = normalized_source
        # Dispatch to split-page mode for large local PDFs
        if should_split_pdf(normalized_source, local_args):
            # Clamp pages_per_task to 8 max
            local_args.pages_per_task = min(max(1, local_args.pages_per_task), 8)
            return parse_one_split(local_args)
        return parse_one(local_args)

    indexed_sources = list(enumerate(discovered, start=1))
    if len(indexed_sources) == 1 or args.workers <= 1:
        for item in indexed_sources:
            results.append(run_one(item))
    else:
        with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
            futures = {executor.submit(run_one, item): item for item in indexed_sources}
            for future in as_completed(futures):
                results.append(future.result())

    results = sorted(results, key=lambda result: result.index)
    success_states = {"done", "skipped", "partial"}
    ok = all(result.state in success_states for result in results)

    if is_batch:
        assert batch_dir is not None
        manifest_path = write_manifest(batch_dir, batch_id, results)
        print_batch_summary(manifest_path, results)
        return 0 if ok else 1

    result = results[0]
    if args.as_json:
        if result.state == "done" and result.raw_response:
            print(json.dumps(result.raw_response, ensure_ascii=False, indent=2))
        else:
            print(json.dumps(result.to_status(), ensure_ascii=False, indent=2))
    elif args.stdout or args.view == "markdown":
        # Explicit request to print Markdown to stdout.
        _ensure_utf8_stdout()
        print(result.markdown or "")
    else:
        # Default: print JSON status summary (not raw Markdown) to avoid
        # terminal encoding issues (e.g. Chinese garbling on Windows).
        # The agent should use the Read tool on markdown_path to get the
        # Markdown content without terminal encoding problems.
        print(json.dumps(result.to_status(), ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
