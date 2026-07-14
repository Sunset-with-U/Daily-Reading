"""多供应商适配层：Claude / OpenAI / Gemini / DeepSeek。

设计约定：
- "中立请求形状" = 现有 Anthropic params dict（model/max_tokens/system/messages/
  output_config/thinking），不另造 IR；非 Anthropic 供应商做单向翻译，
  Claude 专属字段（thinking/effort）直接丢弃。
- 返回值契约与 batches.collect 一致：{"ok": text, "usage": {...}} | {"error": type}，
  上层 _apply_results 幂等合并逻辑零改动。
- OpenAI/Gemini/DeepSeek 走 httpx REST（已是依赖，不引入三个 SDK）；
  网络出口收敛到 _post/_get/_post_file 三个函数，测试单点打桩。
"""
from __future__ import annotations

import json
import os

# 能力矩阵：batch=False 的供应商在"省钱模式"下自动降级实时
PROVIDERS = {
    "anthropic": {"batch": True, "env": "ANTHROPIC_API_KEY"},
    "openai": {"batch": True, "env": "OPENAI_API_KEY"},
    # Gemini 有 Batch API 但本项目暂未接（选省钱模式时降级实时并提示）
    "gemini": {"batch": False, "env": "GEMINI_API_KEY"},
    "deepseek": {"batch": False, "env": "DEEPSEEK_API_KEY"},
}

# 各家默认模型（面板/settings.ai.models 可覆盖；实现时以各家现行 GA 型号为准）
DEFAULT_MODELS = {
    "anthropic": {"item": "claude-haiku-4-5", "report": "claude-opus-4-8"},
    "openai": {"item": "gpt-5-mini", "report": "gpt-5.1"},
    "gemini": {"item": "gemini-2.5-flash", "report": "gemini-2.5-pro"},
    "deepseek": {"item": "deepseek-chat", "report": "deepseek-reasoner"},
}

_OPENAI_BASE = "https://api.openai.com/v1"
_GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"
_DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"


def provider_of(settings: dict) -> str:
    return settings.get("ai", {}).get("provider", "anthropic")


def supports_batch(provider: str) -> bool:
    return bool(PROVIDERS.get(provider, {}).get("batch"))


def available(settings: dict) -> bool:
    """当前所选供应商的 API Key 是否就位（gating 用）。"""
    return key_available(provider_of(settings))


def key_available(provider: str) -> bool:
    info = PROVIDERS.get(provider)
    return bool(info and os.environ.get(info["env"]))


def env_var(provider: str) -> str:
    """供应商对应的 API Key 环境变量名（提示语用，调用方不必知道矩阵内部形状）。"""
    return PROVIDERS.get(provider, {}).get("env", "API Key")


def model_for(settings: dict, kind: str, provider: str | None = None) -> str:
    """kind: "item"|"report"。models 表缺失时回退旧键（item_model/report_model），
    保证既有 settings fixture 与云端出厂配置不变。

    provider 显式传入时优先（断点续传补录按 pending entry 的 provider 解析
    模型归属，与当前面板选择无关）；未知 provider 回退 anthropic 并告警。
    """
    ai = settings.get("ai", {})
    provider = provider or provider_of(settings)
    if provider not in PROVIDERS:
        print(f"  [providers] 未知的 ai.provider={provider!r}，按 anthropic 处理")
        provider = "anthropic"
    table = (ai.get("models") or {}).get(provider) or {}
    if table.get(kind):
        return table[kind]
    legacy = ai.get("item_model" if kind == "item" else "report_model")
    if provider == "anthropic" and legacy:
        return legacy
    return DEFAULT_MODELS[provider][kind]


def _key(provider: str) -> str:
    return os.environ.get(PROVIDERS[provider]["env"], "")


# ── 网络出口（测试打桩缝） ──────────────────────────────────

_http = None  # 共享连接池：实时模式数百请求复用 TCP/TLS（并发首调竞态无害）


def _http_client():
    global _http
    if _http is None:
        import httpx

        _http = httpx.Client()
    return _http


def _post(url: str, headers: dict, body: dict, timeout_s: int = 600) -> dict:
    resp = _http_client().post(url, headers=headers, json=body, timeout=timeout_s)
    resp.raise_for_status()
    return resp.json()


def _get(url: str, headers: dict, timeout_s: int = 60):
    # 轮询/下载走仓库共享 GET：自带 429/5xx 重试与 Retry-After 退避
    from ..fetch import http

    return http.get(url, headers=headers, timeout_s=timeout_s)


