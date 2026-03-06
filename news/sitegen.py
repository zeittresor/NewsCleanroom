from __future__ import annotations

import html
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from .cache import Cache, ArticleRow


def generate_offline_site(cache: Cache, *, lang: str, categories: List[str]) -> Path:
    site = cache.site_dir
    assets_dir = site / "assets"
    articles_dir = site / "articles"
    assets_dir.mkdir(parents=True, exist_ok=True)
    articles_dir.mkdir(parents=True, exist_ok=True)
    rows = cache.list_articles(lang=lang, categories=categories, search="", limit=3000)

    asset_map: Dict[str, str] = {}

    def asset_for(path_str: str) -> str:
        if not path_str:
            return ""
        src = Path(path_str)
        if not src.exists():
            return ""
        if path_str in asset_map:
            return asset_map[path_str]
        safe_name = f"{len(asset_map)+1}_{src.name}"
        dest = assets_dir / safe_name
        shutil.copy2(src, dest)
        rel = f"assets/{safe_name}"
        asset_map[path_str] = rel
        return rel

    for row in rows:
        content = cache.get_article_html(row.id)
        thumb_rel = asset_for(row.thumbnail_path)
        if thumb_rel:
            content = content.replace(row.thumbnail_path, f"../{thumb_rel}")
            content = content.replace(Path(row.thumbnail_path).as_uri(), f"../{thumb_rel}")
        (articles_dir / f"{row.id}.html").write_text(content, encoding="utf-8")

    by_cat: Dict[str, List[ArticleRow]] = {}
    for row in rows:
        by_cat.setdefault(row.category, []).append(row)

    def card(row: ArticleRow) -> str:
        title = html.escape(row.title)
        source = html.escape(row.source)
        stamp = html.escape((row.published or row.fetched_at)[:19].replace("T", " "))
        thumb_rel = asset_for(row.thumbnail_path)
        media = ""
        if thumb_rel:
            media = f"<div class='thumb'><img src='{thumb_rel}' alt=''></div>"
        return (
            "<article class='card'>"
            f"{media}"
            "<div class='card-body'>"
            f"<a class='title' href='articles/{row.id}.html'>{title}</a>"
            f"<div class='small'>{source} · {stamp}</div>"
            "</div>"
            "</article>"
        )

    links = []
    for category, items in sorted(by_cat.items(), key=lambda x: x[0]):
        links.append(f"<a class='pill' href='{html.escape(category)}.html'>{html.escape(category)}</a>")
        body = (
            "<div class='topbar'><div class='wrap'>"
            f"<h1>{html.escape(category)}</h1>"
            f"<div class='meta'>{len(items)} articles</div>"
            "<div class='pills'><a class='pill' href='index.html'>Back</a></div>"
            "</div></div><div class='wrap'>"
        )
        if items:
            body += "<div class='grid'>" + "".join(card(item) for item in items[:1000]) + "</div>"
        else:
            body += "<div class='empty'>No articles available.</div>"
        body += "</div>"
        (site / f"{category}.html").write_text(_wrap(category, body), encoding="utf-8")

    generated = datetime.now().isoformat(timespec="seconds")
    body = (
        "<div class='topbar'><div class='wrap'>"
        "<h1>NewsCleanroom Offline</h1>"
        f"<div class='meta'>Generated: {html.escape(generated)} · Cached articles: {len(rows)}</div>"
        "</div></div><div class='wrap'>"
        "<div class='pills'>" + " ".join(links) + "</div>"
    )
    if rows:
        body += "<h2>Latest</h2><div class='grid'>" + "".join(card(item) for item in rows[:60]) + "</div>"
    else:
        body += "<div class='empty'>No cached articles yet. Run an update first.</div>"
    body += "</div>"
    (site / "index.html").write_text(_wrap("NewsCleanroom Offline", body), encoding="utf-8")
    return site / "index.html"


def _wrap(title: str, body: str) -> str:
    css = """
:root { color-scheme: dark; }
body {
  font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
  margin: 0;
  background:
    radial-gradient(1100px 520px at 15% 0%, rgba(90,120,255,.18), transparent 60%),
    radial-gradient(800px 440px at 85% 10%, rgba(86,214,164,.10), transparent 55%),
    #0c1017;
  color: #e7ebf3;
}
a { color: #8bb4ff; text-decoration: none; }
a:hover { text-decoration: underline; }
img { display:block; max-width:100%; }
.topbar {
  position: sticky;
  top: 0;
  backdrop-filter: blur(12px);
  background: rgba(12,16,23,.72);
  border-bottom: 1px solid rgba(255,255,255,.07);
}
.wrap { max-width: 1180px; margin: 0 auto; padding: 18px 22px; }
h1 { margin: 0; font-size: 28px; }
h2 { margin: 28px 0 14px 0; font-size: 20px; }
.meta { margin-top: 8px; opacity: .78; font-size: 12px; }
.pills { display: flex; flex-wrap: wrap; gap: 10px; margin: 18px 0 10px 0; }
.pill {
  padding: 9px 13px;
  border-radius: 999px;
  border: 1px solid rgba(255,255,255,.11);
  background: rgba(255,255,255,.04);
}
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px; }
.card {
  border: 1px solid rgba(255,255,255,.08);
  border-radius: 18px;
  overflow: hidden;
  background: rgba(255,255,255,.03);
  box-shadow: 0 14px 40px rgba(0,0,0,.26);
}
.thumb { aspect-ratio: 16 / 9; background: #131a25; }
.thumb img { width: 100%; height: 100%; object-fit: cover; }
.card-body { padding: 14px; }
.card .title {
  display: block;
  font-weight: 600;
  line-height: 1.35;
  margin-bottom: 10px;
}
.card .small { font-size: 12px; opacity: .76; }
.empty {
  border: 1px dashed rgba(255,255,255,.18);
  border-radius: 16px;
  padding: 20px;
  background: rgba(255,255,255,.02);
}
"""
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        f"<title>{html.escape(title)}</title>"
        f"<style>{css}</style>"
        "</head><body>"
        f"{body}"
        "</body></html>"
    )
