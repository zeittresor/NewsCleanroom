from __future__ import annotations

from typing import Dict, List, Tuple

LANGS = [
    ("en", "English"),
    ("de", "Deutsch"),
    ("fr", "Français"),
    ("es", "Español"),
    ("uk", "Українська"),
    ("ru", "Русский"),
    ("zh-Hans", "简体中文"),
]

COUNTRIES = [
    ("AUTO", "Auto"),
    ("DE", "Germany"),
    ("US", "United States"),
    ("GB", "United Kingdom"),
    ("FR", "France"),
    ("ES", "Spain"),
    ("UA", "Ukraine"),
    ("RU", "Russia"),
    ("CN", "China"),
]

DEFAULT_COUNTRY_BY_LANG = {
    "en": "US",
    "de": "DE",
    "fr": "FR",
    "es": "ES",
    "uk": "UA",
    "ru": "RU",
    "zh-Hans": "CN",
}

CATEGORIES = [
    ("national", "National"),
    ("world", "World"),
    ("business", "Business"),
    ("ai", "Artificial Intelligence"),
    ("entertainment", "Entertainment"),
    ("sports", "Sports"),
    ("it", "IT"),
    ("science", "Knowledge/Science"),
    ("politics", "Politics"),
    ("health", "Health"),
    ("custom", "Custom"),
]

# Primary category feeds by interface language
CATEGORY_FEEDS: Dict[str, Dict[str, List[str]]] = {
    "en": {
        "world": [
            "https://feeds.bbci.co.uk/news/world/rss.xml",
            "https://www.aljazeera.com/xml/rss/all.xml",
        ],
        "business": [
            "https://feeds.bbci.co.uk/news/business/rss.xml",
            "https://www.theguardian.com/business/rss",
        ],
        "ai": [
            "https://techcrunch.com/category/artificial-intelligence/feed/",
            "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml",
        ],
        "entertainment": [
            "https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml",
        ],
        "sports": [
            "https://feeds.bbci.co.uk/sport/rss.xml",
        ],
        "it": [
            "https://feeds.bbci.co.uk/news/technology/rss.xml",
            "https://www.theregister.com/headlines.atom",
            "https://rss.golem.de/rss.php?feed=RSS2.0",
            "https://rss.golem.de/rss.php?feed=RSS2.0&ms=internet",
        ],
        "science": [
            "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
        ],
        "politics": [
            "https://feeds.bbci.co.uk/news/politics/rss.xml",
        ],
        "health": [
            "https://feeds.bbci.co.uk/news/health/rss.xml",
        ],
        "custom": [],
    },
    "de": {
        "world": [
            "https://www.tagesschau.de/ausland/index~rss2.xml",
            "https://rss.dw.com/rdf/rss-de-all",
        ],
        "business": [
            "https://www.tagesschau.de/wirtschaft/index~rss2.xml",
            "https://rss.dw.com/rdf/rss-de-wirtschaft",
        ],
        "ai": [
            "https://www.heise.de/rss/heise-atom.xml",
        ],
        "entertainment": [
            "https://www.tagesschau.de/kultur/index~rss2.xml",
        ],
        "sports": [
            "https://www.tagesschau.de/sport/index~rss2.xml",
        ],
        "it": [
            "https://www.heise.de/rss/heise-Rubrik-IT-atom.xml",
            "https://www.heise.de/security/feed.xml",
            "https://rss.golem.de/rss.php?feed=RSS2.0&ms=internet",
            "https://rss.golem.de/rss.php?feed=RSS2.0&ms=security",
            "https://rss.golem.de/rss.php?feed=RSS2.0",
        ],
        "science": [
            "https://www.tagesschau.de/wissen/index~rss2.xml",
            "https://rss.dw.com/rdf/rss-de-wissen",
        ],
        "politics": [
            "https://www.tagesschau.de/inland/index~rss2.xml",
            "https://www.tagesschau.de/ausland/index~rss2.xml",
        ],
        "health": [
            "https://www.tagesschau.de/wissen/gesundheit/index~rss2.xml",
        ],
        "custom": [],
    },
    "fr": {
        "world": [
            "https://www.france24.com/fr/rss",
            "https://www.rfi.fr/fr/rss",
        ],
        "business": [
            "https://www.france24.com/fr/economie/rss",
        ],
        "ai": [
            "https://www.france24.com/fr/technologies/rss",
        ],
        "entertainment": [
            "https://www.france24.com/fr/culture/rss",
        ],
        "sports": [
            "https://www.france24.com/fr/sports/rss",
        ],
        "it": [
            "https://www.france24.com/fr/technologies/rss",
        ],
        "science": [
            "https://www.france24.com/fr/sciences/rss",
        ],
        "politics": [
            "https://www.france24.com/fr/france/rss",
        ],
        "health": [
            "https://www.rfi.fr/fr/rss",
        ],
        "custom": [],
    },
    "es": {
        "world": [
            "https://feeds.bbci.co.uk/mundo/rss.xml",
            "https://www.rtve.es/rss/",
        ],
        "business": [
            "https://www.rtve.es/rss/",
        ],
        "ai": [
            "https://www.rtve.es/rss/",
        ],
        "entertainment": [
            "https://www.rtve.es/rss/",
        ],
        "sports": [
            "https://www.rtve.es/rss/",
        ],
        "it": [
            "https://www.rtve.es/rss/",
        ],
        "science": [
            "https://www.rtve.es/rss/",
        ],
        "politics": [
            "https://www.rtve.es/rss/",
        ],
        "health": [
            "https://www.rtve.es/rss/",
        ],
        "custom": [],
    },
    "uk": {
        "world": ["https://www.pravda.com.ua/rss/"],
        "business": ["https://www.pravda.com.ua/rss/"],
        "ai": ["https://www.pravda.com.ua/rss/"],
        "entertainment": ["https://www.pravda.com.ua/rss/"],
        "sports": ["https://www.pravda.com.ua/rss/"],
        "it": ["https://www.pravda.com.ua/rss/"],
        "science": ["https://www.pravda.com.ua/rss/"],
        "politics": ["https://www.pravda.com.ua/rss/"],
        "health": ["https://www.pravda.com.ua/rss/"],
        "custom": [],
    },
    "ru": {
        "world": ["https://www.bbc.com/russian/index.xml"],
        "business": ["https://www.bbc.com/russian/index.xml"],
        "ai": ["https://www.bbc.com/russian/index.xml"],
        "entertainment": ["https://www.bbc.com/russian/index.xml"],
        "sports": ["https://www.bbc.com/russian/index.xml"],
        "it": ["https://www.bbc.com/russian/index.xml"],
        "science": ["https://www.bbc.com/russian/index.xml"],
        "politics": ["https://www.bbc.com/russian/index.xml"],
        "health": ["https://www.bbc.com/russian/index.xml"],
        "custom": [],
    },
    "zh-Hans": {
        "world": ["https://feeds.bbci.co.uk/zhongwen/simp/rss.xml"],
        "business": ["https://feeds.bbci.co.uk/zhongwen/simp/rss.xml"],
        "ai": ["https://feeds.bbci.co.uk/zhongwen/simp/rss.xml"],
        "entertainment": ["https://feeds.bbci.co.uk/zhongwen/simp/rss.xml"],
        "sports": ["https://feeds.bbci.co.uk/zhongwen/simp/rss.xml"],
        "it": ["https://feeds.bbci.co.uk/zhongwen/simp/rss.xml"],
        "science": ["https://feeds.bbci.co.uk/zhongwen/simp/rss.xml"],
        "politics": ["https://feeds.bbci.co.uk/zhongwen/simp/rss.xml"],
        "health": ["https://feeds.bbci.co.uk/zhongwen/simp/rss.xml"],
        "custom": [],
    },
}