def _post_file(url: str, headers: dict, filename: str, content: bytes,
               data: dict, timeout_s: int = 120) -> dict:
    resp = _http_client().post(url, headers=headers, data=data,
                               files={"file": (filename, content, "application/jsonl")},
                               timeout=timeout_s)
    resp.raise_for_status()
    return resp.json()


# ── 请求翻译（Anthropic 形状 → 各家 REST body） ─────────────


def _schema_of(params: dict) -> dict | None:
    return ((params.get("output_config") or {}).get("format") or {}).get("schema")


def _user_text(params: dict) -> str:
    return "\n\n".join(m["content"] for m in params.get("messages", [])
                       if m.get("role") == "user")


def openai_body(params: dict) -> dict:
    """OpenAI chat completions（DeepSeek 兼容同形状，见 deepseek_body）。"""
    body = {
        "model": params["model"],
        "max_completion_tokens": params.get("max_tokens", 4096),
        "messages": ([{"role": "system", "content": params["system"]}]
                     if params.get("system") else []) + list(params.get("messages", [])),
    }
    schema = _schema_of(params)
    if schema:
        body["response_format"] = {"type": "json_schema", "json_schema": {
            "name": "result", "strict": True, "schema": schema}}
    return body  # thinking/effort 为 Claude 专属，不翻译


def gemini_body(params: dict) -> dict:
    body = {
        "contents": [{"role": "user", "parts": [{"text": _user_text(params)}]}],
        "generationConfig": {"maxOutputTokens": params.get("max_tokens", 4096)},
    }
    if params.get("system"):
        body["systemInstruction"] = {"parts": [{"text": params["system"]}]}
    schema = _schema_of(params)
    if schema:
        body["generationConfig"]["responseMimeType"] = "application/json"
        body["generationConfig"]["responseSchema"] = _gemini_schema(schema)
    return body


def _gemini_schema(schema):
    """Gemini responseSchema（OpenAPI 子集）翻译：

    - 剥除不支持的 additionalProperties/$schema
    - anyOf: [{type: null}, X] → X + nullable: true（Gemini 无 "null" 类型；
      ITEM_SCHEMA.deep 正是这个形状）
    """
    if isinstance(schema, dict):
        branches = schema.get("anyOf")
        if branches:
            non_null = [b for b in branches if b.get("type") != "null"]
            if len(non_null) == 1 and len(non_null) < len(branches):
                out = _gemini_schema(non_null[0])
                out["nullable"] = True
                return out
        return {k: _gemini_schema(v) for k, v in schema.items()
                if k not in ("additionalProperties", "$schema")}
    if isinstance(schema, list):
        return [_gemini_schema(v) for v in schema]
    return schema


def deepseek_body(params: dict) -> dict:
    """DeepSeek：OpenAI 兼容但无 json_schema 严格模式——降级 json_object +
    在 system 末尾追加 schema 文本约束，最终由 clamp/parse 兜底校验。

    deepseek-reasoner 不支持 response_format（只能靠提示词约束）；
    max_tokens 上限 8192，超出请求会被拒，就地收紧。
    """
    system = params.get("system", "")
    schema = _schema_of(params)
    if schema:
        system += ("\n\n# 输出格式（必须严格遵守）\n只输出一个 JSON 对象，"
                   "符合以下 JSON Schema，不要输出任何其他文字：\n"
                   + json.dumps(schema, ensure_ascii=False))
    body = {
        "model": params["model"],
        "max_tokens": min(int(params.get("max_tokens", 4096)), 8192),
        "messages": ([{"role": "system", "content": system}] if system else [])
        + list(params.get("messages", [])),
    }
    if schema and "reasoner" not in params["model"]:
        body["response_format"] = {"type": "json_object"}
    return body


# ── 实时调用（单请求，永不抛异常） ──────────────────────────


def call_realtime(provider: str, params: dict) -> dict:
    """返回 {"ok": text, "usage": {...}} | {"error": type}，与 batches.collect 同契约。"""
    try:
        return _REALTIME[provider](params)
    except Exception as exc:  # noqa: BLE001 — 单请求隔离，失败进错误契约
        return {"error": f"{type(exc).__name__}"}


_anthropic_clients: dict[str, object] = {}


