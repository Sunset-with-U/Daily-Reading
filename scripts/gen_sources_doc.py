#!/usr/bin/env python3
"""从 config/sources.yaml 生成 docs/sources.md（源清单文档，保持与配置同步）。

用法：python3 scripts/gen_sources_doc.py
"""
from __future__ import annotations

import sys
from collections import Counter, OrderedDict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent

CATEGORY_ZH = OrderedDict([
    ("squawk", "实时快讯 / X 精选"),
    ("global_media", "全球财经媒体"),
    ("cn_media", "中文财经媒体"),
    ("cn_official", "中文官方与政策"),
    ("central_bank", "央行与监管"),
    ("academic", "学术研究"),
    ("thinktank", "智库与中国研究"),
    ("newsletter", "Newsletter 专栏"),
    ("crypto", "加密与链上"),
    ("podcast", "播客"),
])

METHOD_ZH = {
    "rss": "RSS/Atom",
    "json_api": "公开 JSON API",
    "html_scrape": "HTML 爬虫",
    "rsshub": "自建 RSSHub",
    "telegram": "Telegram 公开频道",
    "google_news": "Google News 兜底",
    "twitter": "X（twitterapi.io，需密钥）",
    "podcast_itunes": "播客（iTunes 解析）",
}

TIER_ZH = {"A": "A·核心", "B": "B·标准", "C": "C·尽力而为"}
SCHEDULE_ZH = {"both": "早晚", "morning": "早报", "evening": "晚报", "weekly": "每周"}


def main() -> int:
    doc = yaml.safe_load((ROOT / "config" / "sources.yaml").read_text(encoding="utf-8"))
    srcs = doc.get("sources", [])
    enabled = [s for s in srcs if s.get("enabled", True)]
    n_handles = sum(len(s.get("handles", [])) for s in srcs)
    method_count = Counter(s.get("method", "rss") for s in srcs)

    lines = [
        "# 信息源清单",
        "",
        "> 本文档由 `scripts/gen_sources_doc.py` 从 `config/sources.yaml` 自动生成，请勿手改。",
        "",
        f"共 **{len(srcs)}** 个源（启用 {len(enabled)} 个），其中 X 主题组覆盖 **{n_handles}** 个精选账号。",
        "",
        "## 接入方式分布",
        "",
        "| 方式 | 数量 | 说明 |",
        "|---|---:|---|",
    ]
    for m, cnt in method_count.most_common():
        lines.append(f"| {METHOD_ZH.get(m, m)} | {cnt} | `{m}` |")
    lines += ["", "## 分类明细", ""]

    by_cat: dict[str, list[dict]] = {}
    for s in srcs:
        by_cat.setdefault(s.get("category", "other"), []).append(s)

    cats = list(CATEGORY_ZH) + sorted(set(by_cat) - set(CATEGORY_ZH))
    for cat in cats:
        group = by_cat.get(cat)
        if not group:
            continue
        lines += [f"### {CATEGORY_ZH.get(cat, cat)}（{len(group)}）", "",
                  "| 源 | 等级 | 班次 | 方式 | 状态 | 备注 |",
                  "|---|---|---|---|---|---|"]
        for s in sorted(group, key=lambda x: (x.get("tier", "B"), x["id"])):
            name = s.get("name_zh") or s.get("name") or s["id"]
            state = "✅" if s.get("enabled", True) else "⛔ 停用"
            note = str(s.get("notes", "")).replace("|", "\\|")
            if s.get("method") == "twitter":
                note = (f"{len(s.get('handles', []))} 账号；" + note).rstrip("；")
            lines.append(
                f"| {name}（`{s['id']}`） | {TIER_ZH.get(str(s.get('tier', 'B')), s.get('tier'))} "
                f"| {SCHEDULE_ZH.get(s.get('schedule', 'both'), s.get('schedule'))} "
                f"| {METHOD_ZH.get(s.get('method', 'rss'), s.get('method'))} "
                f"| {state} | {note} |")
        lines.append("")

    lines += [
        "## 维护约定",
        "",
        "- 新增/调整源只改 `config/sources.yaml`，然后重跑本脚本更新文档。",
        "- `tier`：A=必读核心，B=标准监控，C=尽力而为（失败不告警）。",
        "- 每周一的 `source-health` 工作流探活全部源（含停用源），连败 3 次以上的源会在",
        "  「源健康周报」Issue 中被点名，建议停用或更换接入方式。",
        "- X 主题组仅在配置了 `TWITTERAPI_IO_KEY` Secret 时启用，未配置时自动跳过。",
    ]
    out = ROOT / "docs" / "sources.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"已生成 {out}（{len(srcs)} 源）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
