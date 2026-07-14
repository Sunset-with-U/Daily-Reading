"""多供应商适配层：翻译契约 + 模型解析 + 出厂请求形状锁定。"""
import json

from pipeline.analyze import providers
from pipeline.analyze.schemas import ITEM_SCHEMA

_PARAMS = {
    "model": "test-model",
    "max_tokens": 1500,
    "system": "系统提示",
    "messages": [{"role": "user", "content": "条目内容"}],
    "output_config": {"format": {"type": "json_schema", "schema": ITEM_SCHEMA}},
    "thinking": {"type": "adaptive"},  # Claude 专属，翻译层必须丢弃
}

FACTORY = {"ai": {
    "provider": "anthropic", "mode": "batch",
    "models": {
        "anthropic": {"item": "claude-haiku-4-5", "report": "claude-opus-4-8"},
        "deepseek": {"item": "deepseek-chat", "report": "deepseek-reasoner"},
    },
    "item_model": "claude-haiku-4-5", "report_model": "claude-opus-4-8",
}}


def test_default_models_match_factory_settings():
    # DEFAULT_MODELS（代码兜底）与出厂 settings.yaml 的 models 表刻意两层——
    # yaml 驱动面板显示、代码表保 fail-open。此断言防止两份清单漂移。
    import yaml as _yaml

    from pipeline.util import CONFIG_DIR

    factory = _yaml.safe_load((CONFIG_DIR / "settings.yaml").read_text(encoding="utf-8"))
    assert factory["ai"]["models"] == providers.DEFAULT_MODELS


def test_model_for_factory_legacy_and_defaults():
    assert providers.model_for(FACTORY, "item") == "claude-haiku-4-5"
    assert providers.model_for(FACTORY, "report") == "claude-opus-4-8"
    # 旧 settings（无 models 表）回退旧键——既有云端配置与测试 fixture 不变
    legacy = {"ai": {"item_model": "claude-haiku-4-5", "report_model": "claude-opus-4-8"}}
    assert providers.model_for(legacy, "item") == "claude-haiku-4-5"
    assert providers.model_for(legacy, "report") == "claude-opus-4-8"
    # 其他供应商无 models 表时用内置默认
    assert providers.model_for({"ai": {"provider": "gemini"}}, "item") \
        == providers.DEFAULT_MODELS["gemini"]["item"]


def test_openai_body_translation():
    body = providers.openai_body(_PARAMS)
    assert body["model"] == "test-model"
    assert body["max_completion_tokens"] == 1500
    assert body["messages"][0] == {"role": "system", "content": "系统提示"}
    assert body["messages"][1]["role"] == "user"
    rf = body["response_format"]
    assert rf["type"] == "json_schema"
    assert rf["json_schema"]["strict"] is True
    assert rf["json_schema"]["schema"] == ITEM_SCHEMA
    assert "thinking" not in json.dumps(body)  # Claude 专属字段已剥离


def test_model_for_unknown_provider_and_explicit_provider(capsys):
    # 未知 provider 回退 anthropic（collect-pending 不能因面板手滑崩溃）
    bad = {"ai": {"provider": "azure"}}
    assert providers.model_for(bad, "item") == "claude-haiku-4-5"
    assert "未知的 ai.provider" in capsys.readouterr().out
    # 显式 provider（断点续传按 entry.provider 解析归属）优先于 settings
    assert providers.model_for(FACTORY, "item", provider="deepseek") == "deepseek-chat"


def test_gemini_schema_translates_null_anyof():
    # ITEM_SCHEMA.deep 的 anyOf:[{type:null}, obj] → obj + nullable（Gemini 无 null 类型）
    body = providers.gemini_body(_PARAMS)
    deep = body["generationConfig"]["responseSchema"]["properties"]["deep"]
    assert "anyOf" not in deep
    assert deep.get("nullable") is True
    assert deep.get("type") == "object"


def test_deepseek_reasoner_alignment():
    params = {**_PARAMS, "model": "deepseek-reasoner", "max_tokens": 30000}
    body = providers.deepseek_body(params)
    assert "response_format" not in body  # reasoner 不支持 json_object
    assert body["max_tokens"] == 8192     # 上限收紧
    assert "JSON Schema" in body["messages"][0]["content"]  # 提示词约束仍在


