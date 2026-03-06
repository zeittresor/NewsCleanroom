from __future__ import annotations

import html
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from .cache import Cache, ArticleRow


CATEGORY_LABELS = {
    "de": {"national": "[{country}]", "world": "Welt", "business": "Wirtschaft", "ai": "Künstliche Intelligenz", "entertainment": "Unterhaltung", "sports": "Sport", "it": "IT", "science": "Wissen", "politics": "Politik", "health": "Gesundheit", "custom": "Eigenes"},
    "fr": {"national": "[{country}]", "world": "Monde", "business": "Économie", "ai": "IA", "entertainment": "Divertissement", "sports": "Sport", "it": "Informatique", "science": "Science", "politics": "Politique", "health": "Santé", "custom": "Personnalisé"},
    "es": {"national": "[{country}]", "world": "Mundo", "business": "Economía", "ai": "IA", "entertainment": "Entretenimiento", "sports": "Deporte", "it": "TI", "science": "Ciencia", "politics": "Política", "health": "Salud", "custom": "Personalizado"},
    "uk": {"national": "[{country}]", "world": "Світ", "business": "Економіка", "ai": "ШІ", "entertainment": "Розваги", "sports": "Спорт", "it": "ІТ", "science": "Наука", "politics": "Політика", "health": "Здоров'я", "custom": "Власне"},
    "ru": {"national": "[{country}]", "world": "Мир", "business": "Экономика", "ai": "ИИ", "entertainment": "Развлечения", "sports": "Спорт", "it": "ИТ", "science": "Наука", "politics": "Политика", "health": "Здоровье", "custom": "Своё"},
    "zh-Hans": {"national": "[{country}]", "world": "全球", "business": "经济", "ai": "人工智能", "entertainment": "娱乐", "sports": "体育", "it": "IT", "science": "科学", "politics": "政治", "health": "健康", "custom": "自定义"},
    "en": {"national": "[{country}]", "world": "World", "business": "Business", "ai": "Artificial Intelligence", "entertainment": "Entertainment", "sports": "Sports", "it": "IT", "science": "Science", "politics": "Politics", "health": "Health", "custom": "Custom"},
}


def category_label(lang: str, category: str, country_iso2: str = "") -> str:
    label = CATEGORY_LABELS.get(lang, CATEGORY_LABELS["en"]).get(category, category)
    if "{country}" in label:
        label = label.format(country=country_iso2 or "")
    return label


def generate_offline_site(cache: Cache, *, lang: str, categories: List[str], country_iso2: str = "") -> Path:
    site = cache.site_dir
    assets_dir = site / "assets"
    articles_dir = site / "articles"
    assets_dir.mkdir(parents=True, exist_ok=True)
    articles_dir.mkdir(parents=True, exist_ok=True)
    selected_categories = list(dict.fromkeys(categories))
    rows = cache.list_articles(lang=lang, categories=selected_categories, search="", limit=3000)

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
        cat_name = html.escape(category_label(lang, row.category, country_iso2))
        return (
            "<article class='card'>"
            f"{media}"
            "<div class='card-body'>"
            f"<a class='title' href='articles/{row.id}.html'>{title}</a>"
            f"<div class='small'>{source} · {stamp}</div>"
            f"<div class='small small-tag'>{cat_name}</div>"
            "</div>"
            "</article>"
        )

    links = []
    for category in selected_categories:
        items = by_cat.get(category, [])
        label = category_label(lang, category, country_iso2)
        links.append(f"<a class='pill' href='{html.escape(category)}.html'>{html.escape(label)}</a>")
        body = (
            "<div class='topbar'><div class='wrap'>"
            f"<h1>{html.escape(label)}</h1>"
            f"<div class='meta'>{len(items)} articles</div>"
            "<div class='pills'><a class='pill' href='index.html'>Back</a></div>"
            "</div></div><div class='wrap'>"
        )
        if items:
            body += "<div class='grid'>" + "".join(card(item) for item in items[:1000]) + "</div>"
        else:
            body += "<div class='empty'>No articles available in this category yet.</div>"
        body += "</div>"
        (site / f"{category}.html").write_text(_wrap(label, body), encoding="utf-8")

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
    radial-gradient(1200px 600px at 20% 0%, rgba(122,162,255,0.16), transparent 60%),
    radial-gradient(900px 500px at 80% 10%, rgba(64,180,255,0.10), transparent 55%),
    #08101b;
  color: #eef4ff;
}
a { color: #9bc1ff; text-decoration: none; }
a:hover { text-decoration: underline; }
.topbar {
  position: sticky; top: 0;
  backdrop-filter: blur(10px);
  background: rgba(8,16,27,0.72);
  border-bottom: 1px solid rgba(255,255,255,0.07);
  padding: 14px 18px;
  z-index: 2;
}
.wrap { max-width: 1320px; margin: 0 auto; padding: 18px 22px; }
h1 { font-size: 22px; margin: 0; }
h2 { font-size: 18px; margin: 12px 0 14px; }
.meta { font-size: 12px; opacity: 0.75; margin-top: 6px; }
.pills { display: flex; flex-wrap: wrap; gap: 10px; margin: 18px 0 20px; }
.pill {
  padding: 10px 14px;
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: 999px;
  background: rgba(255,255,255,0.03);
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.03);
}
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
  align-items: start;
}
.card {
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 18px;
  background: rgba(255,255,255,0.03);
  overflow: hidden;
  box-shadow: 0 12px 34px rgba(0,0,0,0.24);
}
.thumb {
  aspect-ratio: 16 / 9;
  background: #0a1320;
  overflow: hidden;
}
.thumb img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.card-body { padding: 12px 14px 14px; }
.title {
  display: block;
  font-size: 15px;
  font-weight: 650;
  line-height: 1.35;
  margin-bottom: 8px;
  color: #eef4ff;
}
.small { font-size: 12px; opacity: 0.78; }
.small-tag { margin-top: 6px; color: #b7ccff; }
.empty {
  border: 1px dashed rgba(255,255,255,0.18);
  border-radius: 14px;
  padding: 18px;
  background: rgba(255,255,255,0.02);
}
"""
    return (
        "<!doctype html>\n"
        "<html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'>\n"
        "<title>" + html.escape(title) + "</title>\n"
        "<style>\n" + css + "\n</style>\n"
        "</head><body>\n" + body + "\n</body></html>"
    )
