# AI-News

Täglicher KI-Newsletter (Fokus Deutschland/EU, kleiner Welt-Teil) als installierbare Web-App (PWA).

## Aufbau
- `scripts/build_newsletter.py` – nur Standardbibliothek, zwei Befehle:
  `sammeln` (Feeds → `build/meldungen.json`) und `fertigstellen` (`build/ausgabe.json` prüfen → `docs/data/`).
- `scripts/redaktion.md` – Auftrag an Claude Code, das im Workflow `build/ausgabe.json` schreibt.
  Claude läuft über das Abo (`CLAUDE_CODE_OAUTH_TOKEN`), nicht über die API – keine API-Aufrufe ins Skript einbauen.
- `scripts/feeds.json` – Quellenliste.
- `docs/` – statische App (kein Build-Schritt, kein Framework): `index.html`, `app.js`, `style.css`, `sw.js`.
- `.github/workflows/newsletter.yml` – täglicher Lauf (sammeln → Claude Code → fertigstellen) + Deployment auf GitHub Pages.
  Der Claude-Schritt darf nur `Read,Write`; danach wird alles außer `build/ausgabe.json` zurückgesetzt (Feeds sind fremder Text).

## Befehle
- Tests: `python3 -m unittest discover -s tests`
- App lokal: `cd docs && python3 -m http.server 8000`

## Konventionen
- Code, Kommentare und UI-Texte auf Deutsch.
- Datenformat (`docs/data/latest.json`) ist die Schnittstelle zwischen Skript und App – Änderungen an beiden Seiten nachziehen.
- Inhalte aus Feeds/Claude in der App nie als HTML einsetzen, nur über `textContent`; Links nur http(s).
- Bei Änderungen an App-Dateien `VERSION` in `docs/sw.js` hochzählen, sonst sehen Handys die alte Version.
- `docs/data/` wird vom Bot committet – nicht von Hand bearbeiten.
