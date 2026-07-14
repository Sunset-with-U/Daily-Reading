"""JSON"拾荒器"：在结构未知/易变的 JSON 响应里递归寻找文章记录数组。

适用于 gov.cn 政策库这类没有公开文档、字段名可能调整的接口——
只要响应里存在"带标题和链接的对象数组"就能提取。
"""
from __future__ import annotations

from typing import Any

TITLE_KEYS = ("title", "name", "doctitle", "docname", "subject")
URL_KEYS = ("url", "link", "href", "docurl", "puburl", "pub_url", "wwwurl")
DATE_KEYS = ("pubdate", "pub_date", "publish_time", "pubtime", "date",
             "publishdate", "ptime", "display_time", "printdate")
CONTENT_KEYS = ("summary", "content", "description", "abstract", "digest")


def _norm_key(k: str) -> str:
    return k.lower().replace("_", "").replace("-", "")


def _pick(obj: dict, keys: tuple[str, ...]) -> str:
    normed = {_norm_key(k): v for k, v in obj.items()}
    for key in keys:
        val = normed.get(_norm_key(key))
        if isinstance(val, (str, int, float)) and str(val).strip():
            return str(val).strip()
    return ""


def find_records(data: Any, min_count: int = 2) -> list[dict]:
    """递归找到第一个"文章记录数组"（≥min_count 个含标题+链接的 dict）。"""
    best: list[dict] = []

    def walk(node: Any) -> None:
        nonlocal best
        if best:
            return
        if isinstance(node, list):
            hits = [x for x in node if isinstance(x, dict)
                    and _pick(x, TITLE_KEYS) and _pick(x, URL_KEYS)]
            if len(hits) >= min_count:
                best = hits
                return
            for x in node:
                walk(x)
        elif isinstance(node, dict):
            for v in node.values():
                walk(v)

    walk(data)
    return best


def record_fields(rec: dict) -> dict:
    """从记录中提取标准字段。"""
    return {
        "title": _pick(rec, TITLE_KEYS),
        "url": _pick(rec, URL_KEYS),
        "date": _pick(rec, DATE_KEYS),
        "content": _pick(rec, CONTENT_KEYS),
    }
