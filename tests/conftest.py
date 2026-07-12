"""测试公共设施：FakeResponse + http.get 打桩。"""
from __future__ import annotations

import json as _json
import sys
from pathlib import Path

import pytest

# 保证 `import pipeline` 可用（从仓库根运行 pytest 时通常已可用，这里兜底）
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

FIXTURES = Path(__file__).parent / "fixtures"


class FakeResponse:
    def __init__(self, body: bytes | str, url: str = "https://example.com/",
                 status_code: int = 200):
        self._body = body.encode("utf-8") if isinstance(body, str) else body
        self.url = url
        self.status_code = status_code

    @property
    def content(self) -> bytes:
        return self._body

    @property
    def text(self) -> str:
        return self._body.decode("utf-8", errors="replace")

    def json(self):
        return _json.loads(self.text)


@pytest.fixture
def fixture_response():
    def _load(rel_path: str, url: str = "https://example.com/") -> FakeResponse:
        return FakeResponse((FIXTURES / rel_path).read_bytes(), url=url)

    return _load


@pytest.fixture
def stub_http(monkeypatch):
    """把 pipeline.fetch.http.get 替换为按 URL 匹配 fixture 的桩。

    用法: stub_http({"paper.people.com.cn": "html/rmrb_node.html", ...})
    键为 URL 子串，值为 fixture 相对路径。
    """
    def _install(url_map: dict[str, str]):
        from pipeline.fetch import http as http_mod

        def fake_get(url, **kwargs):
            for pattern, fixture_rel in url_map.items():
                if pattern in url:
                    return FakeResponse((FIXTURES / fixture_rel).read_bytes(), url=url)
            raise AssertionError(f"测试桩未覆盖的 URL: {url}")

        monkeypatch.setattr(http_mod, "get", fake_get)
        return fake_get

    return _install


@pytest.fixture
def make_ctx():
    from pipeline.models import FetchContext

    def _make(**overrides):
        defaults = dict(
            settings={"fetch": {"content_truncate_chars": 4000, "excerpt_chars": 500}},
            rsshub_base="http://localhost:1200",
            date_bj="2026-07-12",
            edition="morning",
        )
        defaults.update(overrides)
        return FetchContext(**defaults)

    return _make


@pytest.fixture
def make_source():
    from pipeline.models import SourceConfig

    def _make(**overrides):
        defaults = dict(id="test-src", name="Test", method="rss",
                        url="https://example.com/feed.xml", lang="en")
        defaults.update(overrides)
        return SourceConfig(**defaults)

    return _make
