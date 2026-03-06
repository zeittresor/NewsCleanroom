from __future__ import annotations

import html as html_lib
import mimetypes
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import feedparser
import requests

from .cache import Cache
from .config import PAYWALL_DOMAIN_DENYLIST, feeds_for
from .extractor import extract_article, wrap_summary

USER_AGENT = "NewsCleanroom/2.1 (+desktop rss reader)"


@dataclass
class CrawlOptions:
    lang: str
    country_iso2: str
    categories: List[str]
    custom_feeds: List[str]
    custom_keywords: List[str]
    fetch_fulltext: bool
    max_items_per_feed: int
    request_timeout_sec: int
    per_domain_delay_ms: int


def crawl_into_cache(
    cache_dir,
    options: CrawlOptions,
    log_cb: Callable[[str], None],
    status_cb: Callable[[str], None],
) -> Dict[str, int]:
    cache = Cache(cache_dir)
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    saved = 0
    skipped_paywall = 0
    skipped_keyword = 0
    feed_count = 0
    article_attempts = 0
    last_seen: Dict[str, float] = {}

    try:
        for category in options.categories:
            feed_urls = feeds_for(options.lang, options.country_iso2, category, options.custom_feeds)
            if not feed_urls:
                log_cb(f"[{category}] no feeds configured")
                continue
            for feed_url in feed_urls:
                feed_count += 1
                status_cb(f"{category}: {feed_url}")
                log_cb(f"Feed: {feed_url}")
                try:
                    parsed = feedparser.parse(feed_url)
                except Exception as exc:
                    log_cb(f"  parse error: {exc}")
                    continue
                entries = list(parsed.entries)[: options.max_items_per_feed]
                for entry in entries:
                    article_attempts += 1
                    url = (getattr(entry, "link", "") or "").strip()
                    if not url:
                        continue
                    title = (getattr(entry, "title", "") or "").strip() or url
                    summary = (getattr(entry, "summary", "") or getattr(entry, "description", "") or "").strip()
                    published = (getattr(entry, "published", "") or getattr(entry, "updated", "") or "").strip()
                    source = (getattr(parsed.feed, "title", "") or urlparse(url).netloc).strip()

                    if _is_paywall_domain(url):
                        skipped_paywall += 1
                        log_cb(f"  skip paywall domain: {title[:80]}")
                        continue

                    if category == "custom" and options.custom_keywords:
                        blob = (title + " " + summary).lower()
                        if not any(k in blob for k in options.custom_keywords):
                            skipped_keyword += 1
                            continue

                    feed_image_url = _find_feed_image(entry, summary, url)
                    thumb_path = _ensure_thumb(cache, session, feed_image_url, category, title, options.request_timeout_sec, options.per_domain_delay_ms, last_seen)

                    html_to_store = ""
                    summary_text = _plain(summary)
                    if options.fetch_fulltext:
                        html = _fetch_url(session, url, options.request_timeout_sec, options.per_domain_delay_ms, last_seen)
                        if html:
                            ex = extract_article(url, html, title, summary, lead_image_override=feed_image_url, hero_src=Path(thumb_path).as_uri() if thumb_path else "")
                            if ex.is_paywalled:
                                skipped_paywall += 1
                                log_cb(f"  skip paywall text: {title[:80]}")
                                continue
                            if ex.lead_image_url and (not thumb_path or _is_placeholder(thumb_path)):
                                thumb_path = _ensure_thumb(cache, session, ex.lead_image_url, category, title, options.request_timeout_sec, options.per_domain_delay_ms, last_seen)
                                ex = extract_article(url, html, title, summary, lead_image_override=ex.lead_image_url, hero_src=Path(thumb_path).as_uri() if thumb_path else "")
                            html_to_store = ex.content_html
                            summary_text = ex.summary_text or summary_text
                        else:
                            html_to_store = wrap_summary(title, url, summary or f"<p>{title}</p>", hero_src=Path(thumb_path).as_uri() if thumb_path else "")
                    else:
                        html_to_store = wrap_summary(title, url, summary or f"<p>{title}</p>", hero_src=Path(thumb_path).as_uri() if thumb_path else "")

                    cache.upsert_article(
                        url=url,
                        category=category,
                        lang=options.lang,
                        country_iso2=options.country_iso2,
                        title=title,
                        source=source,
                        published=published,
                        summary=summary_text,
                        content_html=html_to_store,
                        thumbnail_path=thumb_path,
                    )
                    saved += 1
                log_cb(f"  done: {len(entries)} items checked")
    finally:
        cache.close()
        session.close()

    return {
        "saved": saved,
        "skipped_paywall": skipped_paywall,
        "skipped_keyword": skipped_keyword,
        "feeds": feed_count,
        "attempts": article_attempts,
    }


def _is_paywall_domain(url: str) -> bool:
    host = urlparse(url).netloc.lower().lstrip("www.")
    return any(host == d or host.endswith("." + d) for d in PAYWALL_DOMAIN_DENYLIST)


