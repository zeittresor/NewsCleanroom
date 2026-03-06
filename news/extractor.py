from __future__ import annotations

import re
from dataclasses import dataclass
from bs4 import BeautifulSoup

PAYWALL_MARKERS = [
    "subscribe", "subscription", "register to continue", "sign in to continue", "paywall",
    "abonnieren", "zahlungspflicht", "abo", "nur für abonnenten",
    "réservé aux abonnés", "abonnez", "abonnement",
    "suscríbete", "solo suscriptores",
    "передплат", "для передплатників",
    "подпис", "только для подписчиков",
    "订阅", "付费", "會員", "会员",
]

TRASH_HINTS = [
    "cookie", "consent", "newsletter", "promo", "advert", "banner", "social", "share",
    "related", "recommend", "comment", "footer", "header", "nav", "aside", "sponsor"
]

@dataclass
class ExtractResult:
    title: str
    summary_text: str
    content_html: str
    is_paywalled: bool

def _clean_soup(soup: BeautifulSoup) -> None:
    for tag in soup(["script", "style", "noscript", "iframe", "svg"]):
        tag.decompose()
    for tag_name in ("header", "footer", "nav", "aside", "form"):
        for t in soup.find_all(tag_name):
            t.decompose()
    def is_trash(tag) -> bool:
        attrs = " ".join([
            " ".join(tag.get("class", [])),
            tag.get("id", "") or "",
            tag.get("role", "") or "",
            tag.get("aria-label", "") or "",
        ]).lower()
        return any(h in attrs for h in TRASH_HINTS)
    for t in list(soup.find_all(is_trash)):
        try:
            t.decompose()
        except Exception:
            pass

def _pick_container(soup: BeautifulSoup):
    selectors = [
        "article",
        "main",
        "[itemprop='articleBody']",
        ".article-body",
        ".story-body",
        ".entry-content",
        ".post-content",
        "#article-body",
        "#main-content",
    ]
    for sel in selectors:
        node = soup.select_one(sel)
        if node:
            return node
    best = None
    best_score = 0
    for node in soup.find_all(["div", "section"]):
        text = node.get_text(" ", strip=True)
        score = len(text)
        if score > best_score:
            best = node
            best_score = score
    return best or soup.body or soup

def extract_article(url: str, html: str, fallback_title: str, fallback_summary: str) -> ExtractResult:
    soup = BeautifulSoup(html, "lxml")
    _clean_soup(soup)
    container = _pick_container(soup)
    title = fallback_title.strip() or (soup.title.get_text(" ", strip=True) if soup.title else "Article")
    # remove tiny paragraphs and noisy links
    for a in container.find_all("a"):
        a["target"] = "_blank"
        a["rel"] = "noopener noreferrer"
    for node in list(container.find_all(["div", "section"])):
        txt = node.get_text(" ", strip=True)
        if len(txt) < 40 and not node.find("img"):
            try:
                node.decompose()
            except Exception:
                pass
    content_html = str(container)
    text = BeautifulSoup(content_html, "lxml").get_text("\n", strip=True)
    compact = re.sub(r"\s+", " ", text).strip()
    lower = compact.lower()
    html_lower = html.lower()
    is_paywalled = any(m in lower for m in PAYWALL_MARKERS)
    if not is_paywalled and len(compact) < 500 and any(m in html_lower for m in PAYWALL_MARKERS):
        is_paywalled = True
    if not compact:
        compact = fallback_summary.strip()
    wrapped = _wrap_article(title, url, content_html if compact else f"<p>{fallback_summary}</p>")
    return ExtractResult(
        title=title,
        summary_text=compact[:1400] if compact else fallback_summary.strip(),
        content_html=wrapped,
        is_paywalled=is_paywalled,
    )

def wrap_summary(title: str, url: str, summary_html: str) -> str:
    return _wrap_article(title, url, summary_html)

def _wrap_article(title: str, url: str, body_html: str) -> str:
    safe_title = title.replace("<", "&lt;").replace(">", "&gt;")
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        f"<title>{safe_title}</title>"
        "<style>"
        "body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;"
        "margin:0;background:#0e1116;color:#e6e8ee;line-height:1.55;}"
        ".wrap{max-width:900px;margin:0 auto;padding:24px;}"
        ".meta{font-size:12px;opacity:.8;margin-bottom:16px;}"
        "a{color:#7aa2ff;}img{max-width:100%;height:auto;border-radius:12px;}"
        "pre,code{white-space:pre-wrap;word-break:break-word;}"
        "</style></head><body><div class='wrap'>"
        f"<div class='meta'><a href='{url}'>{url}</a></div>"
        f"{body_html}"
        "</div></body></html>"
    )
