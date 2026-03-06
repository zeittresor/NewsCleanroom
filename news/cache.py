from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List


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
                UNIQUE(url, category, lang)
            )
            """
        )
        self._ensure_column("thumbnail_path", "thumbnail_path TEXT")
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_articles_lookup ON articles(lang, category, published)"
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
        fetched_at = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        url_hash = hashlib.sha256(f"{url}|{category}|{lang}".encode("utf-8")).hexdigest()
        content_file = self.articles_dir / f"{url_hash}.html"
        content_file.write_text(content_html, encoding="utf-8")
        self.conn.execute(
            """
            INSERT INTO articles(url, category, lang, country_iso2, url_hash, title, source, published, summary, fetched_at, content_path, thumbnail_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(url, category, lang) DO UPDATE SET
                country_iso2=excluded.country_iso2,
                title=excluded.title,
                source=excluded.source,
                published=excluded.published,
                summary=excluded.summary,
                fetched_at=excluded.fetched_at,
                content_path=excluded.content_path,
                thumbnail_path=excluded.thumbnail_path
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
            "SELECT id, title, url, source, category, lang, country_iso2, published, fetched_at, summary, content_path, thumbnail_path "
            "FROM articles WHERE " + " AND ".join(where) + " "
            "ORDER BY COALESCE(NULLIF(published, ''), fetched_at) DESC LIMIT ?"
        )
        params.append(limit)
        rows = []
        for r in self.conn.execute(sql, params).fetchall():
            rows.append(
                ArticleRow(
                    id=r["id"],
                    title=r["title"],
                    url=r["url"],
                    source=r["source"],
                    category=r["category"],
                    lang=r["lang"],
                    country_iso2=r["country_iso2"],
                    published=r["published"] or "",
                    fetched_at=r["fetched_at"] or "",
                    summary=r["summary"] or "",
                    content_path=r["content_path"] or "",
                    thumbnail_path=r["thumbnail_path"] or "",
                )
            )
        return rows

    def get_article_html(self, article_id: int) -> str:
        row = self.conn.execute(
            "SELECT content_path, url, summary, title, thumbnail_path FROM articles WHERE id=?",
            (article_id,),
        ).fetchone()
        if not row:
            return "<html><body><p>Missing article.</p></body></html>"
        p = row["content_path"]
        if p:
            fp = Path(p)
            if fp.exists():
                return fp.read_text(encoding="utf-8")
        title = row["title"] or "Article"
        url = row["url"] or ""
        summary = row["summary"] or ""
        thumb = row["thumbnail_path"] or ""
        hero = ""
        if thumb:
            hero = f"<p><img src='{Path(thumb).as_uri()}' alt='' style='max-width:100%;border-radius:16px;'></p>"
        return (
            "<!doctype html><html><head><meta charset='utf-8'></head><body>"
            f"<h1>{title}</h1><p><a href='{url}'>{url}</a></p>{hero}<div>{summary}</div>"
            "</body></html>"
        )
