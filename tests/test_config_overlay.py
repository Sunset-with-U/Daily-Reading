"""用户配置覆盖层：settings 深合并 / sources overrides+extra / watchlist 整替换。"""
from pipeline.util import deep_merge


def test_deep_merge():
    base = {"ai": {"provider": "anthropic", "daily_item_cap": 600}, "fetch": {"workers": 16}}
    over = {"ai": {"provider": "deepseek"}, "extra": 1}
    merged = deep_merge(base, over)
    assert merged["ai"] == {"provider": "deepseek", "daily_item_cap": 600}
    assert merged["fetch"] == {"workers": 16}
    assert merged["extra"] == 1
    assert base["ai"]["provider"] == "anthropic"  # 不改原 dict


def test_deep_merge_replaces_non_dict_values():
    assert deep_merge({"a": [1, 2]}, {"a": [3]}) == {"a": [3]}


def test_deep_merge_none_does_not_clobber():
    # 用户 YAML 空节头（`fetch:` → None）按"没写"处理，不抹掉出厂 dict
    assert deep_merge({"fetch": {"workers": 16}}, {"fetch": None}) \
        == {"fetch": {"workers": 16}}
    # 但 None 可以作为新键存在
    assert deep_merge({}, {"x": None}) == {"x": None}


def test_load_settings_corrupt_overlay_falls_back(tmp_path, monkeypatch, capsys):
    (tmp_path / "settings.yaml").write_text("ai:\n  provider: anthropic\n", encoding="utf-8")
    user = tmp_path / "user"
    user.mkdir()
    (user / "settings_user.yaml").write_text("ai: [broken\n  yaml", encoding="utf-8")
    monkeypatch.setattr("pipeline.cli.CONFIG_DIR", tmp_path)
    monkeypatch.setattr("pipeline.cli.USER_CONFIG_DIR", user)
    from pipeline.cli import load_settings

    s = load_settings()  # 不抛异常
    assert s["ai"]["provider"] == "anthropic"
    assert "已忽略" in capsys.readouterr().out


def test_load_settings_overlay(tmp_path, monkeypatch):
    (tmp_path / "settings.yaml").write_text(
        "ai:\n  provider: anthropic\n  daily_item_cap: 600\n", encoding="utf-8")
    user = tmp_path / "user"
    user.mkdir()
    (user / "settings_user.yaml").write_text(
        "ai:\n  provider: deepseek\n", encoding="utf-8")
    monkeypatch.setattr("pipeline.cli.CONFIG_DIR", tmp_path)
    monkeypatch.setattr("pipeline.cli.USER_CONFIG_DIR", user)
    from pipeline.cli import load_settings

    s = load_settings()
    assert s["ai"]["provider"] == "deepseek"
    assert s["ai"]["daily_item_cap"] == 600


FACTORY_SOURCES = """
defaults:
  timeout_s: 20
sources:
  - id: src-a
    name: A
    method: rss
    url: https://a.example.com/feed
  - id: src-b
    name: B
    method: rss
    url: https://b.example.com/feed
"""


def _write_registry_fixture(tmp_path, monkeypatch, user_yaml: str | None):
    (tmp_path / "sources.yaml").write_text(FACTORY_SOURCES, encoding="utf-8")
    user = tmp_path / "user"
    user.mkdir()
    if user_yaml is not None:
        (user / "sources_user.yaml").write_text(user_yaml, encoding="utf-8")
    monkeypatch.setattr("pipeline.registry.CONFIG_DIR", tmp_path)
    monkeypatch.setattr("pipeline.registry.USER_CONFIG_DIR", user)


def test_sources_overlay_override_and_extra(tmp_path, monkeypatch):
    _write_registry_fixture(tmp_path, monkeypatch, """
overrides:
  src-a:
    enabled: false
extra_sources:
  - id: my-blog
    name: My Blog
    method: rss
    url: https://blog.example.com/rss
""")
    from pipeline.registry import load_sources

    srcs = {s.id: s for s in load_sources()}
    assert srcs["src-a"].enabled is False
    assert srcs["src-b"].enabled is True
    assert srcs["my-blog"].url == "https://blog.example.com/rss"
    assert srcs["my-blog"].timeout_s == 20  # defaults 对 extra 源同样生效


def test_sources_overlay_absent_is_noop(tmp_path, monkeypatch):
    _write_registry_fixture(tmp_path, monkeypatch, None)
    from pipeline.registry import load_sources

    assert sorted(s.id for s in load_sources()) == ["src-a", "src-b"]


