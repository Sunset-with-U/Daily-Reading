"""通用工具函数。"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
STATE_DIR = DATA_DIR / "state"
CONFIG_DIR = REPO_ROOT / "config"

_TRACKING_PARAMS = re.compile(r"^(utm_|fbclid|gclid|ref$|ref_|spm)", re.I)
_WS = re.compile(r"\s+")


def load_json(path: Path, default: Any = None) -> Any:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return default
    return default


def save_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(obj, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )


def canonical_url(url: str) -> str:
    """规范化 URL：去追踪参数、去 fragment、去尾斜杠。"""
    if not url:
        return ""
    try:
        parts = urlsplit(url.strip())
    except ValueError:
        return url.strip()
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
             if not _TRACKING_PARAMS.match(k)]
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path,
                       urlencode(query), ""))


def normalize_title(title: str) -> str:
    """标题归一化（去空白/标点差异），用于次级去重键。"""
    t = title.lower().strip()
    t = re.sub(r"[^\w一-鿿]+", "", t)
    return t


def squeeze_text(text: str, limit: int = 0) -> str:
    """压缩空白并可选截断。"""
    t = _WS.sub(" ", (text or "")).strip()
    if limit and len(t) > limit:
        t = t[:limit].rsplit(" ", 1)[0] if " " in t[:limit] else t[:limit]
    return t


def strip_html(html: str) -> str:
    """轻量去 HTML 标签（适用于 RSS summary 等小片段）。"""
    if not html:
        return ""
    from bs4 import BeautifulSoup

    return BeautifulSoup(html, "lxml").get_text(" ", strip=True)
