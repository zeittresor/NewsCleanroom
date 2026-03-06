from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List

@dataclass
class AppSettings:
    custom_keywords: str = ""
    custom_feeds: List[str] = None  # type: ignore
    max_items_per_feed: int = 15
    request_timeout_sec: int = 12
    per_domain_delay_ms: int = 600

    def __post_init__(self):
        if self.custom_feeds is None:
            self.custom_feeds = []

def load_settings(path: Path) -> AppSettings:
    if not path.exists():
        return AppSettings()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return AppSettings(
            custom_keywords=data.get("custom_keywords", ""),
            custom_feeds=list(data.get("custom_feeds", [])),
            max_items_per_feed=int(data.get("max_items_per_feed", 15)),
            request_timeout_sec=int(data.get("request_timeout_sec", 12)),
            per_domain_delay_ms=int(data.get("per_domain_delay_ms", 600)),
        )
    except Exception:
        return AppSettings()

def save_settings(path: Path, settings: AppSettings) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(settings), ensure_ascii=False, indent=2), encoding="utf-8")
