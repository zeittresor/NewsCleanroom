from __future__ import annotations

import webbrowser
from pathlib import Path
from typing import Dict, List

from PyQt6.QtCore import Qt, QThread, QUrl, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .cache import Cache
from .config import CATEGORIES, COUNTRIES, LANGS, get_default_country
from .crawler import CrawlOptions, crawl_into_cache
from .i18n import t
from .settings import AppSettings, load_settings, save_settings
from .sitegen import generate_offline_site

CATEGORY_LABELS = {
    "de": {"national": "[{country}]", "world": "Welt", "business": "Wirtschaft", "ai": "Künstliche Intelligenz", "entertainment": "Unterhaltung", "sports": "Sport", "it": "IT", "science": "Wissen", "politics": "Politik", "health": "Gesundheit", "custom": "Eigenes"},
    "fr": {"national": "[{country}]", "world": "Monde", "business": "Économie", "ai": "IA", "entertainment": "Divertissement", "sports": "Sport", "it": "Informatique", "science": "Science", "politics": "Politique", "health": "Santé", "custom": "Personnalisé"},
    "es": {"national": "[{country}]", "world": "Mundo", "business": "Economía", "ai": "IA", "entertainment": "Entretenimiento", "sports": "Deportes", "it": "TI", "science": "Ciencia", "politics": "Política", "health": "Salud", "custom": "Personalizado"},
    "uk": {"national": "[{country}]", "world": "Світ", "business": "Економіка", "ai": "ШІ", "entertainment": "Розваги", "sports": "Спорт", "it": "ІТ", "science": "Наука", "politics": "Політика", "health": "Здоров’я", "custom": "Власне"},
    "ru": {"national": "[{country}]", "world": "Мир", "business": "Экономика", "ai": "ИИ", "entertainment": "Развлечения", "sports": "Спорт", "it": "ИТ", "science": "Наука", "politics": "Политика", "health": "Здоровье", "custom": "Своё"},
    "zh-Hans": {"national": "[{country}]", "world": "全球", "business": "经济", "ai": "人工智能", "entertainment": "娱乐", "sports": "体育", "it": "IT", "science": "科学", "politics": "政治", "health": "健康", "custom": "自定义"},
}


class CrawlThread(QThread):
    log = pyqtSignal(str)
    status = pyqtSignal(str)
    done = pyqtSignal(dict)

    def __init__(self, cache_dir: Path, options: CrawlOptions):
        super().__init__()
        self.cache_dir = cache_dir
        self.options = options

    def run(self):
        try:
            result = crawl_into_cache(self.cache_dir, self.options, self.log.emit, self.status.emit)
            self.done.emit({"ok": True, **result})
        except Exception as exc:
            self.done.emit({"ok": False, "error": str(exc)})


class SettingsDialog(QDialog):
    def __init__(self, lang: str, settings_path: Path, settings: AppSettings, parent=None):
        super().__init__(parent)
        self.lang = lang
        self.settings_path = settings_path
        self.settings = settings
        self.setWindowTitle(t(lang, "settings"))
        self.resize(560, 420)

        root = QVBoxLayout(self)
        form = QFormLayout()
        self.ed_keywords = QLineEdit(settings.custom_keywords)
        form.addRow(t(lang, "custom_keywords"), self.ed_keywords)
        root.addLayout(form)

        root.addWidget(QLabel(t(lang, "custom_feeds")))
        self.feed_list = QListWidget()
        for url in settings.custom_feeds:
            self.feed_list.addItem(QListWidgetItem(url))
        root.addWidget(self.feed_list, 1)

        row = QHBoxLayout()
        self.btn_add = QPushButton(t(lang, "add_feed"))
        self.btn_remove = QPushButton(t(lang, "remove"))
        row.addWidget(self.btn_add)
        row.addWidget(self.btn_remove)
        row.addStretch(1)
        root.addLayout(row)

        advanced = QFormLayout()
        self.spin_items = QSpinBox()
        self.spin_items.setRange(5, 50)
        self.spin_items.setValue(settings.max_items_per_feed)
        advanced.addRow("Max items per feed", self.spin_items)

        self.spin_timeout = QSpinBox()
        self.spin_timeout.setRange(5, 60)
        self.spin_timeout.setValue(settings.request_timeout_sec)
        advanced.addRow("Request timeout (sec)", self.spin_timeout)

        self.spin_delay = QSpinBox()
        self.spin_delay.setRange(0, 5000)
        self.spin_delay.setSingleStep(100)
        self.spin_delay.setValue(settings.per_domain_delay_ms)
        advanced.addRow("Delay per domain (ms)", self.spin_delay)
        root.addLayout(advanced)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        self.btn_add.clicked.connect(self._on_add)
        self.btn_remove.clicked.connect(self._on_remove)

    def _on_add(self):
        value, ok = QInputDialog.getText(self, t(self.lang, "add_feed"), "Feed URL:")
        if ok and value.strip():
            self.feed_list.addItem(QListWidgetItem(value.strip()))

    def _on_remove(self):
        for item in self.feed_list.selectedItems():
            self.feed_list.takeItem(self.feed_list.row(item))

    def accept(self):
        self.settings.custom_keywords = self.ed_keywords.text().strip()
        self.settings.custom_feeds = [self.feed_list.item(i).text().strip() for i in range(self.feed_list.count()) if self.feed_list.item(i).text().strip()]
        self.settings.max_items_per_feed = int(self.spin_items.value())
        self.settings.request_timeout_sec = int(self.spin_timeout.value())
        self.settings.per_domain_delay_ms = int(self.spin_delay.value())
        save_settings(self.settings_path, self.settings)
        super().accept()


