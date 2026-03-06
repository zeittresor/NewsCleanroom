# NewsCleanroom v2

Stabiler Neuaufbau des News-Readers mit PyQt6.

## Merkmale

- dunkles modernes Interface
- Kategorien per Checkbox
- UI-Sprache: Englisch, Deutsch, Französisch, Spanisch, Ukrainisch, Russisch, vereinfachtes Chinesisch
- Artikel werden per RSS eingesammelt und lokal gecacht
- Paywall-/Abo-Seiten werden best-effort übersprungen
- Offline-Webseite wird aus dem Cache erzeugt
- eigenes Feed-Set und eigene Keywords für die Kategorie `Custom`
- keine QtWebEngine-Abhängigkeit, kein pandas, kein readability-lxml

## Start (Windows)

Doppelklick auf `run_windows.bat`

oder:

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

## Hinweise

- Für maximale Stabilität nutzt diese Version nur kuratierte RSS-Feeds und optional eigene RSS-Feeds.
- Die Kategorie `Custom` verwendet deine in den Einstellungen hinterlegten Custom-Feeds.
- Wenn ein Artikel sich nicht vollständig extrahieren lässt, wird wenigstens die RSS-Zusammenfassung gespeichert.
- Die Offline-Seite liegt nach dem Erzeugen unter `cache/site/index.html`.
