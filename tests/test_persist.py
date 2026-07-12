"""落盘：条目合并、index、瘦身。"""
from pipeline import persist
from pipeline.datectx import DateContext
from pipeline.models import RawItem


def _dctx(edition="morning"):
    return DateContext(date_bj="2026-07-12", edition=edition,
                       run_at_utc="2026-07-11T23:05:00Z", yyyymm="202607", dd="12")


def test_items_merge_across_editions(tmp_path, monkeypatch):
    monkeypatch.setattr(persist, "DATA_DIR", tmp_path)
    item = RawItem(title="T1", url="https://ex.com/1", source_id="s1", guid="g1",
                   content_text="全文内容" * 300)
    rec = persist.item_to_record(item, "id1", {"name_zh": "测试源", "tier": "A"},
                                 "morning", 500, "2026-07-11T23:05:00Z")
    assert len(rec["content_excerpt"]) <= 500
    assert len(rec["_content_full"]) > 500

    persist.write_items(_dctx("morning"), [rec])
    rec2 = dict(rec, id="id2", edition="evening")
    persist.write_items(_dctx("evening"), [rec, rec2])  # id1 重复提交应被合并

    doc = persist.load_items("2026-07-12")
    assert len(doc["items"]) == 2
    assert len(doc["runs"]) == 2


def test_strip_full_content(tmp_path, monkeypatch):
    monkeypatch.setattr(persist, "DATA_DIR", tmp_path)
    item = RawItem(title="T", url="https://ex.com/1", source_id="s1", guid="g1",
                   content_text="内容")
    rec = persist.item_to_record(item, "id1", {}, "morning", 500, "now")
    persist.write_items(_dctx(), [rec])
    persist.strip_full_content("2026-07-12")
    doc = persist.load_items("2026-07-12")
    assert "_content_full" not in doc["items"][0]
    assert doc["items"][0]["content_excerpt"] == "内容"


def test_update_index(tmp_path, monkeypatch):
    monkeypatch.setattr(persist, "DATA_DIR", tmp_path)
    item = RawItem(title="T", url="https://ex.com/1", source_id="s1", guid="g1")
    rec = persist.item_to_record(item, "id1", {}, "morning", 500, "now")
    rec["analysis"] = {"status": "done", "importance": "A"}
    persist.write_items(_dctx(), [rec])
    persist.update_index(_dctx())

    from pipeline.util import load_json

    idx = load_json(tmp_path / "index.json")
    assert idx["latest_date"] == "2026-07-12"
    assert idx["dates"][0]["items"] == 1
    assert idx["dates"][0]["by_importance"] == {"A": 1}