# National feeds chosen by country first, otherwise by language
NATIONAL_FEEDS: Dict[str, List[str]] = {
    "DE": [
        "https://www.tagesschau.de/inland/index~rss2.xml",
        "https://rss.dw.com/rdf/rss-de-all",
    ],
    "US": [
        "https://feeds.npr.org/1001/rss.xml",
        "https://feeds.bbci.co.uk/news/rss.xml?edition=us",
    ],
    "GB": [
        "https://feeds.bbci.co.uk/news/uk/rss.xml",
        "https://www.theguardian.com/uk/rss",
    ],
    "FR": [
        "https://www.france24.com/fr/france/rss",
        "https://www.rfi.fr/fr/france/rss",
    ],
    "ES": [
        "https://www.rtve.es/rss/",
        "https://feeds.bbci.co.uk/mundo/rss.xml",
    ],
    "UA": [
        "https://www.pravda.com.ua/rss/",
    ],
    "RU": [
        "https://www.bbc.com/russian/index.xml",
    ],
    "CN": [
        "https://feeds.bbci.co.uk/zhongwen/simp/rss.xml",
    ],
}

PAYWALL_DOMAIN_DENYLIST = {
    "ft.com",
    "wsj.com",
    "nytimes.com",
    "economist.com",
    "bloomberg.com",
    "thetimes.co.uk",
    "lemonde.fr",
    "zeit.de",
    "faz.net",
    "elpais.com",
}

def get_default_country(lang: str) -> str:
    return DEFAULT_COUNTRY_BY_LANG.get(lang, "US")

def feeds_for(lang: str, country: str, category: str, custom_feeds: List[str]) -> List[str]:
    if category == "national":
        feeds = NATIONAL_FEEDS.get(country) or NATIONAL_FEEDS.get(get_default_country(lang), [])
        return list(feeds)
    if category == "custom":
        return list(custom_feeds)
    return list(CATEGORY_FEEDS.get(lang, CATEGORY_FEEDS["en"]).get(category, []))
