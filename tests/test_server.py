"""loopback 服务：/api 全路由 + 静态/data 路由 + token 校验（port 0 + httpx）。"""
import threading

import httpx
import pytest
import yaml

from app.server import AppState, make_server


@pytest.fixture
def app_server(tmp_path, monkeypatch, fake_keyring):
    site = tmp_path / "site"
    data = tmp_path / "data"
    user_config = tmp_path / "config"
    for p in (site, data, user_config):
        p.mkdir()
    (site / "index.html").write_text("<title>Daily Reading</title>", encoding="utf-8")
    (data / "index.json").write_text('{"dates":[]}', encoding="utf-8")

    # 出厂 settings 用仓库真实文件；overlay 与注册表 overlay 指向 tmp
    monkeypatch.setattr("pipeline.cli.USER_CONFIG_DIR", user_config)
    monkeypatch.setattr("pipeline.registry.USER_CONFIG_DIR", user_config)

    state = AppState({"site": site, "data": data, "user_config": user_config,
                      "logs": tmp_path / "logs"})
    server = make_server(state, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    yield base, state
    server.shutdown()


def test_static_and_data_routes(app_server):
    base, _ = app_server
    assert "Daily Reading" in httpx.get(f"{base}/").text
    assert httpx.get(f"{base}/data/index.json").json() == {"dates": []}
    assert httpx.get(f"{base}/missing.js").status_code == 404
    # 路径穿越被拒
    assert httpx.get(f"{base}/data/../config/settings_user.yaml").status_code in (403, 404)


def test_status_and_settings_roundtrip(app_server):
    base, state = app_server
    status = httpx.get(f"{base}/api/status").json()
    assert status["mode"] == "app"
    assert status["provider"] == "anthropic"
    assert status["keys"]["ANTHROPIC_API_KEY"] is False
    # 前端提示/密钥名依赖的能力矩阵元数据
    assert status["providers"]["anthropic"]["batch"] is True
    assert status["providers"]["gemini"]["batch"] is False
    assert status["providers"]["openai"]["env"] == "OPENAI_API_KEY"

    headers = {"X-DR-Token": state.token}
    resp = httpx.put(f"{base}/api/settings", headers=headers,
                     json={"ai": {"provider": "deepseek", "mode": "realtime"}})
    assert resp.status_code == 200
    assert resp.json()["ai"]["provider"] == "deepseek"
    # overlay 落盘且深合并（出厂键保留）
    overlay = yaml.safe_load(
        (state.paths["user_config"] / "settings_user.yaml").read_text(encoding="utf-8"))
    assert overlay == {"ai": {"provider": "deepseek", "mode": "realtime"}}
    merged = httpx.get(f"{base}/api/settings").json()
    assert merged["ai"]["provider"] == "deepseek"
    assert merged["ai"]["daily_item_cap"] == 600  # 出厂值仍在


def test_settings_whitelist_and_token(app_server):
    base, state = app_server
    headers = {"X-DR-Token": state.token}
    assert httpx.put(f"{base}/api/settings", headers=headers,
                     json={"evil": 1}).status_code == 400
    # 无 token / 错 token 一律 403
    assert httpx.put(f"{base}/api/settings", json={"ai": {}}).status_code == 403
    assert httpx.post(f"{base}/api/run", headers={"X-DR-Token": "wrong"},
                      json={}).status_code == 403


def test_keys_api_never_returns_plaintext(app_server):
    base, state = app_server
    headers = {"X-DR-Token": state.token}
    resp = httpx.put(f"{base}/api/keys", headers=headers,
                     json={"name": "DEEPSEEK_API_KEY", "value": "sk-secret-123"})
    assert resp.status_code == 200
    assert resp.json()["DEEPSEEK_API_KEY"] is True
    assert "sk-secret-123" not in resp.text
    assert httpx.get(f"{base}/api/keys").json()["DEEPSEEK_API_KEY"] is True
    assert httpx.put(f"{base}/api/keys", headers=headers,
                     json={"name": "EVIL", "value": "x"}).status_code == 400
    resp = httpx.request("DELETE", f"{base}/api/keys", headers=headers,
                         json={"name": "DEEPSEEK_API_KEY"})
    assert resp.json()["DEEPSEEK_API_KEY"] is False


def test_sources_overlay_roundtrip_and_rollback(app_server):
    base, state = app_server
    headers = {"X-DR-Token": state.token}
    srcs = httpx.get(f"{base}/api/sources").json()["sources"]
    assert len(srcs) > 100  # 出厂注册表
    some_id = srcs[0]["id"]

    resp = httpx.put(f"{base}/api/sources", headers=headers, json={
        "overrides": {some_id: {"enabled": False}},
        "extra_sources": [{"id": "my-feed", "name": "Mine", "method": "rss",
                           "url": "https://example.com/feed"}],
    })
    assert resp.status_code == 200
    got = httpx.get(f"{base}/api/sources").json()
    by_id = {s["id"]: s for s in got["sources"]}
    assert by_id[some_id]["enabled"] is False
    assert "my-feed" in by_id

    # 非法 overlay（未知 method）→ 400 且回滚到上一版
    resp = httpx.put(f"{base}/api/sources", headers=headers, json={
        "extra_sources": [{"id": "bad", "method": "carrier_pigeon", "url": "https://x/"}],
    })
    assert resp.status_code == 400
    by_id = {s["id"]: s for s in httpx.get(f"{base}/api/sources").json()["sources"]}
    assert "my-feed" in by_id and "bad" not in by_id


def test_run_endpoint_sets_event(app_server):
    base, state = app_server
    headers = {"X-DR-Token": state.token}
    resp = httpx.post(f"{base}/api/run", headers=headers, json={"edition": "morning"})
    assert resp.json() == {"status": "queued"}
    assert state.run_requested.is_set()
    assert state.run_edition == "morning"