class MainWindow(QMainWindow):
    def __init__(self, cache: Cache, cache_dir: Path):
        super().__init__()
        self.cache = cache
        self.cache_dir = cache_dir
        self.settings_path = self.cache_dir / "settings.json"
        self.settings = load_settings(self.settings_path)
        self.lang = "de"
        self.country_iso2 = get_default_country(self.lang)
        self._rows = []
        self._current_url = ""
        self._current_article_id = None
        self._offline_index_path: Path | None = None
        self.setWindowTitle("NewsCleanroom")
        self.resize(1600, 980)
        self._build_ui()
        self._apply_i18n()
        self._reload_articles()
        self._show_placeholder()

    def _build_ui(self):
        root = QWidget()
        outer = QVBoxLayout(root)
        outer.setContentsMargins(12, 12, 12, 8)
        outer.setSpacing(10)

        top_panel = QGroupBox()
        top_layout = QGridLayout(top_panel)

        self.lbl_lang = QLabel()
        self.cmb_lang = QComboBox()
        for code, label in LANGS:
            self.cmb_lang.addItem(label, code)
        self.cmb_lang.setCurrentIndex(1)
        self.cmb_lang.currentIndexChanged.connect(self._on_lang_changed)

        self.lbl_country = QLabel()
        self.cmb_country = QComboBox()
        for code, label in COUNTRIES:
            self.cmb_country.addItem(f"{label} ({code})" if code != "AUTO" else label, code)
        self.cmb_country.setCurrentText("Germany (DE)")
        self.cmb_country.currentIndexChanged.connect(self._on_country_changed)

        self.chk_offline = QCheckBox()
        self.chk_offline.stateChanged.connect(self._reload_articles)
        self.chk_fulltext = QCheckBox()
        self.chk_fulltext.setChecked(True)

        self.ed_search = QLineEdit()
        self.ed_search.textChanged.connect(self._reload_articles)

        self.btn_update = QPushButton()
        self.btn_generate = QPushButton()
        self.btn_open_site = QPushButton()
        self.btn_open_site_internal = QPushButton()
        self.btn_settings = QPushButton()
        self.btn_update.clicked.connect(self._on_update)
        self.btn_generate.clicked.connect(self._on_generate_site)
        self.btn_open_site.clicked.connect(self._on_open_site)
        self.btn_open_site_internal.clicked.connect(self._on_open_site_internal)
        self.btn_settings.clicked.connect(self._on_settings)

        top_layout.addWidget(self.lbl_lang, 0, 0)
        top_layout.addWidget(self.cmb_lang, 0, 1)
        top_layout.addWidget(self.lbl_country, 0, 2)
        top_layout.addWidget(self.cmb_country, 0, 3)
        top_layout.addWidget(self.chk_offline, 0, 4)
        top_layout.addWidget(self.chk_fulltext, 0, 5)
        top_layout.addWidget(self.ed_search, 1, 0, 1, 4)
        top_layout.addWidget(self.btn_update, 1, 4)
        top_layout.addWidget(self.btn_generate, 1, 5)
        top_layout.addWidget(self.btn_open_site, 1, 6)
        top_layout.addWidget(self.btn_open_site_internal, 1, 7)
        top_layout.addWidget(self.btn_settings, 1, 8)

        outer.addWidget(top_panel)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        self.cat_group = QGroupBox()
        cat_group_layout = QVBoxLayout(self.cat_group)
        self.category_checks: Dict[str, QCheckBox] = {}
        for key, _label in CATEGORIES:
            cb = QCheckBox()
            cb.setChecked(key in {"national", "world", "business", "ai", "it", "science", "politics", "health"})
            cb.stateChanged.connect(self._reload_articles)
            self.category_checks[key] = cb
            cat_group_layout.addWidget(cb)
        cat_group_layout.addStretch(1)
        cat_scroll = QScrollArea()
        cat_scroll.setWidgetResizable(True)
        cat_scroll.setWidget(self.cat_group)
        left_layout.addWidget(cat_scroll, 2)

        self.table_group = QGroupBox()
        table_layout = QVBoxLayout(self.table_group)
        self.table = QTableWidget(0, 4)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.itemSelectionChanged.connect(self._on_table_select)
        table_layout.addWidget(self.table)
        left_layout.addWidget(self.table_group, 5)

        self.log_group = QGroupBox()
        log_layout = QVBoxLayout(self.log_group)
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setMinimumHeight(150)
        log_layout.addWidget(self.log_box)
        left_layout.addWidget(self.log_group, 2)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        action_row = QHBoxLayout()
        self.btn_open_original = QPushButton()
        self.btn_copy_url = QPushButton()
        self.btn_open_original.clicked.connect(self._open_original)
        self.btn_copy_url.clicked.connect(self._copy_url)
        action_row.addWidget(self.btn_open_original)
        action_row.addWidget(self.btn_copy_url)
        action_row.addStretch(1)
        right_layout.addLayout(action_row)

        self.viewer = QTextBrowser()
        self.viewer.setOpenLinks(False)
        self.viewer.setOpenExternalLinks(False)
        self.viewer.anchorClicked.connect(self._on_viewer_link_clicked)
        right_layout.addWidget(self.viewer, 1)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 5)
        outer.addWidget(splitter, 1)

        self.setCentralWidget(root)
        self.status = QStatusBar()
        self.setStatusBar(self.status)

    def _apply_i18n(self):
        self.setWindowTitle(t(self.lang, "app_title"))
        self.lbl_lang.setText(t(self.lang, "language"))
        self.lbl_country.setText(t(self.lang, "country"))
        self.chk_offline.setText(t(self.lang, "offline_mode"))
        self.chk_fulltext.setText(t(self.lang, "fetch_fulltext"))
        self.ed_search.setPlaceholderText(t(self.lang, "search"))
        self.btn_update.setText(t(self.lang, "update"))
        self.btn_generate.setText(t(self.lang, "generate_site"))
        self.btn_open_site.setText(t(self.lang, "open_site"))
        self.btn_open_site_internal.setText(t(self.lang, "open_site_internal"))
        self.btn_settings.setText(t(self.lang, "settings"))
        self.btn_open_original.setText(t(self.lang, "open_original"))
        self.btn_copy_url.setText(t(self.lang, "copy_url"))

        labels = CATEGORY_LABELS.get(self.lang, {})
        for key, default_label in CATEGORIES:
            label = labels.get(key, default_label)
            if "{country}" in label:
                label = label.format(country=self.country_iso2)
            self.category_checks[key].setText(label)

        self.cat_group.setTitle(t(self.lang, "categories"))
        self.table_group.setTitle(t(self.lang, "articles"))
        self.log_group.setTitle(t(self.lang, "log"))
        self.table.setHorizontalHeaderLabels([
            t(self.lang, "published"),
            t(self.lang, "article"),
            t(self.lang, "source"),
            t(self.lang, "category"),
        ])
        self.status.showMessage(t(self.lang, "status_offline") if self.chk_offline.isChecked() else t(self.lang, "status_ready"))

    def _selected_categories(self) -> List[str]:
        return [key for key, cb in self.category_checks.items() if cb.isChecked()]

    def _append_log(self, text: str):
        self.log_box.append(text)

    def _show_placeholder(self):
        html = (
            "<html><body style='background:#0c1017;color:#dbe6ff;font-family:Segoe UI,Arial,sans-serif;'>"
            "<div style='max-width:740px;margin:60px auto;padding:24px;border:1px solid rgba(255,255,255,.08);"
            "border-radius:18px;background:rgba(255,255,255,.03)'>"
            f"<h2 style='margin-top:0'>{t(self.lang, 'app_title')}</h2>"
            f"<p>{t(self.lang, 'viewer_placeholder')}</p>"
            "</div></body></html>"
        )
        self.viewer.setHtml(html)

    def _on_lang_changed(self):
        self.lang = self.cmb_lang.currentData()
        if self.cmb_country.currentData() == "AUTO":
            self.country_iso2 = get_default_country(self.lang)
        self._apply_i18n()
        self._reload_articles()
        if self.table.currentRow() < 0:
            self._show_placeholder()

    def _on_country_changed(self):
        value = self.cmb_country.currentData()
        self.country_iso2 = get_default_country(self.lang) if value == "AUTO" else value
        self._apply_i18n()
        self._reload_articles()

    def _reload_articles(self):
        rows = self.cache.list_articles(
            lang=self.lang,
            categories=self._selected_categories(),
            search=self.ed_search.text(),
            limit=800,
        )
        self._rows = rows
        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            stamp = (row.published or row.fetched_at)[:19].replace("T", " ")
            self.table.setItem(i, 0, QTableWidgetItem(stamp))
            self.table.setItem(i, 1, QTableWidgetItem(row.title))
            self.table.setItem(i, 2, QTableWidgetItem(row.source))
            self.table.setItem(i, 3, QTableWidgetItem(row.category))
        self.table.resizeColumnsToContents()
        self.status.showMessage(t(self.lang, "status_offline") if self.chk_offline.isChecked() else t(self.lang, "status_ready"))

    def _on_table_select(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self._rows):
            self._show_placeholder()
            return
        article = self._rows[row]
        self._current_article_id = article.id
        self._current_url = article.url
        self.viewer.setHtml(self.cache.get_article_html(article.id))

    def _on_update(self):
        if self.chk_offline.isChecked():
            self.status.showMessage(t(self.lang, "status_offline"))
            return
        cats = self._selected_categories()
        if not cats:
            QMessageBox.warning(self, t(self.lang, "update"), "Please select at least one category.")
            return
        self.btn_update.setEnabled(False)
        self.log_box.clear()
        keywords = [x.strip().lower() for x in self.settings.custom_keywords.split(",") if x.strip()]
        options = CrawlOptions(
            lang=self.lang,
            country_iso2=self.country_iso2,
            categories=cats,
            custom_feeds=list(self.settings.custom_feeds),
            custom_keywords=keywords,
            fetch_fulltext=self.chk_fulltext.isChecked(),
            max_items_per_feed=self.settings.max_items_per_feed,
            request_timeout_sec=self.settings.request_timeout_sec,
            per_domain_delay_ms=self.settings.per_domain_delay_ms,
        )
        self.thread = CrawlThread(self.cache_dir, options)
        self.thread.log.connect(self._append_log)
        self.thread.status.connect(lambda msg: self.status.showMessage(f"{t(self.lang, 'status_updating')} {msg}"))
        self.thread.done.connect(self._on_update_done)
        self.thread.start()

    def _on_update_done(self, result: dict):
        self.btn_update.setEnabled(True)
        if not result.get("ok"):
            QMessageBox.critical(self, t(self.lang, "update"), result.get("error", "Unknown error"))
            self.status.showMessage("Error.")
            return
        self.cache.close()
        self.cache = Cache(self.cache_dir)
        self._reload_articles()
        msg = (
            f"{t(self.lang, 'status_done')} "
            f"saved={result.get('saved', 0)}, "
            f"paywall_skips={result.get('skipped_paywall', 0)}, "
            f"keyword_skips={result.get('skipped_keyword', 0)}"
        )
        self.status.showMessage(msg)
        self._append_log(msg)

    def _on_generate_site(self):
        try:
            index = generate_offline_site(self.cache, lang=self.lang, categories=self._selected_categories())
            self._offline_index_path = index
        except Exception as exc:
            QMessageBox.critical(self, t(self.lang, "generate_site"), str(exc))
            return
        QMessageBox.information(self, t(self.lang, "generate_site"), str(index))

    def _ensure_site_index(self) -> Path | None:
        index = self.cache.site_dir / "index.html"
        if not index.exists():
            try:
                index = generate_offline_site(self.cache, lang=self.lang, categories=self._selected_categories())
                self._offline_index_path = index
            except Exception as exc:
                QMessageBox.critical(self, t(self.lang, "generate_site"), str(exc))
                return None
        return index

    def _on_open_site(self):
        index = self._ensure_site_index()
        if not index:
            return
        webbrowser.open(index.as_uri())

    def _on_open_site_internal(self):
        index = self._ensure_site_index()
        if not index:
            return
        self.viewer.setSource(QUrl.fromLocalFile(str(index)))

    def _on_settings(self):
        dialog = SettingsDialog(self.lang, self.settings_path, self.settings, self)
        if dialog.exec():
            self.settings = load_settings(self.settings_path)

    def _open_original(self):
        if self._current_url:
            webbrowser.open(self._current_url)

    def _copy_url(self):
        if self._current_url:
            QApplication.clipboard().setText(self._current_url)

    def _on_viewer_link_clicked(self, url: QUrl):
        if url.scheme() in {"http", "https"}:
            webbrowser.open(url.toString())
            return
        self.viewer.setSource(url)