def test_gemini_body_translation():
    body = providers.gemini_body(_PARAMS)
    assert body["systemInstruction"]["parts"][0]["text"] == "系统提示"
    assert body["contents"][0]["parts"][0]["text"] == "条目内容"
    gc = body["generationConfig"]
    assert gc["maxOutputTokens"] == 1500
    assert gc["responseMimeType"] == "application/json"
    # responseSchema 任意深度都不得残留 additionalProperties
    assert "additionalProperties" not in json.dumps(gc["responseSchema"])
    assert "thinking" not in json.dumps(body)


def test_deepseek_body_translation():
    body = providers.deepseek_body(_PARAMS)
    assert body["response_format"] == {"type": "json_object"}
    system = body["messages"][0]["content"]
    assert system.startswith("系统提示")
    assert "JSON Schema" in system and "summary_zh" in system  # schema 注入提示词
    assert body["max_tokens"] == 1500


def test_call_realtime_openai_ok_and_error(monkeypatch):
    responses = [
        {"choices": [{"message": {"content": '{"a":1}'}}],
         "usage": {"prompt_tokens": 10, "completion_tokens": 5}},
        {"choices": [{"message": {"content": ""}, "finish_reason": "length"}]},
    ]
    monkeypatch.setattr(providers, "_post", lambda *a, **k: responses.pop(0))
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    ok = providers.call_realtime("openai", _PARAMS)
    assert ok == {"ok": '{"a":1}', "usage": {"input_tokens": 10, "output_tokens": 5}}
    err = providers.call_realtime("openai", _PARAMS)
    assert err == {"error": "length"}


def test_call_realtime_never_raises(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("network down")

    monkeypatch.setattr(providers, "_post", boom)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    assert providers.call_realtime("deepseek", _PARAMS) == {"error": "RuntimeError"}


def test_openai_batch_flow(monkeypatch):
    calls = {}

    def fake_post_file(url, headers, filename, content, data, **kw):
        calls["jsonl"] = content.decode("utf-8")
        return {"id": "file-1"}

    def fake_post(url, headers, body, **kw):
        calls["batch_body"] = body
        return {"id": "batch-1", "status": "validating"}

    class FakeResp:
        def __init__(self, payload, text=""):
            self._payload, self.text = payload, text

        def json(self):
            return self._payload

    def fake_get(url, headers, **kw):
        if url.endswith("/batches/batch-1"):
            return FakeResp({"id": "batch-1", "status": "completed",
                             "output_file_id": "file-out"})
        return FakeResp(None, text=json.dumps({
            "custom_id": "aaa",
            "response": {"body": {"choices": [{"message": {"content": '{"x":1}'}}],
                                  "usage": {"prompt_tokens": 3, "completion_tokens": 2}}},
        }))

    monkeypatch.setattr(providers, "_post_file", fake_post_file)
    monkeypatch.setattr(providers, "_post", fake_post)
    monkeypatch.setattr(providers, "_get", fake_get)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    batch_id = providers.openai_batch_submit([{"custom_id": "aaa", "params": _PARAMS}])
    assert batch_id == "batch-1"
    line = json.loads(calls["jsonl"])
    assert line["custom_id"] == "aaa" and line["url"] == "/v1/chat/completions"
    assert calls["batch_body"]["input_file_id"] == "file-1"

    results = providers.openai_batch_collect("batch-1")
    assert results["aaa"]["ok"] == '{"x":1}'


def test_factory_item_request_contract(tmp_path, monkeypatch):
    """出厂配置下 item 请求形状锁定——云端回归保障的核心断言。"""
    from pipeline import persist
    from pipeline.analyze import item_analysis, runner

    captured = {}

    def fake_execute(requests, settings, dctx, kind, on_results=None):
        captured["requests"], captured["kind"] = requests, kind
        return {}

    monkeypatch.setattr(runner, "execute", fake_execute)
    monkeypatch.setattr(persist, "DATA_DIR", tmp_path)
    persist.save_items_doc("2026-07-12", {"date": "2026-07-12", "runs": [], "items": [
        {"id": "aaa", "title": "T", "analysis": {"status": "pending"}}]})

    from types import SimpleNamespace
    dctx = SimpleNamespace(date_bj="2026-07-12", edition="morning",
                           run_at_utc="2026-07-12T00:00:00Z")
    item_analysis.analyze_items(dctx, FACTORY)

    params = captured["requests"][0]["params"]
    assert set(params) == {"model", "max_tokens", "system", "messages", "output_config"}
    assert params["model"] == "claude-haiku-4-5"
    assert params["max_tokens"] == 1500
    assert params["output_config"] == {
        "format": {"type": "json_schema", "schema": ITEM_SCHEMA}}
    assert captured["kind"] == "items"
