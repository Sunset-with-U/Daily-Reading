"""AI 分析层：schema 钳制、报告输入压缩、batch 合并与断点续传（全 mock，不打网络）。"""
import json

import pytest

from pipeline.analyze.schemas import ITEM_SCHEMA, REPORT_SCHEMA, clamp_item_analysis


# ── schema 合规性 ────────────────────────────────────────────

def _assert_strict(schema, path="$"):
    """structured outputs 要求：object 全部 additionalProperties:false + 列全 required。"""
    if schema.get("type") == "object":
        assert schema.get("additionalProperties") is False, f"{path} 缺 additionalProperties:false"
        assert set(schema.get("required", [])) == set(schema.get("properties", {})), \
            f"{path} required 未列全"
        for k, v in schema.get("properties", {}).items():
            _assert_strict(v, f"{path}.{k}")
    if schema.get("type") == "array":
        _assert_strict(schema.get("items", {}), f"{path}[]")
    for sub in schema.get("anyOf", []):
        _assert_strict(sub, f"{path}|anyOf")


def test_schemas_are_strict():
    _assert_strict(ITEM_SCHEMA)
    _assert_strict(REPORT_SCHEMA)


def test_clamp_strips_deep_for_low_importance():
    obj = {"summary_zh": "x", "importance": "B", "markets": ["宏观"] * 5,
           "tags": ["a"] * 10, "content_type": "新闻",
           "deep": {"assessment_zh": "y", "implications": []}}
    out = clamp_item_analysis(obj)
    assert out["deep"] is None
    assert len(out["tags"]) <= 6
    assert len(out["markets"]) <= 3


def test_clamp_keeps_deep_for_s_level():
    obj = {"summary_zh": "x", "importance": "S", "markets": [], "tags": [],
           "content_type": "新闻",
           "deep": {"assessment_zh": "y", "implications": [{}] * 5}}
    out = clamp_item_analysis(obj)
    assert out["deep"] is not None
    assert len(out["deep"]["implications"]) <= 3
    assert out["markets"] == ["其他"]  # 空市场兜底


# ── 报告输入压缩 ────────────────────────────────────────────

def _fake_doc(n_s=2, n_a=5, n_b=50, n_c=100):
    items = []
    grades = [("S", n_s), ("A", n_a), ("B", n_b), ("C", n_c)]
    i = 0
    for grade, n in grades:
        for _ in range(n):
            i += 1
            items.append({
                "id": f"id{i}", "title": f"标题{i}" * 5,
                "source_name_zh": "测试源", "published_at": "2026-07-12T08:00:00+08:00",
                "analysis": {
                    "status": "done", "importance": grade,
                    "markets": ["宏观"], "summary_zh": "摘要内容" * 20,
                    "deep": ({"assessment_zh": "评价" * 30, "implications": [
                        {"direction": "利多", "assets": ["黄金"],
                         "timeframe": "短期", "confidence": "中"}]}
                             if grade in "SA" else None),
                },
            })
    return {"date": "2026-07-12", "items": items}


def _dctx():
    from pipeline.datectx import DateContext

    return DateContext(date_bj="2026-07-12", edition="morning",
                       run_at_utc="2026-07-11T23:05:00Z", yyyymm="202607", dd="12")


def test_report_input_contains_tiers():
    from pipeline.analyze.report import build_report_input

    settings = {"ai": {"report_input_budget_tokens": 120000},
                "report": {"editions": {"morning": "早报"}}}
    text, stats = build_report_input(_dctx(), settings, _fake_doc(),
                                     {"quotes": [{"id": "spx", "price": 6000}], "_meta": {}})
    assert "重要信息条目" in text and "[1]" in text
    assert "次要条目" in text and "B 级" in text
    assert "6000" in text            # 市场快照进入输入
    assert stats["S"] == 2 and stats["A"] == 5 and stats["B"] == 50


def test_report_input_respects_budget():
    from pipeline.analyze.report import build_report_input

    settings = {"ai": {"report_input_budget_tokens": 2000},  # 极小预算
                "report": {"editions": {}}}
    text, stats = build_report_input(_dctx(), settings, _fake_doc(n_b=500), None)
    assert len(text) <= int(2000 * 1.2) + 100
    assert stats["input_chars"] == len(text)


# ── batch 合并 / 断点续传（mock anthropic 客户端） ─────────────

