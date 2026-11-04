# AI-News

Täglicher KI-Newsletter (Fokus Deutschland/EU, kleiner Welt-Teil) als installierbare Web-App (PWA).

## Aufbau
- `scripts/build_newsletter.py` – Feeds abrufen, filtern, mit Claude aufbereiten, nach `docs/data/` schreiben.
  Nur Standardbibliothek + `anthropic` (wird nur importiert, wenn `ANTHROPIC_API_KEY` gesetzt ist).
- `scripts/feeds.json` – Quellenliste.
- `docs/` – statische App (kein Build-Schritt, kein Framework): `index.html`, `app.js`, `style.css`, `sw.js`.
- `.github/workflows/newsletter.yml` – täglicher Lauf + Deployment auf GitHub Pages.

## Befehle
- Tests: `python3 -m unittest discover -s tests`
- App lokal: `cd docs && python3 -m http.server 8000`

## Konventionen
- Code, Kommentare und UI-Texte auf Deutsch.
- Datenformat (`docs/data/latest.json`) ist die Schnittstelle zwischen Skript und App – Änderungen an beiden Seiten nachziehen.
- Inhalte aus Feeds/Claude in der App nie als HTML einsetzen, nur über `textContent`; Links nur http(s).
- Bei Änderungen an App-Dateien `VERSION` in `docs/sw.js` hochzählen, sonst sehen Handys die alte Version.
- `docs/data/` wird vom Bot committet – nicht von Hand bearbeiten.
