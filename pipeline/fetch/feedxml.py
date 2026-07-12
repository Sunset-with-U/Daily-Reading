"""精简 RSS/Atom/RDF 解析器（基于 lxml，替代 feedparser）。

为什么不用 feedparser：其依赖 sgmllib3k 在 setuptools>=78 下无法构建
（2025 起的已知问题），在 CI 与本地都会挂。我们只需要标题/链接/guid/
时间/摘要这几样，lxml 按 localname 匹配即可健壮覆盖 RSS 2.0 / Atom /
RSS 1.0(RDF) 三种格式。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from lxml import etree


@dataclass
class FeedEntry:
    title: str = ""
    link: str = ""
    guid: str = ""
    published: str = ""       # 原始字符串，由调用方用 dateutil 解析
    author: str = ""
    summary_html: str = ""
    content_html: str = ""
    enclosures: list[str] = field(default_factory=list)


def _local(el) -> str:
    try:
        return etree.QName(el).localname.lower()
    except ValueError:
        return ""


def _text(el) -> str:
    return "".join(el.itertext()).strip() if el is not None else ""


def parse_feed(content: bytes) -> list[FeedEntry]:
    """解析 feed 字节流。解析不出任何条目时抛 ValueError。"""
    content = content.lstrip()
    parser = etree.XMLParser(recover=True, resolve_entities=False,
                             no_network=True, huge_tree=False)
    try:
        root = etree.fromstring(content, parser)
    except (etree.XMLSyntaxError, ValueError) as exc:
        raise ValueError(f"feed XML 解析失败: {exc}") from exc
    if root is None:
        raise ValueError("feed XML 解析失败: 空文档")

    root_name = _local(root)
    if root_name == "feed":                      # Atom
        nodes = [el for el in root if _local(el) == "entry"]
        entries = [_parse_atom_entry(el) for el in nodes]
    elif root_name in ("rss", "rdf"):            # RSS 2.0 / RSS 1.0
        nodes = [el for el in root.iter() if _local(el) == "item"]
        entries = [_parse_rss_item(el) for el in nodes]
    else:
        raise ValueError(f"未知的 feed 根元素: <{root_name}>")

    entries = [e for e in entries if e.title or e.link]
    if not entries and not nodes:
        raise ValueError("feed 中没有条目")
    return entries


def _parse_rss_item(item) -> FeedEntry:
    e = FeedEntry()
    for child in item:
        name = _local(child)
        if name == "title":
            e.title = _text(child)
        elif name == "link" and not e.link:
            # RSS: 文本节点；某些混合 feed 用 Atom link@href
            e.link = _text(child) or (child.get("href") or "")
        elif name == "guid":
            e.guid = _text(child)
        elif name in ("pubdate", "date", "published") and not e.published:
            e.published = _text(child)
        elif name in ("creator", "author") and not e.author:
            e.author = _text(child)
        elif name == "description":
            e.summary_html = _text(child)
        elif name == "encoded":                  # content:encoded
            e.content_html = _text(child)
        elif name == "enclosure":
            url = child.get("url")
            if url:
                e.enclosures.append(url)
    return e


def _parse_atom_entry(entry) -> FeedEntry:
    e = FeedEntry()
    fallback_link = ""
    for child in entry:
        name = _local(child)
        if name == "title":
            e.title = _text(child)
        elif name == "link":
            href = child.get("href") or ""
            rel = child.get("rel") or "alternate"
            if rel == "alternate" and href:
                e.link = href
            elif rel == "enclosure" and href:
                e.enclosures.append(href)
            elif href and not fallback_link:
                fallback_link = href
        elif name == "id":
            e.guid = _text(child)
        elif name in ("published", "updated") and not e.published:
            e.published = _text(child)
        elif name == "author":
            names = [el for el in child if _local(el) == "name"]
            e.author = _text(names[0]) if names else _text(child)
        elif name == "summary":
            e.summary_html = _text(child)
        elif name == "content":
            e.content_html = _text(child)
    if not e.link:
        e.link = fallback_link
    return e
