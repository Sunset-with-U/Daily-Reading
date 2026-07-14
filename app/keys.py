"""API Key 管理：macOS Keychain（keyring）存取 + 回填 os.environ。

回填后 pipeline 的 8 处 os.environ 读取点无需任何改动；
测试与命令行开发不经过本模块（直接读环境变量）。
"""
from __future__ import annotations

import os

SERVICE = "Daily-Reading"
# 四家 AI + 付费信息源凭证，同一套机制管理
MANAGED_KEYS = (
    "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY", "DEEPSEEK_API_KEY",
    "TWITTERAPI_IO_KEY", "FRED_API_KEY",
)


def _keyring():
    import keyring

    return keyring


def _check(name: str) -> None:
    if name not in MANAGED_KEYS:
        raise ValueError(f"未知的密钥名：{name}")


def set_key(name: str, value: str) -> None:
    _check(name)
    _keyring().set_password(SERVICE, name, value)
    os.environ[name] = value  # 立即生效，无需重启


def delete_key(name: str) -> None:
    _check(name)
    try:
        _keyring().delete_password(SERVICE, name)
    except Exception:  # noqa: BLE001 — 不存在即视为已删除
        pass
    os.environ.pop(name, None)


def backfill_env() -> None:
    """启动时把 Keychain 里的密钥回填进程环境（已有 env 的不覆盖）。"""
    for name in MANAGED_KEYS:
        if os.environ.get(name):
            continue
        try:
            value = _keyring().get_password(SERVICE, name)
        except Exception:  # noqa: BLE001 — 无可用 backend（如 CI）时静默
            return
        if value:
            os.environ[name] = value


def key_status() -> dict[str, bool]:
    """只回布尔（永不回明文）；回填后 env 即事实来源。"""
    return {name: bool(os.environ.get(name)) for name in MANAGED_KEYS}
