"""路径 env 重定向：DAILY_READING_* 生效与默认回退（子进程隔离验证 import 时求值）。"""
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

_PROBE = (
    "import json, pipeline.util as u, pipeline.dedupe as d, pipeline.analyze.batches as b;"
    "print(json.dumps({'data': str(u.DATA_DIR), 'config': str(u.CONFIG_DIR),"
    " 'user_config': str(u.USER_CONFIG_DIR), 'seen': str(d._STATE_FILE),"
    " 'pending': str(b._PENDING_FILE)}))"
)


def _probe(extra_env: dict) -> dict:
    env = {**os.environ, **extra_env}
    out = subprocess.run([sys.executable, "-c", _PROBE], cwd=REPO, env=env,
                         capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def test_default_paths_anchor_repo():
    env = {k: "" for k in ("DAILY_READING_DATA_DIR", "DAILY_READING_CONFIG_DIR",
                           "DAILY_READING_USER_CONFIG_DIR")}
    got = _probe(env)
    assert got["data"] == str(REPO / "data")
    assert got["config"] == str(REPO / "config")
    assert got["user_config"] == str(REPO / "config")  # 未设时与出厂目录相同


def test_init_env_honors_preset_env(tmp_path, monkeypatch):
    """env 预设时 init_env 的路径字典必须与之一致（服务端读 = 管线写）。"""
    monkeypatch.setenv("DAILY_READING_DATA_DIR", str(tmp_path / "d"))
    monkeypatch.setenv("DAILY_READING_USER_CONFIG_DIR", str(tmp_path / "u"))
    from app import paths as app_paths

    p = app_paths.init_env()
    assert p["data"] == tmp_path / "d"
    assert p["user_config"] == tmp_path / "u"


def test_env_redirects_all_dependents(tmp_path):
    got = _probe({
        "DAILY_READING_DATA_DIR": str(tmp_path / "d"),
        "DAILY_READING_CONFIG_DIR": str(tmp_path / "c"),
        "DAILY_READING_USER_CONFIG_DIR": str(tmp_path / "u"),
    })
    assert got["data"] == str(tmp_path / "d")
    assert got["config"] == str(tmp_path / "c")
    assert got["user_config"] == str(tmp_path / "u")
    # 模块级常量（import 时求值）必须跟随重定向——App 依赖此性质
    assert got["seen"] == str(tmp_path / "d" / "state" / "seen_items.json")
    assert got["pending"] == str(tmp_path / "d" / "state" / "pending_batches.json")