def _plain(html: str) -> str:
    try:
        from bs4 import BeautifulSoup
        return BeautifulSoup(html, "lxml").get_text(" ", strip=True)
    except Exception:
        return html


def _fetch_url(session: requests.Session, url: str, timeout: int, delay_ms: int, last_seen: Dict[str, float]) -> Optional[str]:
    host = urlparse(url).netloc.lower()
    now = time.time()
    prev = last_seen.get(host, 0.0)
    wait = (delay_ms / 1000.0) - (now - prev)
    if wait > 0:
        time.sleep(wait)
    last_seen[host] = time.time()
    try:
        resp = session.get(url, timeout=timeout)
        if resp.status_code >= 400:
            return None
        resp.encoding = resp.apparent_encoding or resp.encoding
        return resp.text
    except Exception:
        return None


def _find_feed_image(entry, summary_html: str, base_url: str) -> str:
    media = getattr(entry, "media_content", None) or []
    for item in media:
        url = (item.get("url") or "").strip()
        if url:
            return urljoin(base_url, url)
    thumbs = getattr(entry, "media_thumbnail", None) or []
    for item in thumbs:
        url = (item.get("url") or "").strip()
        if url:
            return urljoin(base_url, url)
    links = getattr(entry, "links", None) or []
    for item in links:
        href = (item.get("href") or "").strip()
        typ = (item.get("type") or "").lower()
        if href and typ.startswith("image/"):
            return urljoin(base_url, href)
    m = re.search(r"<img[^>]+src=[\"']([^\"']+)[\"']", summary_html or "", flags=re.I)
    if m:
        return urljoin(base_url, m.group(1).strip())
    return ""


def _ensure_thumb(cache: Cache, session: requests.Session, image_url: str, category: str, title: str, timeout: int, delay_ms: int, last_seen: Dict[str, float]) -> str:
    if image_url:
        downloaded = _download_image(cache, session, image_url, timeout, delay_ms, last_seen)
        if downloaded:
            return downloaded
    return _placeholder_thumb(cache, category, title)


def _download_image(cache: Cache, session: requests.Session, image_url: str, timeout: int, delay_ms: int, last_seen: Dict[str, float]) -> str:
    host = urlparse(image_url).netloc.lower()
    now = time.time()
    prev = last_seen.get(host, 0.0)
    wait = (delay_ms / 1000.0) - (now - prev)
    if wait > 0:
        time.sleep(wait)
    last_seen[host] = time.time()
    url_hash = _hash(image_url)
    existing = next(cache.thumbs_dir.glob(url_hash + ".*"), None)
    if existing and existing.exists():
        return str(existing)
    try:
        resp = session.get(image_url, timeout=timeout, stream=True)
        if resp.status_code >= 400:
            return ""
        content_type = (resp.headers.get("content-type") or "").split(";")[0].strip().lower()
        if not content_type.startswith("image/"):
            return ""
        ext = mimetypes.guess_extension(content_type) or Path(urlparse(image_url).path).suffix or ".img"
        if ext == ".jpe":
            ext = ".jpg"
        target = cache.thumbs_dir / f"{url_hash}{ext}"
        data = resp.content
        if len(data) > 3_500_000:
            return ""
        target.write_bytes(data)
        return str(target)
    except Exception:
        return ""


def _placeholder_thumb(cache: Cache, category: str, title: str) -> str:
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
    c1, c2 = colors.get(category, ("#6b8cff", "#263556"))
    name = re.sub(r"[^a-z0-9_-]+", "_", category.lower())
    target = cache.thumbs_dir / f"placeholder_{name}.svg"
    if not target.exists():
        label = html_lib.escape(category.upper())
        svg = f"""<svg xmlns='http://www.w3.org/2000/svg' width='1200' height='630' viewBox='0 0 1200 630'>
<defs>
<linearGradient id='g' x1='0' y1='0' x2='1' y2='1'>
<stop offset='0%' stop-color='{c1}'/>
<stop offset='100%' stop-color='{c2}'/>
</linearGradient>
</defs>
<rect width='1200' height='630' rx='34' fill='#0d1117'/>
<rect x='28' y='28' width='1144' height='574' rx='28' fill='url(#g)' opacity='0.86'/>
<circle cx='1030' cy='120' r='180' fill='rgba(255,255,255,0.08)'/>
<circle cx='180' cy='560' r='220' fill='rgba(255,255,255,0.06)'/>
<text x='68' y='126' font-family='Segoe UI, Arial, sans-serif' font-size='42' fill='white' opacity='0.88'>{label}</text>
<text x='68' y='226' font-family='Segoe UI, Arial, sans-serif' font-size='68' font-weight='700' fill='white'>NewsCleanroom</text>
<text x='68' y='300' font-family='Segoe UI, Arial, sans-serif' font-size='30' fill='white' opacity='0.88'>Offline preview image</text>
</svg>"""
        target.write_text(svg, encoding="utf-8")
    return str(target)


def _hash(value: str) -> str:
    import hashlib
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _is_placeholder(path: str) -> bool:
    return Path(path).name.startswith("placeholder_")
