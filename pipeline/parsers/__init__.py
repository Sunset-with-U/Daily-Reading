"""站点专用解析器：每个模块对应一个需要定制解析的站点。

统一签名：
    def parse_xxx(resp: httpx.Response, src: SourceConfig, ctx: FetchContext) -> list[RawItem]
"""
