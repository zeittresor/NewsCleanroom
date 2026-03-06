from __future__ import annotations

import mimetypes
import re
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import feedparser
import requests

from .cache import Cache, canonicalize_url, make_placeholder_thumb, normalize_title
from .config import PAYWALL_DOMAIN_DENYLIST, feeds_for
from .extractor import extract_article, wrap_summary

USER_AGENT = "NewsCleanroom/2.4 (+desktop rss reader)"

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
    history_days: int

def crawl_into_cache(cache_dir, options: CrawlOptions, log_cb: Callable[[str], None], status_cb: Callable[[str], None], progress_cb: Optional[Callable[[int, int], None]] = None) -> Dict[str, int]:
    cache = Cache(cache_dir)
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    saved = skipped_paywall = skipped_keyword = skipped_duplicate = skipped_old = 0
    feed_count = article_attempts = 0
    last_seen: Dict[str, float] = {}
    seen_canonical: set[str] = set()
    seen_source_title: set[tuple[str, str]] = set()
    tasks: List[tuple[str, object, str]] = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=max(1, int(options.history_days)))

    try:
        for row in cache.list_articles(lang=options.lang, categories=options.categories, search="", limit=5000):
            canon = canonicalize_url(row.url)
            if canon:
                seen_canonical.add(canon)
            tkey = normalize_title(row.title)
            skey = (row.source or "").strip().lower()
            if skey and tkey:
                seen_source_title.add((skey, tkey))

        for category in options.categories:
            feed_urls = feeds_for(options.lang, options.country_iso2, category, options.custom_feeds)
            if not feed_urls:
                log_cb(f"[{category}] no feeds configured")
                continue
            for feed_url in feed_urls:
                feed_count += 1
                log_cb(f"Feed: {feed_url}")
                try:
                    parsed = feedparser.parse(feed_url)
                except Exception as exc:
                    log_cb(f"  parse error: {exc}")
                    continue
                source = (getattr(parsed.feed, "title", "") or urlparse(feed_url).netloc).strip()
                entries = list(parsed.entries)[: options.max_items_per_feed]
                fresh = []
                for entry in entries:
                    dt = _entry_datetime(entry)
                    if dt and dt < cutoff:
                        skipped_old += 1
                        continue
                    fresh.append(entry)
                log_cb(f"  queued: {len(fresh)} items")
                for entry in fresh:
                    tasks.append((category, entry, source))

        total = max(len(tasks), 1)
        done = 0
        if progress_cb:
            progress_cb(0, total)

        for category, entry, source in tasks:
            article_attempts += 1
            raw_url = (getattr(entry, "link", "") or "").strip()
            title = (getattr(entry, "title", "") or "").strip() or raw_url
            if not raw_url:
                done += 1
                if progress_cb: progress_cb(done, total)
                continue
            url = canonicalize_url(raw_url)
            title_key = normalize_title(title)
            summary = (getattr(entry, "summary", "") or getattr(entry, "description", "") or "").strip()
            published = (getattr(entry, "published", "") or getattr(entry, "updated", "") or "").strip()
            source_key = source.lower()
            status_cb(f"{min(done+1,total)}/{total} · {title[:72]}")

            if url and url in seen_canonical:
                skipped_duplicate += 1
                log_cb(f"  skip duplicate url: {title[:80]}")
                done += 1
                if progress_cb: progress_cb(done, total)
                continue
            if source_key and title_key and (source_key, title_key) in seen_source_title:
                skipped_duplicate += 1
                log_cb(f"  skip duplicate title: {title[:80]}")
                done += 1
                if progress_cb: progress_cb(done, total)
                continue
            if _is_paywall_domain(url):
                skipped_paywall += 1
                log_cb(f"  skip paywall domain: {title[:80]}")
                done += 1
                if progress_cb: progress_cb(done, total)
                continue
            if category == "custom" and options.custom_keywords:
                blob = (title + " " + summary).lower()
                if not any(k in blob for k in options.custom_keywords):
                    skipped_keyword += 1
                    done += 1
                    if progress_cb: progress_cb(done, total)
                    continue

            feed_image_url = _find_feed_image(entry, summary, url)
            if _is_bad_preview_url(feed_image_url):
                feed_image_url = ""
            thumb_path = _ensure_thumb(cache, session, feed_image_url, category, title, options.request_timeout_sec, options.per_domain_delay_ms, last_seen)

            summary_text = _plain(summary)
            if options.fetch_fulltext:
                html = _fetch_url(session, raw_url, options.request_timeout_sec, options.per_domain_delay_ms, last_seen)
                if html:
                    ex = extract_article(raw_url, html, title, summary, lead_image_override=feed_image_url, hero_src=Path(thumb_path).as_uri() if thumb_path else "")
                    if ex.is_paywalled:
                        skipped_paywall += 1
                        log_cb(f"  skip paywall text: {title[:80]}")
                        done += 1
                        if progress_cb: progress_cb(done, total)
                        continue
                    lead_url = ex.lead_image_url if not _is_bad_preview_url(ex.lead_image_url) else ""
                    if lead_url and (not thumb_path or _is_placeholder(thumb_path)):
                        thumb_path = _ensure_thumb(cache, session, lead_url, category, title, options.request_timeout_sec, options.per_domain_delay_ms, last_seen)
                        ex = extract_article(raw_url, html, title, summary, lead_image_override=lead_url, hero_src=Path(thumb_path).as_uri() if thumb_path else "")
                    html_to_store = ex.content_html
                    summary_text = ex.summary_text or summary_text
                else:
                    html_to_store = wrap_summary(title, raw_url, summary or f"<p>{title}</p>", hero_src=Path(thumb_path).as_uri() if thumb_path else "")
            else:
                html_to_store = wrap_summary(title, raw_url, summary or f"<p>{title}</p>", hero_src=Path(thumb_path).as_uri() if thumb_path else "")

            cache.upsert_article(url=url or raw_url, category=category, lang=options.lang, country_iso2=options.country_iso2, title=title, source=source, published=published, summary=summary_text, content_html=html_to_store, thumbnail_path=thumb_path)
            if url:
                seen_canonical.add(url)
            if source_key and title_key:
                seen_source_title.add((source_key, title_key))
            saved += 1
            done += 1
            if progress_cb: progress_cb(done, total)
    finally:
        cache.close()
        session.close()

    return {"saved": saved, "skipped_paywall": skipped_paywall, "skipped_keyword": skipped_keyword, "skipped_duplicate": skipped_duplicate, "skipped_old": skipped_old, "feeds": feed_count, "attempts": article_attempts, "total": len(tasks)}

