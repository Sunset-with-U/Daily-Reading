"""runner.execute 路由：实时并发合并 / batch 超时登记 pending / 能力降级。"""
from types import SimpleNamespace

from pipeline.analyze import batches, providers, runner


def _dctx():
    return SimpleNamespace(date_bj="2026-07-12", edition="morning",
                           run_at_utc="2026-07-12T00:00:00Z")


_REQS = [
    {"custom_id": "aaa", "params": {"model": "m", "messages": []}},
    {"custom_id": "bbb", "params": {"model": "m", "messages": []}},
]


def test_realtime_merges_per_request_results(monkeypatch):
    def fake_call(provider, params):
        return {"ok": "text"} if provider == "deepseek" else {"error": "x"}

    monkeypatch.setattr(providers, "call_realtime", fake_call)
    settings = {"ai": {"provider": "deepseek", "mode": "realtime"}}
    results = runner.execute(_REQS, settings, _dctx(), kind="items")
    assert results == {"aaa": {"ok": "text"}, "bbb": {"ok": "text"}}


def test_realtime_isolates_failures(monkeypatch):
    def fake_call(provider, params):
        return {"error": "APIError"}

    monkeypatch.setattr(providers, "call_realtime", fake_call)
    settings = {"ai": {"provider": "anthropic", "mode": "realtime"}}
    results = runner.execute(_REQS, settings, _dctx(), kind="items")
    assert all(r == {"error": "APIError"} for r in results.values())


def test_batch_timeout_registers_pending_with_provider(tmp_path, monkeypatch):
    from pipeline.util import load_json

    monkeypatch.setattr(batches, "_PENDING_FILE", tmp_path / "pending.json")
    monkeypatch.setattr(batches, "submit_for", lambda p, reqs: "batch-t1")
    monkeypatch.setattr(batches, "wait_for", lambda p, bid, t, i: False)
    settings = {"ai": {"provider": "anthropic", "mode": "batch",
                       "batch_poll_timeout_min": 0}}
    results = runner.execute(_REQS, settings, _dctx(), kind="items")
    assert results == {}  # 超时请求不出现在返回值中
    entry = load_json(tmp_path / "pending.json")[0]
    assert entry["batch_id"] == "batch-t1"
    assert entry["provider"] == "anthropic"
    assert entry["kind"] == "items"


def test_batch_unsupported_provider_downgrades_to_realtime(monkeypatch, capsys):
    called = {}

    def fake_call(provider, params):
        called["provider"] = provider
        return {"ok": "t"}

    monkeypatch.setattr(providers, "call_realtime", fake_call)

    def no_batch(*a, **k):
        raise AssertionError("不应走 batch 路径")

    monkeypatch.setattr(batches, "submit_for", no_batch)
    settings = {"ai": {"provider": "gemini", "mode": "batch"}}  # gemini 无 batch
    results = runner.execute(_REQS, settings, _dctx(), kind="items")
    assert called["provider"] == "gemini"
    assert len(results) == 2
    assert "降级实时" in capsys.readouterr().out


def test_collect_pending_skips_entries_without_key(tmp_path, monkeypatch):
    """openai pending 但无 OPENAI_API_KEY → 原样保留，不丢弃。"""
    from pipeline.util import load_json, save_json

    pending_file = tmp_path / "pending.json"
    monkeypatch.setattr(batches, "_PENDING_FILE", pending_file)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    save_json(pending_file, [{"batch_id": "b-openai", "provider": "openai",
                              "kind": "items", "date": "2026-07-12",
                              "edition": "morning"}])
    out = batches.collect_pending()
    assert "仍在处理 1" in out
    assert load_json(pending_file)[0]["batch_id"] == "b-openai"