def test_sources_overlay_invalid_extra_skipped(tmp_path, monkeypatch, capsys):
    """用户自定义源非法 → 跳过并告警，不击穿 fail-open 管线。"""
    _write_registry_fixture(tmp_path, monkeypatch, """
extra_sources:
  - id: bad-src
    method: carrier_pigeon
    url: https://x.example.com/
  - name: 没有id的源
    method: rss
    url: https://y.example.com/feed
  - id: good-src
    name: Good
    method: rss
    url: https://z.example.com/feed
""")
    from pipeline.registry import load_sources

    ids = [s.id for s in load_sources()]
    assert "good-src" in ids
    assert "bad-src" not in ids
    out = capsys.readouterr().out
    assert out.count("已跳过") == 2


def test_sources_bad_override_falls_back_to_factory(tmp_path, monkeypatch, capsys):
    """坏的用户覆盖 → 忽略覆盖、回退出厂配置，源仍然可用。"""
    _write_registry_fixture(tmp_path, monkeypatch, """
overrides:
  src-a:
    method: carrier_pigeon
""")
    from pipeline.registry import load_sources

    srcs = {s.id: s for s in load_sources()}
    assert srcs["src-a"].method == "rss"  # 出厂值
    assert "已忽略" in capsys.readouterr().out


def test_sources_corrupt_overlay_file_ignored(tmp_path, monkeypatch, capsys):
    _write_registry_fixture(tmp_path, monkeypatch, "overrides: [broken\n  yaml")
    from pipeline.registry import load_sources

    assert sorted(s.id for s in load_sources()) == ["src-a", "src-b"]
    assert "已忽略" in capsys.readouterr().out


def test_watchlist_corrupt_user_file_falls_back(tmp_path, monkeypatch, capsys):
    factory = tmp_path / "factory"
    user = tmp_path / "user"
    data = tmp_path / "data"
    factory.mkdir(), user.mkdir()
    (factory / "watchlist.yaml").write_text(
        "tickers:\n  - {symbol: SPY, name_zh: 标普}\n", encoding="utf-8")
    (user / "watchlist_user.yaml").write_text("tickers: [broken", encoding="utf-8")
    monkeypatch.setattr("pipeline.util.CONFIG_DIR", factory)
    monkeypatch.setattr("pipeline.util.USER_CONFIG_DIR", user)
    monkeypatch.setattr("pipeline.persist.DATA_DIR", data)
    from pipeline import persist
    from pipeline.util import load_json

    persist.write_watchlist_export()
    assert [t["symbol"] for t in load_json(data / "watchlist.json")["tickers"]] == ["SPY"]


def test_watchlist_empty_user_file_falls_back(tmp_path, monkeypatch):
    """空的 watchlist_user.yaml 按"没写"处理 → 仍导出出厂清单（终局评审回归项）。"""
    factory = tmp_path / "factory"
    user = tmp_path / "user"
    data = tmp_path / "data"
    factory.mkdir(), user.mkdir()
    (factory / "watchlist.yaml").write_text(
        "tickers:\n  - {symbol: SPY, name_zh: 标普}\n", encoding="utf-8")
    (user / "watchlist_user.yaml").write_text("", encoding="utf-8")
    monkeypatch.setattr("pipeline.util.CONFIG_DIR", factory)
    monkeypatch.setattr("pipeline.util.USER_CONFIG_DIR", user)
    monkeypatch.setattr("pipeline.persist.DATA_DIR", data)
    from pipeline import persist
    from pipeline.util import load_json

    persist.write_watchlist_export()
    assert [t["symbol"] for t in load_json(data / "watchlist.json")["tickers"]] == ["SPY"]


def test_watchlist_user_replaces_factory(tmp_path, monkeypatch):
    factory = tmp_path / "factory"
    user = tmp_path / "user"
    data = tmp_path / "data"
    factory.mkdir(), user.mkdir()
    (factory / "watchlist.yaml").write_text(
        "tickers:\n  - {symbol: SPY, name_zh: 标普}\n", encoding="utf-8")
    (user / "watchlist_user.yaml").write_text(
        "tickers:\n  - {symbol: GC=F, name_zh: 黄金}\n", encoding="utf-8")
    monkeypatch.setattr("pipeline.util.CONFIG_DIR", factory)
    monkeypatch.setattr("pipeline.util.USER_CONFIG_DIR", user)
    monkeypatch.setattr("pipeline.persist.DATA_DIR", data)
    from pipeline import persist
    from pipeline.util import load_json

    persist.write_watchlist_export()
    doc = load_json(data / "watchlist.json")
    assert [t["symbol"] for t in doc["tickers"]] == ["GC=F"]
