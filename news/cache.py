from __future__ import annotations

import hashlib
import html as html_lib
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List
from urllib.parse import parse_qsl, unquote, urlencode, urlsplit, urlunsplit


TRACKING_QUERY_PARAMS = {
    "fbclid", "gclid", "dclid", "mc_cid", "mc_eid", "igshid", "ocid", "cmpid",
    "camp", "campaign", "ref", "ref_src", "ref_url", "output", "spm", "xtor",
    "wt_mc", "guccounter", "ga_source", "ga_medium", "ga_term", "ga_campaign",
}


def canonicalize_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    try:
        parts = urlsplit(url)
    except Exception:
        return url
    scheme = (parts.scheme or "https").lower()
    netloc = (parts.netloc or "").lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    path = unquote(parts.path or "/")
    path = re.sub(r"/{2,}", "/", path)
    if path != "/" and path.endswith("/"):
        path = path[:-1]
    kept = []
    for k, v in parse_qsl(parts.query, keep_blank_values=True):
        lk = k.lower()
        if lk.startswith("utm_") or lk in TRACKING_QUERY_PARAMS:
            continue
        kept.append((k, v))
    query = urlencode(sorted(kept), doseq=True)
    return urlunsplit((scheme, netloc, path, query, ""))


def normalize_title(title: str) -> str:
    text = html_lib.unescape((title or "").strip().lower())
    text = text.replace("–", "-").replace("—", "-").replace("|", " ")
    # keep unicode letters/numbers, normalize punctuation/spacing
    text = re.sub(r"[^\w\s-]+", " ", text, flags=re.UNICODE)
    text = re.sub(r"\s+", " ", text).strip(" -_")
    return text


def _category_colors(category: str):
    colors = {
        "national": ("#3456ff", "#1d2c65"),
        "world": ("#0ea5e9", "#0b3e65"),
        "business": ("#16a34a", "#0f5132"),
        "ai": ("#8b5cf6", "#41256d"),
        "entertainment": ("#f97316", "#6d2f13"),
        "sports": ("#ef4444", "#6b1f1f"),
        "it": ("#06b6d4", "#0a4555"),
        "science": ("#22c55e", "#144b2a"),
        "politics": ("#eab308", "#625214"),
        "health": ("#ec4899", "#6d1f4c"),
        "custom": ("#94a3b8", "#334155"),
    }
    return colors.get(category, ("#6b8cff", "#263556"))


def _title_initials(title: str) -> str:
    words = [w for w in re.split(r"\s+", (title or "").strip()) if w]
    if not words:
        return "N"
    initials = "".join(w[0].upper() for w in words[:3])
    return initials[:3] or "N"


def _title_line(title: str, max_len: int = 54) -> str:
    clean = html_lib.escape(" ".join((title or "").split()))
    if len(clean) > max_len:
        clean = clean[: max_len - 1] + "…"
    return clean


def make_placeholder_thumb(thumbs_dir: Path, category: str, title: str) -> str:
    thumbs_dir.mkdir(parents=True, exist_ok=True)
    seed = hashlib.sha256(f"{category}|{title}".encode("utf-8")).hexdigest()
    c1, c2 = _category_colors(category)
    name = re.sub(r"[^a-z0-9_-]+", "_", (category or "news").lower())
    target = thumbs_dir / f"placeholder_{name}_{seed[:12]}.svg"
    if not target.exists():
        initials = html_lib.escape(_title_initials(title))
        label = html_lib.escape((category or "news").upper())
        line = _title_line(title or "NewsCleanroom")
        x1 = 180 + int(seed[0:2], 16)
        y1 = 540 - int(seed[2:4], 16)
        x2 = 980 - int(seed[4:6], 16)
        y2 = 120 + int(seed[6:8], 16)
        svg = f"""<svg xmlns='http://www.w3.org/2000/svg' width='1200' height='630' viewBox='0 0 1200 630'>
<defs>
  <linearGradient id='g' x1='0' y1='0' x2='1' y2='1'>
    <stop offset='0%' stop-color='{c1}'/>
    <stop offset='100%' stop-color='{c2}'/>
  </linearGradient>
  <filter id='blur'><feGaussianBlur stdDeviation='18'/></filter>
</defs>
<rect width='1200' height='630' rx='34' fill='#0d1117'/>
<rect x='28' y='28' width='1144' height='574' rx='28' fill='url(#g)' opacity='0.88'/>
<circle cx='{x1}' cy='{y1}' r='220' fill='rgba(255,255,255,0.08)' filter='url(#blur)'/>
<circle cx='{x2}' cy='{y2}' r='180' fill='rgba(255,255,255,0.06)' filter='url(#blur)'/>
<rect x='66' y='62' width='160' height='44' rx='22' fill='rgba(10,14,20,0.28)' stroke='rgba(255,255,255,0.18)'/>
<text x='88' y='92' font-family='Segoe UI, Arial, sans-serif' font-size='24' fill='white' opacity='0.9'>{label}</text>
<text x='68' y='272' font-family='Segoe UI, Arial, sans-serif' font-size='118' font-weight='700' fill='white'>{initials}</text>
<text x='70' y='356' font-family='Segoe UI, Arial, sans-serif' font-size='42' fill='white' opacity='0.92'>{line}</text>
<text x='72' y='414' font-family='Segoe UI, Arial, sans-serif' font-size='28' fill='white' opacity='0.76'>NewsCleanroom preview</text>
</svg>"""
        target.write_text(svg, encoding="utf-8")
    return str(target)


