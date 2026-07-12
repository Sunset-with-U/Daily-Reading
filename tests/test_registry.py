"""注册表加载/校验/筛选。"""
import pytest

from pipeline.registry import load_sources, select_sources


def test_load_real_registry():
    sources = load_sources()
    assert len(sources) >= 10
    ids = [s.id for s in sources]
    assert len(ids) == len(set(ids)), "源 id 不得重复"
    pilot = [s for s in sources if s.test_group == "pilot"]
    assert len(pilot) >= 10, "pilot 组至少 10 个试点源"


def test_select_by_test_group():
    sources = load_sources()
    wanted, skipped = select_sources(sources, edition="morning", source_filter="pilot")
    assert all(s.test_group == "pilot" for s in wanted)
    assert len(wanted) >= 10


def test_select_schedule_filtering():
    sources = load_sources()
    wanted_evening, skipped = select_sources(sources, edition="evening")
    # 早报专属源（如人民日报）晚报班次应被跳过
    assert not any(s.id == "rmrb-paper" for s in wanted_evening)
    assert any(r.source_id == "rmrb-paper" and r.status == "skipped" for r in skipped)


def test_twitter_requires_key(monkeypatch, make_source):
    monkeypatch.delenv("TWITTERAPI_IO_KEY", raising=False)
    src = make_source(id="x-macro", method="twitter", url="", handles=["someone"])
    wanted, skipped = select_sources([src], edition="morning")
    assert not wanted
    assert skipped[0].status == "skipped"

    monkeypatch.setenv("TWITTERAPI_IO_KEY", "test-key")
    wanted, skipped = select_sources([src], edition="morning")
    assert len(wanted) == 1


def test_validation_rejects_bad_method(make_source):
    from pipeline.registry import _validate

    with pytest.raises(ValueError):
        _validate(make_source(method="carrier_pigeon"), set())
