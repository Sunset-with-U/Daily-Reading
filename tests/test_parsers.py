"""专用解析器：gov.cn JSON 拾荒、通用列表页。"""
from pipeline.parsers.jsonutil import find_records, record_fields


def test_json_scavenger_on_gov_cn(fixture_response, make_ctx, make_source, monkeypatch):
    from pipeline.parsers.gov_cn import parse_policies

    resp = fixture_response("json_api/gov_cn_policies.json")
    items = parse_policies(resp, make_source(id="gov", lang="zh"), make_ctx())
    assert len(items) == 2
    assert items[0].title == "国务院关于促进民营经济发展的若干意见"
    assert items[0].url.endswith("content_10012.htm")
    assert items[0].published_at.startswith("2026-07-10")
    assert "民营经济" in items[0].content_text


def test_json_scavenger_tolerates_unknown_shapes():
    # 换个包裹结构和字段名也能找到记录
    data = {"result": {"data": {"rows": [
        {"docTitle": "文件A", "pubUrl": "https://x.gov.cn/a.htm", "printDate": "2026-07-01"},
        {"docTitle": "文件B", "pubUrl": "https://x.gov.cn/b.htm"},
    ]}}}
    records = find_records(data)
    assert len(records) == 2
    f = record_fields(records[0])
    assert f["title"] == "文件A" and f["url"].endswith("a.htm") and f["date"]


def test_generic_list_parser(stub_http, fixture_response, make_ctx, make_source):
    from pipeline.parsers.cn_ministries import parse_list

    # 列表页 fixture；正文抓取指到文章 fixture
    stub_http({"t2026": "html/rmrb_article.html"})
    resp = fixture_response("html/generic_list.html", url="https://www.csrc.gov.cn/news/")
    items = parse_list(resp, make_source(id="csrc", lang="zh", max_items=10), make_ctx())
    assert len(items) == 2  # 导航链接/短标题/无中文的被过滤
    assert items[0].title == "关于进一步规范程序化交易的通知"
    assert items[0].url == "https://www.csrc.gov.cn/zhengce/202607/t20260711_100001.html"
    assert "高技术制造业" in items[0].content_text  # 正文已抓取


def test_generic_list_body_failure_tolerated(stub_http, fixture_response, make_ctx, make_source):
    """正文抓取失败不影响条目产出（fetch_article_text 永不抛）。"""
    from pipeline.parsers.cn_ministries import parse_list

    stub_http({})  # 任何正文请求都会 AssertionError → 被 fetch_article_text 兜住
    resp = fixture_response("html/generic_list.html", url="https://www.csrc.gov.cn/news/")
    items = parse_list(resp, make_source(id="csrc", lang="zh"), make_ctx())
    assert len(items) == 2
    assert items[0].content_text == ""
