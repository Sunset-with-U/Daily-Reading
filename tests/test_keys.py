"""密钥管理：存取/回填/只回布尔（fake_keyring 桩见 conftest）。"""
import pytest

from app import keys


def test_managed_keys_cover_provider_envs():
    # keys.MANAGED_KEYS 与 providers.PROVIDERS 因 import 顺序约束刻意双写——
    # 此断言防止新增供应商时漏改一边
    from pipeline.analyze.providers import PROVIDERS

    assert {info["env"] for info in PROVIDERS.values()} <= set(keys.MANAGED_KEYS)


def test_set_key_writes_keychain_and_env(fake_keyring, monkeypatch):
    keys.set_key("DEEPSEEK_API_KEY", "sk-abc")
    assert fake_keyring.store[(keys.SERVICE, "DEEPSEEK_API_KEY")] == "sk-abc"
    import os

    assert os.environ["DEEPSEEK_API_KEY"] == "sk-abc"
    assert keys.key_status()["DEEPSEEK_API_KEY"] is True
    # key_status 只含布尔，绝无明文
    assert "sk-abc" not in str(keys.key_status())


def test_unknown_key_rejected(fake_keyring):
    with pytest.raises(ValueError):
        keys.set_key("EVIL_KEY", "x")
    with pytest.raises(ValueError):
        keys.delete_key("PATH")


def test_backfill_env_respects_existing(fake_keyring, monkeypatch):
    fake_keyring.store[(keys.SERVICE, "OPENAI_API_KEY")] = "sk-from-keychain"
    fake_keyring.store[(keys.SERVICE, "FRED_API_KEY")] = "fred-keychain"
    monkeypatch.setenv("FRED_API_KEY", "fred-env")  # 已有 env 不覆盖
    keys.backfill_env()
    import os

    assert os.environ["OPENAI_API_KEY"] == "sk-from-keychain"
    assert os.environ["FRED_API_KEY"] == "fred-env"


def test_delete_key(fake_keyring, monkeypatch):
    keys.set_key("GEMINI_API_KEY", "g-1")
    keys.delete_key("GEMINI_API_KEY")
    assert keys.key_status()["GEMINI_API_KEY"] is False
    keys.delete_key("GEMINI_API_KEY")  # 重复删除不报错
