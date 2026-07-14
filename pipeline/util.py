"""通用工具函数。"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

# 桌面 App 通过这两个环境变量把数据/配置重定向到用户目录
# （必须在 import pipeline 之前设置——dedupe/batches 的模块级常量随此求值）；
# 未设置时（本地开发/测试）回落仓库根。
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("DAILY_READING_DATA_DIR", "") or REPO_ROOT / "data")
STATE_DIR = DATA_DIR / "state"
CONFIG_DIR = Path(os.environ.get("DAILY_READING_CONFIG_DIR", "") or REPO_ROOT / "config")
# 用户配置覆盖层目录（App 设置面板写这里）；未设置时与 CONFIG_DIR 相同，
# 此时 *_user.yaml 与出厂文件同目录（开发/云端模式天然无覆盖文件）。
USER_CONFIG_DIR = Path(os.environ.get("DAILY_READING_USER_CONFIG_DIR", "") or CONFIG_DIR)

_TRACKING_PARAMS = re.compile(r"^(utm_|fbclid|gclid|ref$|ref_|spm)", re.I)
_WS = re.compile(r"\s+")


def deep_merge(base: dict, override: dict) -> dict:
    """递归字典合并：override 键胜出，仅 dict 递归，其余类型整值替换。返回新 dict。

    override 值为 None 时不覆盖（用户 YAML 里留了个空节头 `fetch:` 解析为
    None——按"没写"处理，避免把出厂 dict 整段抹掉后下游 .get 崩溃）。
    """
    out = dict(base)
    for k, v in override.items():
        if v is None and k in out:
            continue
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_user_yaml(path: Path) -> dict | None:
    """用户覆盖层 YAML 的 fail-open 读取：不存在/损坏/顶层非映射 → None（告警）。

    可写文件绝不击穿管线——cli/registry/persist/server 的用户层读取统一走这里。
    """
    if not path.exists():
        return None
    try:
        import yaml

        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        if doc is None:
            return None  # 空文件同样按"没写"处理（watchlist 依此回退出厂清单）
        if not isinstance(doc, dict):
            raise ValueError("顶层必须是映射")
        return doc
    except Exception as exc:  # noqa: BLE001 — 用户文件坏了按"没写"处理
        print(f"[config] {path.name} 无效已忽略：{exc}")
        return None


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