def resolve_thumbnail_path(thumbs_dir: Path, category: str, title: str, thumbnail_path: str) -> str:
    if thumbnail_path:
        fp = Path(thumbnail_path)
        name = fp.name.lower()
        if fp.exists() and not (name.startswith("placeholder_") and re.fullmatch(r"placeholder_[a-z0-9_-]+\.svg", name)):
            return str(fp)
    return make_placeholder_thumb(thumbs_dir, category, title)


@dataclass
class ArticleRow:
    id: int
    title: str
    url: str
    source: str
    category: str
    lang: str
    country_iso2: str
    published: str
    fetched_at: str
    summary: str
    content_path: str
    thumbnail_path: str


class Cache:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.articles_dir = self.base_dir / "articles"
        self.articles_dir.mkdir(parents=True, exist_ok=True)
        self.site_dir = self.base_dir / "site"
        self.site_dir.mkdir(parents=True, exist_ok=True)
        self.thumbs_dir = self.base_dir / "thumbs"
        self.thumbs_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.base_dir / "news_cache.sqlite"
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute("PRAGMA synchronous=NORMAL;")
        self.conn.execute("PRAGMA busy_timeout=5000;")
        self._init_db()

    def close(self) -> None:
        try:
            self.conn.close()
        except Exception:
            pass

    def _ensure_column(self, name: str, ddl: str) -> None:
        cols = {row[1] for row in self.conn.execute("PRAGMA table_info(articles)").fetchall()}
        if name not in cols:
            self.conn.execute(f"ALTER TABLE articles ADD COLUMN {ddl}")
            self.conn.commit()

    def _init_db(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL,
                category TEXT NOT NULL,
                lang TEXT NOT NULL,
                country_iso2 TEXT NOT NULL,
                url_hash TEXT NOT NULL,
                title TEXT NOT NULL,
                source TEXT NOT NULL,
                published TEXT,
                summary TEXT,
                fetched_at TEXT NOT NULL,
                content_path TEXT,
                thumbnail_path TEXT,
                canonical_url TEXT,
                title_key TEXT,
                UNIQUE(url, category, lang)
            )
            """
        )
        self._ensure_column("thumbnail_path", "thumbnail_path TEXT")
        self._ensure_column("canonical_url", "canonical_url TEXT")
        self._ensure_column("title_key", "title_key TEXT")
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_articles_lookup ON articles(lang, category, published)"
        )
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_articles_canonical ON articles(lang, canonical_url)"
        )
        self.conn.commit()

    def upsert_article(
        self,
        *,
        url: str,
        category: str,
        lang: str,
        country_iso2: str,
        title: str,
        source: str,
        published: str,
        summary: str,
        content_html: str,
        thumbnail_path: str = "",
    ) -> int:
        canonical_url = canonicalize_url(url)
        title_key = normalize_title(title)
        fetched_at = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        url_hash = hashlib.sha256(f"{canonical_url}|{category}|{lang}".encode("utf-8")).hexdigest()
        content_file = self.articles_dir / f"{url_hash}.html"
        content_file.write_text(content_html, encoding="utf-8")
        self.conn.execute(
            """
            INSERT INTO articles(url, category, lang, country_iso2, url_hash, title, source, published, summary, fetched_at, content_path, thumbnail_path, canonical_url, title_key)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(url, category, lang) DO UPDATE SET
                country_iso2=excluded.country_iso2,
                title=excluded.title,
                source=excluded.source,
                published=excluded.published,
                summary=excluded.summary,
                fetched_at=excluded.fetched_at,
                content_path=excluded.content_path,
                thumbnail_path=excluded.thumbnail_path,
                canonical_url=excluded.canonical_url,
                title_key=excluded.title_key
            """,
            (
                url,
                category,
                lang,
                country_iso2,
                url_hash,
                title,
                source,
                published,
                summary,
                fetched_at,
                str(content_file),
                thumbnail_path or "",
                canonical_url,
                title_key,
            ),
        )
        self.conn.commit()
        cur = self.conn.execute(
            "SELECT id FROM articles WHERE url=? AND category=? AND lang=?",
            (url, category, lang),
        )
        row = cur.fetchone()
        return int(row["id"])

    def list_articles(self, *, lang: str, categories: List[str], search: str = "", limit: int = 600) -> List[ArticleRow]:
        where = ["lang = ?"]
        params = [lang]
        if categories:
            where.append("category IN (%s)" % ",".join("?" for _ in categories))
            params.extend(categories)
        if search.strip():
            like = f"%{search.strip()}%"
            where.append("(title LIKE ? OR source LIKE ? OR summary LIKE ?)")
            params.extend([like, like, like])

        sql = (
            "SELECT id, title, url, source, category, lang, country_iso2, published, fetched_at, summary, content_path, thumbnail_path, canonical_url, title_key "
            "FROM articles WHERE " + " AND ".join(where) + " "
            "ORDER BY COALESCE(NULLIF(published, ''), fetched_at) DESC LIMIT ?"
        )
        # fetch a bit more so post-query dedupe still returns enough rows
        params.append(max(limit * 4, limit))
        seen_canonical = set()
        seen_source_title = set()
        rows: List[ArticleRow] = []
        for r in self.conn.execute(sql, params).fetchall():
            canonical = (r["canonical_url"] or canonicalize_url(r["url"] or "")).strip()
            title_key = (r["title_key"] or normalize_title(r["title"] or "")).strip()
            source_key = (r["source"] or "").strip().lower()

            if canonical and canonical in seen_canonical:
                continue
            if source_key and title_key and (source_key, title_key) in seen_source_title:
                continue

            seen_canonical.add(canonical)
            seen_source_title.add((source_key, title_key))

            thumb = resolve_thumbnail_path(self.thumbs_dir, r["category"] or "", r["title"] or "", r["thumbnail_path"] or "")
            rows.append(
                ArticleRow(
                    id=r["id"],
                    title=r["title"],
                    url=canonical or r["url"],
                    source=r["source"],
                    category=r["category"],
                    lang=r["lang"],
                    country_iso2=r["country_iso2"],
                    published=r["published"] or "",
                    fetched_at=r["fetched_at"] or "",
                    summary=r["summary"] or "",
                    content_path=r["content_path"] or "",
                    thumbnail_path=thumb,
                )
            )
            if len(rows) >= limit:
                break
        return rows

    def get_article_html(self, article_id: int) -> str:
        row = self.conn.execute(
            "SELECT content_path, url, summary, title, thumbnail_path, category FROM articles WHERE id=?",
            (article_id,),
        ).fetchone()
        if not row:
            return "<html><body><p>Missing article.</p></body></html>"
        p = row["content_path"]
        thumb = resolve_thumbnail_path(self.thumbs_dir, row["category"] or "", row["title"] or "", row["thumbnail_path"] or "")
        if p:
            fp = Path(p)
            if fp.exists():
                content = fp.read_text(encoding="utf-8")
                if thumb:
                    content = content.replace((row["thumbnail_path"] or ""), thumb)
                    try:
                        content = content.replace(Path(row["thumbnail_path"] or "").as_uri(), Path(thumb).as_uri())
                    except Exception:
                        pass
                try:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(content, "lxml")
                    imgs = soup.find_all("img")
                    if len(imgs) >= 2:
                        src0 = (imgs[0].get("src") or "").strip()
                        src1 = (imgs[1].get("src") or "").strip()
                        if src0 and src0 == src1:
                            parent = imgs[1].parent
                            try:
                                parent.decompose()
                            except Exception:
                                imgs[1].decompose()
                            content = str(soup)
                except Exception:
                    pass
                return content
        title = row["title"] or "Article"
        url = canonicalize_url(row["url"] or "")
        summary = row["summary"] or ""
        hero = ""
        if thumb:
            hero = f"<p><img src='{Path(thumb).as_uri()}' alt='' style='max-width:100%;border-radius:16px;'></p>"
        return (
            "<!doctype html><html><head><meta charset='utf-8'></head><body>"
            f"<h1>{title}</h1><p><a href='{url}'>{url}</a></p>{hero}<div>{summary}</div>"
            "</body></html>"
        )
