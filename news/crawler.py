from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlparse

import feedparser
import requests

from .cache import Cache
from .config import PAYWALL_DOMAIN_DENYLIST, feeds_for
from .extractor import extract_article, wrap_summary

USER_AGENT = "NewsCleanroom/2.0 (+desktop rss reader)"

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

                    html_to_store = ""
                    summary_text = _plain(summary)
                    if options.fetch_fulltext:
                        html = _fetch_url(session, url, options.request_timeout_sec, options.per_domain_delay_ms, last_seen)
                        if html:
                            ex = extract_article(url, html, title, summary)
                            if ex.is_paywalled:
                                skipped_paywall += 1
                                log_cb(f"  skip paywall text: {title[:80]}")
                                continue
                            html_to_store = ex.content_html
                            summary_text = ex.summary_text or summary_text
                        else:
                            html_to_store = wrap_summary(title, url, summary or f"<p>{title}</p>")
                    else:
                        html_to_store = wrap_summary(title, url, summary or f"<p>{title}</p>")

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