class _FakeBatches:
    def __init__(self, state):
        self.state = state

    def create(self, requests):
        self.state["submitted"] = requests
        return type("B", (), {"id": "batch_test_001"})()

    def retrieve(self, batch_id):
        status = self.state.get("status", "ended")
        counts = type("C", (), {"processing": 0, "succeeded": 1, "errored": 0})()
        return type("B", (), {"id": batch_id, "processing_status": status,
                              "request_counts": counts})()

    def results(self, batch_id):
        for cid, payload in self.state.get("results", {}).items():
            usage = type("U", (), {"input_tokens": 100, "output_tokens": 50})()
            if payload is None:
                result = type("R", (), {"type": "errored", "error": type("E", (), {"type": "invalid_request"})()})()
            else:
                block = type("T", (), {"type": "text", "text": json.dumps(payload, ensure_ascii=False)})()
                msg = type("M", (), {"content": [block], "usage": usage})()
                result = type("R", (), {"type": "succeeded", "message": msg})()
            yield type("W", (), {"custom_id": cid, "result": result})()


@pytest.fixture
def fake_anthropic(monkeypatch):
    state = {}

    class FakeClient:
        def __init__(self):
            self.messages = type("M", (), {"batches": _FakeBatches(state)})()

    from pipeline.analyze import batches as b

    monkeypatch.setattr(b, "_client", lambda: FakeClient())
    return state


def test_analyze_items_end_to_end(fake_anthropic, tmp_path, monkeypatch):
    from pipeline import persist
    from pipeline.analyze.item_analysis import analyze_items

    monkeypatch.setattr(persist, "DATA_DIR", tmp_path)
    doc = {"date": "2026-07-12", "runs": [], "items": [
        {"id": "aaa", "title": "T1", "source_name_zh": "s", "category": "cn_media",
         "tier": "A", "_content_full": "内容", "analysis": {"status": "pending"}},
        {"id": "bbb", "title": "T2", "source_name_zh": "s", "category": "cn_media",
         "tier": "A", "analysis": {"status": "pending"}},
    ]}
    persist.save_items_doc("2026-07-12", doc)

    fake_anthropic["results"] = {
        "aaa": {"summary_zh": "摘要", "importance": "A", "markets": ["宏观"],
                "tags": ["测试"], "content_type": "新闻",
                "deep": {"assessment_zh": "评", "implications": []}},
        "bbb": None,  # errored
    }
    settings = {"ai": {"item_model": "claude-haiku-4-5", "daily_item_cap": 600,
                       "batch_poll_timeout_min": 1, "batch_poll_interval_s": 1}}
    out = analyze_items(_dctx(), settings)
    assert "完成 1" in out and "失败 1" in out

    saved = persist.load_items("2026-07-12")
    by_id = {it["id"]: it for it in saved["items"]}
    assert by_id["aaa"]["analysis"]["status"] == "done"
    assert by_id["aaa"]["analysis"]["importance"] == "A"
    assert by_id["bbb"]["analysis"]["status"] == "failed"
    assert by_id["bbb"]["analysis"]["attempts"] == 1
    # 提交的请求带 structured output
    req = fake_anthropic["submitted"][0]
    assert req["params"]["output_config"]["format"]["type"] == "json_schema"


def test_analyze_timeout_registers_pending(fake_anthropic, tmp_path, monkeypatch):
    from pipeline import persist
    from pipeline.analyze import batches as b
    from pipeline.analyze.item_analysis import analyze_items
    from pipeline.util import load_json

    monkeypatch.setattr(persist, "DATA_DIR", tmp_path)
    monkeypatch.setattr(b, "_PENDING_FILE", tmp_path / "pending.json")
    persist.save_items_doc("2026-07-12", {"date": "2026-07-12", "runs": [], "items": [
        {"id": "aaa", "title": "T1", "analysis": {"status": "pending"}}]})

    fake_anthropic["status"] = "in_progress"  # 永不 ended → 超时
    settings = {"ai": {"batch_poll_timeout_min": 0, "batch_poll_interval_s": 1}}
    out = analyze_items(_dctx(), settings)
    assert "待续传 1" in out
    pending = load_json(tmp_path / "pending.json")
    assert pending[0]["batch_id"] == "batch_test_001"
    assert pending[0]["kind"] == "items"
