"""去重：双键（源+guid/规范URL 主键，源+归一化标题 次键），状态随 git 持久化。

条目 id = 主键哈希，同时作为 AI Batch 的 custom_id —— 结果合并与重跑天然幂等。
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

from .models import RawItem
from .util import STATE_DIR, canonical_url, load_json, normalize_title, save_json

_STATE_FILE = STATE_DIR / "seen_items.json"


def _h(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def primary_key(item: RawItem) -> str:
    ident = item.guid or canonical_url(item.url)
    return _h(f"{item.source_id}:{ident}")


def secondary_key(item: RawItem) -> str:
    return _h(f"{item.source_id}:t:{normalize_title(item.title)}")


@dataclass
class DedupeResult:
    new_items: list[RawItem]
    seen_count: int


class SeenStore:
    """seen_items.json 的读写封装。值为首次见到的北京日期，供按天数清理。"""

    def __init__(self, path=None):
        self.path = path or _STATE_FILE
        self.data: dict[str, str] = load_json(self.path, {}) or {}

    def filter_new(self, items: list[RawItem], date_bj: str) -> DedupeResult:
        new_items: list[RawItem] = []
        seen = 0
        for item in items:
            pk, sk = primary_key(item), secondary_key(item)
            if pk in self.data or sk in self.data:
                seen += 1
                continue
            self.data[pk] = date_bj
            self.data[sk] = date_bj
            new_items.append(item)
        return DedupeResult(new_items=new_items, seen_count=seen)

    def prune(self, before_date: str) -> int:
        stale = [k for k, v in self.data.items() if v < before_date]
        for k in stale:
            del self.data[k]
        return len(stale)

    def save(self) -> None:
        save_json(self.path, self.data)
