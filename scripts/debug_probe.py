#!/usr/bin/env python3
"""CI 侧探针：抓取 config/debug_probe.yaml 里列出的 URL 并打印结构诊断。

沙盒开发环境无法直连外部站点，解析器选择器只能靠这个探针在 CI 日志里
回看真实页面结构来修。仅在 debug_probe.yaml 存在时由 daily.yml 调用；
问题修完后删掉该配置文件即可（探针脚本保留备用）。
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

CONF = ROOT / "config" / "debug_probe.yaml"


def main() -> int:
    if not CONF.exists():
        print("[debug-probe] 无 config/debug_probe.yaml，跳过")
        return 0
    probes = yaml.safe_load(CONF.read_text(encoding="utf-8")) or []
    from pipeline.fetch import http

    for p in probes:
        name, url = p["name"], p["url"]
        mode = p.get("mode", "html")
        print(f"\n{'=' * 70}\n[probe] {name}  {url}")
        try:
            resp = http.get(url, timeout_s=25, headers=p.get("headers") or None)
        except Exception as exc:  # noqa: BLE001
            print(f"  !! 抓取失败: {type(exc).__name__}: {str(exc)[:200]}")
            continue
        ctype = resp.headers.get("content-type", "?")
        print(f"  status={resp.status_code} final_url={resp.url} "
              f"type={ctype} bytes={len(resp.content)}")
        if mode == "json":
            print("  前 800 字符:")
            print("  " + resp.text[:800].replace("\n", " ")[:800])
            continue
        if mode == "raw":
            print("  前 800 字符:")
            print("  " + repr(resp.text[:800]))
            continue
        _dump_html(resp)
    return 0


def _dump_html(resp) -> None:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(resp.text, "lxml")
    title = soup.title.get_text(strip=True) if soup.title else "(无 title)"
    links = soup.find_all("a", href=True)
    print(f"  <title>: {title[:80]}   <a> 共 {len(links)} 个")
    # 打印文本最长的 25 个链接：真实列表项一般标题最长
    ranked = sorted(links, key=lambda a: -len(a.get_text(strip=True)))[:25]
    for a in ranked:
        text = a.get_text(strip=True)[:60]
        classes = " ".join((a.get("class") or [])[:3])
        parent = a.parent.name if a.parent else "?"
        pclass = " ".join((a.parent.get("class") or [])[:3]) if a.parent else ""
        print(f"    [{parent}.{pclass or '-'}] a.{classes or '-'} "
              f"href={a['href'][:70]}  | {text}")


if __name__ == "__main__":
    sys.exit(main())
