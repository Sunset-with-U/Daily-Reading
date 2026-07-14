"""共享 HTTP 客户端：浏览器 UA、重试、每域名并发限制。"""
from __future__ import annotations

import random
import threading
import time
from urllib.parse import urlsplit

import httpx

BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)
DEFAULT_HEADERS = {
    "User-Agent": BROWSER_UA,
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

_RETRYABLE_STATUS = {429, 500, 502, 503, 504}

_domain_locks: dict[str, threading.Semaphore] = {}
_domain_locks_guard = threading.Lock()
_client: httpx.Client | None = None
_client_guard = threading.Lock()
_per_domain_limit = 2


def configure(per_domain_concurrency: int = 2) -> None:
    global _per_domain_limit
    _per_domain_limit = per_domain_concurrency


def _get_client() -> httpx.Client:
    global _client
    with _client_guard:
        if _client is None:
            _client = httpx.Client(
                headers=DEFAULT_HEADERS,
                follow_redirects=True,
                timeout=20,
                limits=httpx.Limits(max_connections=40, max_keepalive_connections=20),
            )
        return _client


def _domain_sem(url: str) -> threading.Semaphore:
    domain = urlsplit(url).netloc
    with _domain_locks_guard:
        if domain not in _domain_locks:
            _domain_locks[domain] = threading.Semaphore(_per_domain_limit)
        return _domain_locks[domain]


def get(url: str, *, timeout_s: int = 20, retries: int = 2,
        headers: dict | None = None) -> httpx.Response:
    """GET 请求：每域名并发限制 + 对超时/5xx/429 重试（含抖动退避）。

    最终失败会抛出 httpx.HTTPError 或 HTTPStatusError，由调用方兜住。
    """
    client = _get_client()
    merged_headers = {**DEFAULT_HEADERS, **(headers or {})}
    sem = _domain_sem(url)
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            with sem:
                resp = client.get(url, timeout=timeout_s, headers=merged_headers)
            if resp.status_code in _RETRYABLE_STATUS and attempt < retries:
                _backoff(attempt, resp.headers.get("retry-after"))
                continue
            resp.raise_for_status()
            return resp
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            last_exc = exc
            if attempt < retries:
                _backoff(attempt)
                continue
            raise
        except httpx.HTTPStatusError as exc:
            # 非可重试状态码（或重试耗尽）直接抛出
            if exc.response.status_code in _RETRYABLE_STATUS and attempt < retries:
                last_exc = exc
                _backoff(attempt)
                continue
            raise
    raise last_exc or RuntimeError("unreachable")


def _backoff(attempt: int, retry_after: str | None = None) -> None:
    if retry_after and retry_after.isdigit():
        time.sleep(min(int(retry_after), 30))
        return
    time.sleep(min((2 ** attempt) + random.random(), 10))
