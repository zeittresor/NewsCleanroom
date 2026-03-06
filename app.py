from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from news.cache import Cache
from news.theme import apply_dark_theme
from news.ui import MainWindow


def main():
    app = QApplication(sys.argv)
    apply_dark_theme(app)
    cache_dir = Path(__file__).resolve().parent / "cache"
    cache = Cache(cache_dir)
    window = MainWindow(cache, cache_dir)
    window.showMaximized()
    rc = app.exec()
    cache.close()
    sys.exit(rc)


if __name__ == "__main__":
    main()
