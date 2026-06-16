#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Energy Board Japan (energy-board.xvps.jp) の審議会データを RSS 2.0 に変換する。

経産省(METI)の審議会・研究会の新着会議＝1 アイテムとして配信する。
依存ライブラリなし（Python 3 標準ライブラリのみ）。GitHub Actions 等でそのまま動く。

使い方:
  # 全審議会の新着 50 件
  python3 build_feed.py --out docs/energy-board.xml

  # キーワード絞り込み（API の全文検索を利用）
  python3 build_feed.py --search 蓄電池 --out docs/storage.xml

  # 特定の審議会だけ（部分一致・複数可）
  python3 build_feed.py --council 次世代電力系統 容量市場 --out docs/grid.xml

設定ファイル (feeds.json) を使えば複数フィードを一括生成できる:
  python3 build_feed.py --config feeds.json
"""

import argparse
import json
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from xml.sax.saxutils import escape
from email.utils import format_datetime
from pathlib import Path

API = "https://energy-board.xvps.jp/api/meetings"
SITE = "https://energy-board.xvps.jp/"
JST = timezone(timedelta(hours=9))
UA = "energy-board-rss/1.0 (+https://energy-board.xvps.jp/)"


def fetch(search=None, limit=80, sort="desc"):
    """API を叩いて会議リストを返す。search はサーバー側全文検索。"""
    params = {"page": 1, "limit": limit, "sort": sort}
    if search:
        params["search"] = search
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def to_rfc822(date_str):
    """'2026-06-12' -> RFC822。時刻不明なので JST 正午扱い。"""
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").replace(
            hour=12, tzinfo=JST
        )
    except (ValueError, TypeError):
        d = datetime.now(JST)
    return format_datetime(d)


def build_description(m):
    """資料リンク一覧＋タグを HTML で組み立てる。"""
    parts = []
    tags = m.get("tags") or []
    if tags:
        parts.append("タグ: " + "、".join(escape(t) for t in tags) + "<br>")
    docs = m.get("documents") or []
    if docs:
        parts.append("資料:<br><ul>")
        for d in docs:
            title = escape(d.get("title") or "資料")
            url = escape(d.get("url") or "")
            if url:
                parts.append(f'<li><a href="{url}">{title}</a></li>')
            else:
                parts.append(f"<li>{title}</li>")
        parts.append("</ul>")
    return "".join(parts)


def matches_council(m, council_filters):
    if not council_filters:
        return True
    name = m.get("councilName", "")
    return any(f in name for f in council_filters)


def build_rss(meetings, title, link, description, self_url=None):
    now = format_datetime(datetime.now(JST))
    out = []
    out.append('<?xml version="1.0" encoding="UTF-8"?>')
    out.append(
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">'
    )
    out.append("<channel>")
    out.append(f"<title>{escape(title)}</title>")
    out.append(f"<link>{escape(link)}</link>")
    out.append(f"<description>{escape(description)}</description>")
    out.append("<language>ja</language>")
    out.append(f"<lastBuildDate>{now}</lastBuildDate>")
    out.append("<generator>energy-board-rss</generator>")
    if self_url:
        out.append(
            f'<atom:link href="{escape(self_url)}" rel="self" '
            'type="application/rss+xml"/>'
        )
    for m in meetings:
        mtitle = m.get("meetingTitle") or m.get("councilName") or "会議"
        council = m.get("councilName") or ""
        date = m.get("meetingDate") or ""
        guid = m.get("meetingUrl") or m.get("councilUrl") or SITE
        item_title = f"[{date}] {council}｜{mtitle}".strip()
        out.append("<item>")
        out.append(f"<title>{escape(item_title)}</title>")
        out.append(f"<link>{escape(guid)}</link>")
        out.append(f'<guid isPermaLink="false">{escape(guid)}</guid>')
        out.append(f"<pubDate>{to_rfc822(date)}</pubDate>")
        for t in (m.get("tags") or []):
            out.append(f"<category>{escape(t)}</category>")
        out.append(f"<description>{escape(build_description(m))}</description>")
        out.append("</item>")
    out.append("</channel>")
    out.append("</rss>")
    return "\n".join(out)


def generate_one(out_path, search=None, council=None, limit=80,
                 title=None, base_url=None):
    raw = fetch(search=search, limit=limit)
    meetings = raw.get("data", [])
    council_filters = council or []
    meetings = [m for m in meetings if matches_council(m, council_filters)]

    if not title:
        bits = []
        if search:
            bits.append(f"「{search}」")
        if council_filters:
            bits.append("／".join(council_filters))
        suffix = " ".join(bits)
        title = ("METI審議会 新着" + (f"：{suffix}" if suffix else "")).strip()
    desc = "経済産業省（METI）エネルギー審議会の新着会議・資料（Energy Board Japan より生成）"

    self_url = None
    if base_url:
        self_url = base_url.rstrip("/") + "/" + Path(out_path).name

    xml = build_rss(meetings, title, SITE, desc, self_url=self_url)
    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(xml, encoding="utf-8")
    print(f"[ok] {out_path}  ({len(meetings)} items)  title='{title}'")
    return len(meetings)


def main():
    ap = argparse.ArgumentParser(description="Energy Board -> RSS generator")
    ap.add_argument("--config", help="複数フィード定義 JSON")
    ap.add_argument("--out", default="docs/energy-board.xml")
    ap.add_argument("--search", default=None, help="API 全文検索キーワード")
    ap.add_argument("--council", nargs="*", default=None,
                    help="審議会名の部分一致フィルタ（複数可）")
    ap.add_argument("--limit", type=int, default=80)
    ap.add_argument("--title", default=None)
    ap.add_argument("--base-url", default=None,
                    help="公開URLの基点（atom:self 用）例 https://USER.github.io/REPO")
    args = ap.parse_args()

    if args.config:
        cfg = json.load(open(args.config, encoding="utf-8"))
        base = cfg.get("base_url")
        outdir = cfg.get("out_dir", "docs")
        total = 0
        for f in cfg["feeds"]:
            total += generate_one(
                out_path=str(Path(outdir) / f["file"]),
                search=f.get("search"),
                council=f.get("council"),
                limit=f.get("limit", 80),
                title=f.get("title"),
                base_url=base,
            )
        print(f"[done] {len(cfg['feeds'])} feeds, {total} items total")
    else:
        generate_one(
            out_path=args.out,
            search=args.search,
            council=args.council,
            limit=args.limit,
            title=args.title,
            base_url=args.base_url,
        )


if __name__ == "__main__":
    sys.exit(main())
