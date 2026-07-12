"""去重：双键、幂等、清理。"""
from pipeline.dedupe import SeenStore, primary_key, secondary_key
from pipeline.models import RawItem


def _item(**kw):
    defaults = dict(title="Fed Holds Rates", url="https://ex.com/a?utm_source=x",
                    source_id="src1", guid="")
    defaults.update(kw)
    return RawItem(**defaults)


def test_primary_key_ignores_tracking_params():
    a = _item(url="https://ex.com/a?utm_source=rss&id=1")
    b = _item(url="https://ex.com/a?id=1&utm_medium=feed")
    assert primary_key(a) == primary_key(b)


def test_guid_preferred_over_url():
    a = _item(guid="g-1", url="https://ex.com/a")
    b = _item(guid="g-1", url="https://ex.com/DIFFERENT")
    assert primary_key(a) == primary_key(b)


def test_secondary_key_catches_rotated_urls():
    a = _item(title="Gold Tops $3,900!", url="https://ex.com/v1")
    b = _item(title="gold tops  $3900", url="https://ex.com/v2-rotated")
    assert secondary_key(a) == secondary_key(b)


def test_filter_new_idempotent(tmp_path):
    store = SeenStore(path=tmp_path / "seen.json")
    items = [_item(guid="g1"), _item(guid="g2", title="Another")]
    first = store.filter_new(items, "2026-07-12")
    assert len(first.new_items) == 2
    second = store.filter_new(items, "2026-07-12")
    assert len(second.new_items) == 0
    assert second.seen_count == 2


def test_cross_source_not_deduped(tmp_path):
    store = SeenStore(path=tmp_path / "seen.json")
    a = _item(guid="g1", source_id="src1")
    b = _item(guid="g1", source_id="src2")  # 同 guid 不同源 → 都保留（跨源重复是信号）
    result = store.filter_new([a, b], "2026-07-12")
    assert len(result.new_items) == 2


def test_prune(tmp_path):
    store = SeenStore(path=tmp_path / "seen.json")
    store.filter_new([_item(guid="old")], "2026-05-01")
    store.filter_new([_item(guid="new", title="B")], "2026-07-12")
    removed = store.prune("2026-06-01")
    assert removed == 2  # old 的主键+次键
    assert len(store.data) == 2
