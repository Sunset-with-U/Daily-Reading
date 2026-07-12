"""feedxml：RSS 2.0 / Atom / 容错。"""
from pathlib import Path

import pytest

from pipeline.fetch.feedxml import parse_feed

FIXTURES = Path(__file__).parent / "fixtures"


def test_rss2():
    entries = parse_feed((FIXTURES / "rss/sample_feed.xml").read_bytes())
    assert len(entries) == 3  # 空标题条目由上层过滤，解析层保留 link
    assert entries[0].title.startswith("Fed Holds Rates")
    assert entries[0].guid == "example-fed-2026-001"
    assert entries[0].published == "Fri, 10 Jul 2026 18:05:00 GMT"
    assert "two cuts" in entries[0].summary_html


def test_atom():
    entries = parse_feed((FIXTURES / "rss/sample_atom.xml").read_bytes())
    assert len(entries) == 2
    assert entries[0].link == "https://example.substack.com/p/dollar-milkshake"
    assert entries[0].guid == "substack-post-9001"
    assert entries[0].author == "Some Analyst"
    assert "Full text" in entries[0].content_html
    assert entries[1].published == "2026-07-10T08:00:00Z"  # updated 兜底


def test_garbage_raises():
    with pytest.raises(ValueError):
        parse_feed(b"<html><body>not a feed</body></html>")
    with pytest.raises(ValueError):
        parse_feed(b"total garbage \x00\x01")


def test_bom_and_whitespace_tolerated():
    raw = b"\n\n" + (FIXTURES / "rss/sample_feed.xml").read_bytes()
    assert len(parse_feed(raw)) == 3
