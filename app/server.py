"""本地 loopback HTTP 服务：看板静态资源 + /data/* + /api/* 读写通道。

- 只绑 127.0.0.1；写接口（PUT/POST/DELETE）校验 X-DR-Token，防本机其他进程盲打
- /data/* 路由到用户数据目录 → 前端 api.js 的相对路径取数零改动
- 独立可跑：python -m app.server（浏览器开发设置视图，无需打包）
"""
from __future__ import annotations

import json
import mimetypes
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import yaml

# 面板可写的 settings 顶层段（全部是成本/行为旋钮，无敏感信息）
SETTINGS_SECTIONS = ("ai", "fetch", "report", "persist", "dedupe")


class AppState:
    """服务上下文：路径、token、调度器挂钩（Phase 5 注入）。"""

    def __init__(self, paths: dict[str, Path]):
        self.paths = paths
        self.token = secrets.token_urlsafe(24)
        self.run_requested = threading.Event()   # scheduler 消费
        self.run_edition: str | None = None
        self.scheduler_status = lambda: {}       # Phase 5 注入
        self.version = "2.1.0"


def make_server(state: AppState, port: int = 0) -> ThreadingHTTPServer:
    handler = _make_handler(state)
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    server.daemon_threads = True
    return server


def _make_handler(state: AppState):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):  # 静默访问日志
            pass

        # ── 响应helpers ────────────────────────────────
        def _json(self, obj, status: int = 200):
            body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _error(self, status: int, msg: str):
            self._json({"error": msg}, status)

        def _body(self) -> dict:
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b"{}"
            try:
                return json.loads(raw.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                return {}

        def _authorized(self) -> bool:
            return self.headers.get("X-DR-Token", "") == state.token

        # ── 路由 ───────────────────────────────────────
        def do_GET(self):
            path = self.path.split("?", 1)[0]
            if path == "/api/status":
                return self._api_status()
            if path == "/api/settings":
                return self._json(_load_settings())
            if path == "/api/keys":
                from . import keys

                return self._json(keys.key_status())
            if path == "/api/sources":
                return self._api_sources_get()
            if path.startswith("/api/"):
                return self._error(404, "未知接口")
            return self._static(path)

        def do_PUT(self):
            if not self._authorized():
                return self._error(403, "token 无效")
            path = self.path.split("?", 1)[0]
            if path == "/api/settings":
                return self._api_settings_put()
            if path == "/api/keys":
                return self._api_keys_put()
            if path == "/api/sources":
                return self._api_sources_put()
            return self._error(404, "未知接口")

        def do_POST(self):
            if not self._authorized():
                return self._error(403, "token 无效")
            path = self.path.split("?", 1)[0]
            if path == "/api/run":
                body = self._body()
                state.run_edition = body.get("edition") or None
                state.run_requested.set()
                return self._json({"status": "queued"})
            return self._error(404, "未知接口")

        def do_DELETE(self):
            if not self._authorized():
                return self._error(403, "token 无效")
            if self.path.split("?", 1)[0] == "/api/keys":
                from . import keys

                name = self._body().get("name", "")
                try:
                    keys.delete_key(name)
                except ValueError as exc:
                    return self._error(400, str(exc))
                return self._json(keys.key_status())
            return self._error(404, "未知接口")

        # ── API 实现 ───────────────────────────────────
        def _api_status(self):
            from pipeline.analyze.providers import PROVIDERS

            from . import keys

            settings = _load_settings()
            ai = settings.get("ai", {})
            self._json({
                "mode": "app",
                "version": state.version,
                "provider": ai.get("provider", "anthropic"),
                "ai_mode": ai.get("mode", "batch"),
                # 能力矩阵唯一事实源在 providers——前端提示/密钥名从这里取
                "providers": {name: {"batch": info["batch"], "env": info["env"]}
                              for name, info in PROVIDERS.items()},
                "keys": keys.key_status(),
                "scheduler": state.scheduler_status(),
            })

        def _api_settings_put(self):
            overlay_file = state.paths["user_config"] / "settings_user.yaml"
            patch = self._body()
            unknown = [k for k in patch if k not in SETTINGS_SECTIONS]
            if unknown:
                return self._error(400, f"不可写的设置段：{unknown}")
            from pipeline.util import deep_merge, load_user_yaml

            current = load_user_yaml(overlay_file) or {}
            merged = deep_merge(current, patch)
            overlay_file.write_text(
                yaml.safe_dump(merged, allow_unicode=True, sort_keys=False),
                encoding="utf-8")
            return self._json(_load_settings())

        def _api_keys_put(self):
            from . import keys

            body = self._body()
            name, value = body.get("name", ""), body.get("value", "")
            if not value:
                return self._error(400, "value 不能为空")
            try:
                keys.set_key(name, value)
            except ValueError as exc:
                return self._error(400, str(exc))
            return self._json(keys.key_status())  # 只回布尔

        def _api_sources_get(self):
            from pipeline.registry import load_sources

            srcs = [{
                "id": s.id, "name_zh": s.name_zh or s.name, "category": s.category,
                "tier": s.tier, "method": s.method, "enabled": s.enabled,
                "schedule": s.schedule, "notes": s.notes,
            } for s in load_sources()]
            from pipeline.util import load_user_yaml

            overlay_file = state.paths["user_config"] / "sources_user.yaml"
            overlay = load_user_yaml(overlay_file) or {}
            return self._json({"sources": srcs, "overlay": overlay})

        def _api_sources_put(self):
            body = self._body()
            doc = {"overrides": body.get("overrides") or {},
                   "extra_sources": body.get("extra_sources") or []}
            # 保存前严格校验（运行期对坏覆盖是优雅降级，但保存入口必须直接报错）
            from pipeline.registry import validate_overlay

            errors = validate_overlay(doc["overrides"], doc["extra_sources"])
            if errors:
                return self._error(400, "源配置无效：" + "；".join(errors))
            overlay_file = state.paths["user_config"] / "sources_user.yaml"
            overlay_file.write_text(
                yaml.safe_dump(doc, allow_unicode=True, sort_keys=False), encoding="utf-8")
            return self._json({"status": "saved"})

        # ── 静态文件（site/ 与 /data/*） ────────────────
        def _static(self, path: str):
            if path in ("", "/"):
                path = "/index.html"
            if path.startswith("/data/"):
                root, rel = state.paths["data"], path[len("/data/"):]
            else:
                root, rel = state.paths["site"], path.lstrip("/")
            target = (root / rel).resolve()
            try:
                target.relative_to(root.resolve())  # 防路径穿越
            except ValueError:
                return self._error(403, "forbidden")
            if not target.is_file():
                return self._error(404, "not found")
            ctype = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
            body = target.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(body)

    return Handler


def _load_settings() -> dict:
    from pipeline.cli import load_settings

    return load_settings()


def main() -> None:
    """独立开发模式：起服务 + 前台运行；POST /api/run 由后台线程执行管线。"""
    from . import keys, paths

    app_paths = paths.init_env()
    keys.backfill_env()
    state = AppState(app_paths)
    server = make_server(state, port=0)
    port = server.server_address[1]
    print(f"Daily-Reading 本地服务：http://127.0.0.1:{port}/?t={state.token}")

    def _run_worker():
        while True:
            state.run_requested.wait()
            state.run_requested.clear()
            from pipeline.cli import main as cli_main

            args = ["run", "--mode", "test"]
            if state.run_edition:
                args += ["--edition", state.run_edition]
            try:
                cli_main(args)
            except Exception:  # noqa: BLE001
                import traceback

                traceback.print_exc()

    threading.Thread(target=_run_worker, daemon=True).start()
    server.serve_forever()


if __name__ == "__main__":
    main()