def _anthropic_client():
    # 按 Key 缓存：连接池跨请求复用；面板换 Key 后自动用新客户端
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    client = _anthropic_clients.get(key)
    if client is None:
        import anthropic

        client = _anthropic_clients[key] = anthropic.Anthropic()
    return client


def _anthropic_realtime(params: dict) -> dict:
    from . import batches

    client = _anthropic_client()
    # 大输出（报告 30K tokens）必须流式，否则 SDK 拒绝非流式长请求
    if int(params.get("max_tokens", 0)) > 8192:
        with client.messages.stream(**params) as stream:
            msg = stream.get_final_message()
    else:
        msg = client.messages.create(**params)
    return batches.message_to_result(msg)


def _openai_realtime(params: dict) -> dict:
    data = _post(f"{_OPENAI_BASE}/chat/completions",
                 {"Authorization": f"Bearer {_key('openai')}"}, openai_body(params))
    return _openai_result(data)


def _openai_result(data: dict) -> dict:
    choice = (data.get("choices") or [{}])[0]
    text = (choice.get("message") or {}).get("content") or ""
    usage = data.get("usage") or {}
    if not text:
        return {"error": choice.get("finish_reason") or "empty_response"}
    return {"ok": text, "usage": {"input_tokens": usage.get("prompt_tokens", 0),
                                  "output_tokens": usage.get("completion_tokens", 0)}}


def _gemini_realtime(params: dict) -> dict:
    url = f"{_GEMINI_BASE}/models/{params['model']}:generateContent"
    data = _post(url, {"x-goog-api-key": _key("gemini")}, gemini_body(params))
    cand = (data.get("candidates") or [{}])[0]
    parts = (cand.get("content") or {}).get("parts") or []
    text = "".join(p.get("text", "") for p in parts)
    if not text:
        return {"error": cand.get("finishReason") or "empty_response"}
    meta = data.get("usageMetadata") or {}
    return {"ok": text, "usage": {"input_tokens": meta.get("promptTokenCount", 0),
                                  "output_tokens": meta.get("candidatesTokenCount", 0)}}


def _deepseek_realtime(params: dict) -> dict:
    data = _post(_DEEPSEEK_URL, {"Authorization": f"Bearer {_key('deepseek')}"},
                 deepseek_body(params))
    return _openai_result(data)


_REALTIME = {
    "anthropic": _anthropic_realtime,
    "openai": _openai_realtime,
    "gemini": _gemini_realtime,
    "deepseek": _deepseek_realtime,
}


# ── OpenAI Batch（JSONL 上传 → batch → 轮询 → 下载结果） ────


def openai_batch_submit(requests: list[dict]) -> str:
    """requests: [{"custom_id", "params"}]（Anthropic 中立形状）；返回 batch_id。"""
    headers = {"Authorization": f"Bearer {_key('openai')}"}
    lines = [json.dumps({
        "custom_id": r["custom_id"], "method": "POST",
        "url": "/v1/chat/completions", "body": openai_body(r["params"]),
    }, ensure_ascii=False) for r in requests]
    up = _post_file(f"{_OPENAI_BASE}/files", headers, "batch.jsonl",
                    "\n".join(lines).encode("utf-8"), {"purpose": "batch"})
    batch = _post(f"{_OPENAI_BASE}/batches", headers, {
        "input_file_id": up["id"], "endpoint": "/v1/chat/completions",
        "completion_window": "24h",
    })
    return batch["id"]


def openai_batch_status(batch_id: str) -> dict:
    """返回原始 batch 对象；status ∈ validating/in_progress/completed/failed/expired/…"""
    return _get(f"{_OPENAI_BASE}/batches/{batch_id}",
                {"Authorization": f"Bearer {_key('openai')}"}).json()


def openai_batch_collect(batch_id: str) -> dict[str, dict]:
    """回收已完成 batch → {custom_id: 结果契约}。"""
    headers = {"Authorization": f"Bearer {_key('openai')}"}
    batch = openai_batch_status(batch_id)
    out: dict[str, dict] = {}
    for file_key, is_error in (("output_file_id", False), ("error_file_id", True)):
        file_id = batch.get(file_key)
        if not file_id:
            continue
        content = _get(f"{_OPENAI_BASE}/files/{file_id}/content", headers).text
        for line in content.splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            cid = rec.get("custom_id", "")
            if is_error or rec.get("error"):
                out[cid] = {"error": (rec.get("error") or {}).get("code", "errored")}
            else:
                out[cid] = _openai_result((rec.get("response") or {}).get("body") or {})
    return out
