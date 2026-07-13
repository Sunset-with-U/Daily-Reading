"""密钥管理：存取/回填/只回布尔（内存桩 backend，不碰真 Keychain）。"""
import pytest

from app import keys


class _FakeKeyring:
    def __init__(self):
        self.store = {}

    def set_password(self, service, name, value):
        self.store[(service, name)] = value

    def get_password(self, service, name):
        return self.store.get((service, name))

    def delete_password(self, service, name):
        del self.store[(service, name)]


@pytest.fixture
def fake_keyring(monkeypatch):
    fake = _FakeKeyring()
    monkeypatch.setattr(keys, "_keyring", lambda: fake)
    for name in keys.MANAGED_KEYS:
        monkeypatch.delenv(name, raising=False)
    return fake


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
