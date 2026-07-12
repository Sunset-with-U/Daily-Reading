"""各抓取器/解析器的 fixture 回放测试。"""
from pipeline.fetch.rss import parse_feed_bytes


def test_rss_parse(fixture_response, make_ctx, make_source):
    resp = fixture_response("rss/sample_feed.xml")
    items = parse_feed_bytes(resp.content, make_source(id="sample-rss"), make_ctx())
    assert len(items) == 2  # 空标题条目被跳过
    first = items[0]
    assert first.title == "Fed Holds Rates Steady, Signals Two Cuts This Year"
    assert first.guid == "example-fed-2026-001"
    assert "two cuts" in first.content_text
    assert "<p>" not in first.content_text  # HTML 已剥离
    assert first.published_at.startswith("2026-07-10")


def test_rss_fallback_urls(monkeypatch, make_ctx, make_source, fixture_response):
    """主 URL 404 时依次尝试 fallback_urls；主 URL 合法空 feed 不被兜底失败掩盖。"""
    import httpx

    from pipeline.fetch import http as http_mod
    from pipeline.fetch import rss

    good = fixture_response("rss/sample_feed.xml")
    empty = type(good)(b"<rss><channel><title>t</title></channel></rss>")

    def fake_get(url, **kwargs):
        if "primary" in url:
            raise httpx.HTTPStatusError("404", request=None, response=None)
        if "empty" in url:
            return empty
        return good

    monkeypatch.setattr(http_mod, "get", fake_get)

    src = make_source(url="https://primary.example.com/feed.xml",
                      fallback_urls=["https://mirror.example.com/feed.xml"])
    result = rss.fetch(src, make_ctx())
    assert result.status == "ok" and len(result.items) == 2

    # 主 URL 空 feed + 兜底失败 → empty 而非 error
    src2 = make_source(url="https://empty.example.com/feed.xml",
                       fallback_urls=["https://primary.example.com/feed.xml"])
    result2 = rss.fetch(src2, make_ctx())
    assert result2.status == "empty"


def test_telegram_parse(stub_http, make_ctx, make_source):
    stub_http({"t.me/s/FinancialJuice": "html/telegram_channel.html"})
    from pipeline.fetch.telegram import fetch

    src = make_source(id="fj-tg", method="telegram",
                      url="https://t.me/s/FinancialJuice")
    result = fetch(src, make_ctx())
    assert result.status == "ok"
    assert len(result.items) == 2  # 无文本消息被跳过
    # 倒序：最新在前
    assert "Lagarde" in result.items[0].title
    assert result.items[0].guid == "FinancialJuice/100002"
    assert result.items[1].url == "https://t.me/FinancialJuice/100001"
    assert result.items[0].published_at == "2026-07-11T13:45:22+00:00"


def test_wallstreetcn_parse(fixture_response, make_ctx, make_source):
    from pipeline.parsers.wallstreetcn import parse_information_flow

    resp = fixture_response("json_api/wallstreetcn_flow.json")
    items = parse_information_flow(resp, make_source(id="wscn", lang="zh"), make_ctx())
    assert len(items) == 2
    assert items[0].title == "美联储按兵不动，点阵图暗示年内两次降息"
    assert items[0].guid == "wscn-3720001"
    assert "降息空间" in items[0].content_text
    assert "<p>" not in items[0].content_text


def test_people_daily_parse(stub_http, make_ctx, make_source):
    stub_http({
        "node_0": "html/rmrb_node.html",       # 版面页（node_01/node_02 共用）
        "content_": "html/rmrb_article.html",  # 文章页
    })
    from pipeline.fetch.html_scrape import fetch

    src = make_source(
        id="rmrb", method="html_scrape",
        url="https://paper.people.com.cn/rmrb/pc/layout/{yyyymm}/{dd}/node_01.html",
        parser="people_daily.parse_layout", lang="zh", max_items=10,
    )
    result = fetch(src, make_ctx())
    assert result.status == "ok"
    assert len(result.items) == 2
    assert result.items[0].title == "坚定不移推动高质量发展"
    assert "高技术制造业" in result.items[0].content_text
    assert result.items[0].published_at.startswith("2026-07-12")


def test_rsshub_requires_base(make_ctx, make_source):
    from pipeline.fetch.rsshub import fetch

    src = make_source(id="gov", method="rsshub", url="/gov/zhengce/zuixin")
    result = fetch(src, make_ctx(rsshub_base=""))
    assert result.status == "skipped"


def test_fetch_isolation(make_ctx, make_source, monkeypatch):
    """单源抛异常必须被兜住为 error 状态。"""
    from pipeline import fetch as fetch_pkg

    def boom(src, ctx):
        raise RuntimeError("模拟崩溃")

    # 注意：fetch/__init__.py 在模块顶部绑定了 get_fetcher，须打它自己的命名空间
    monkeypatch.setattr("pipeline.fetch.get_fetcher", lambda m: boom)
    results = fetch_pkg.run_fetch([make_source(id="broken")], make_ctx())
    assert len(results) == 1
    assert results[0].status == "error"
    assert "模拟崩溃" in results[0].error