def _entry_datetime(entry) -> Optional[datetime]:
    st = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
    if not st:
        return None
    try:
        return datetime.fromtimestamp(time.mktime(st), tz=timezone.utc)
    except Exception:
        return None

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
    if wait > 0: time.sleep(wait)
    last_seen[host] = time.time()
    try:
        resp = session.get(url, timeout=timeout)
        if resp.status_code >= 400: return None
        resp.encoding = resp.apparent_encoding or resp.encoding
        return resp.text
    except Exception:
        return None

def _find_feed_image(entry, summary_html: str, base_url: str) -> str:
    media = getattr(entry, "media_content", None) or []
    for item in media:
        url = (item.get("url") or "").strip()
        if url: return urljoin(base_url, url)
    thumbs = getattr(entry, "media_thumbnail", None) or []
    for item in thumbs:
        url = (item.get("url") or "").strip()
        if url: return urljoin(base_url, url)
    links = getattr(entry, "links", None) or []
    for item in links:
        href = (item.get("href") or "").strip()
        typ = (item.get("type") or "").lower()
        if href and typ.startswith("image/"): return urljoin(base_url, href)
    m = re.search(r"<img[^>]+src=[\"']([^\"']+)[\"']", summary_html or "", flags=re.I)
    if m: return urljoin(base_url, m.group(1).strip())
    return ""

def _ensure_thumb(cache: Cache, session: requests.Session, image_url: str, category: str, title: str, timeout: int, delay_ms: int, last_seen: Dict[str, float]) -> str:
    if image_url:
        downloaded = _download_image(cache, session, image_url, timeout, delay_ms, last_seen)
        if downloaded: return downloaded
    return make_placeholder_thumb(cache.thumbs_dir, category, title)

def _download_image(cache: Cache, session: requests.Session, image_url: str, timeout: int, delay_ms: int, last_seen: Dict[str, float]) -> str:
    if _is_bad_preview_url(image_url): return ""
    host = urlparse(image_url).netloc.lower()
    now = time.time()
    prev = last_seen.get(host, 0.0)
    wait = (delay_ms / 1000.0) - (now - prev)
    if wait > 0: time.sleep(wait)
    last_seen[host] = time.time()
    url_hash = _hash(image_url)
    existing = next(cache.thumbs_dir.glob(url_hash + ".*"), None)
    if existing and existing.exists(): return str(existing)
    try:
        resp = session.get(image_url, timeout=timeout, stream=True)
        if resp.status_code >= 400: return ""
        content_type = (resp.headers.get("content-type") or "").split(";")[0].strip().lower()
        if not content_type.startswith("image/"): return ""
        ext = mimetypes.guess_extension(content_type) or Path(urlparse(image_url).path).suffix or ".img"
        if ext == ".jpe": ext = ".jpg"
        target = cache.thumbs_dir / f"{url_hash}{ext}"
        data = resp.content
        if len(data) > 3_500_000 or len(data) < 3_000: return ""
        target.write_bytes(data)
        return str(target)
    except Exception:
        return ""

def _hash(value: str) -> str:
    import hashlib
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

def _is_placeholder(path: str) -> bool:
    return Path(path).name.startswith("placeholder_")

def _is_bad_preview_url(url: str) -> bool:
    if not url: return True
    low = url.lower()
    bad_bits = ["logo", "icon", "avatar", "sprite", "favicon", "apple-touch-icon", "blank.", "spacer.", "/pixel", "placeholder", "default-user"]
    if any(bit in low for bit in bad_bits): return True
    if re.search(r"(?i)(/|_)(logo|icon|avatar|favicon)(\.|_|/)", low): return True
    return False
