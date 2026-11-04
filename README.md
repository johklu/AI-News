# AI-News

Ein ruhiger, täglicher Überblick über Entwicklungen in der künstlichen Intelligenz –
mit Schwerpunkt **Deutschland und EU** und einem kleinen Abschnitt **Weltweit**.
Gedacht als App fürs Handy (installierbare Web-App, funktioniert auch offline).

## So funktioniert es

1. Jeden Morgen startet GitHub Actions `scripts/build_newsletter.py`.
2. Das Skript liest rund 15 Nachrichtenfeeds (`scripts/feeds.json`), behält KI-Meldungen
   der letzten 36 Stunden und entfernt Dubletten.
3. Claude fasst die Meldungen auf Deutsch zusammen, legt Doppelmeldungen zusammen, ordnet sie
   Deutschland / EU / Welt zu und schreibt eine kurze „Lage“ des Tages.
   Ohne API-Schlüssel gibt es nur die Schlagzeilen.
4. Das Ergebnis landet in `docs/data/` (90 Tage Archiv) und wird über GitHub Pages ausgeliefert.

## Einrichtung (einmalig)

1. **API-Schlüssel hinterlegen:** Settings → Secrets and variables → Actions → *New repository secret*,
   Name `ANTHROPIC_API_KEY`. Einen Schlüssel gibt es unter https://platform.claude.com.
2. **GitHub Pages einschalten:** Settings → Pages → *Source*: **GitHub Actions**.
3. **Erste Ausgabe erzeugen:** Actions → *Newsletter erstellen und veröffentlichen* → *Run workflow*.
4. **Aufs Handy holen:** `https://<dein-name>.github.io/AI-News/` öffnen, dann
   - iPhone (Safari): Teilen → *Zum Home-Bildschirm*
   - Android (Chrome): Menü ⋮ → *App installieren*

## Anpassen

- **Quellen:** `scripts/feeds.json` (Region `de`, `eu` oder `welt`; `nur_ki: false` filtert nach KI-Stichworten).
- **Ton, Umfang, Schwerpunkte:** Systemprompt `SYSTEM` in `scripts/build_newsletter.py`.
- **Uhrzeit:** `cron` in `.github/workflows/newsletter.yml` (UTC).
- **Modell:** Umgebungsvariable `CLAUDE_MODEL` (Standard `claude-opus-5-5`).

## Kosten

Ein Lauf schickt etwa 15–25 Tsd. Tokens an Claude und bekommt 2–4 Tsd. zurück –
mit Claude Opus 5.5 grob 0,10–0,25 US-Dollar pro Tag (also etwa 3–7 $ im Monat). GitHub Actions und Pages sind für
öffentliche Repositories kostenlos.

## Lokal ausprobieren

```bash
python3 -m unittest discover -s tests          # Tests
ANTHROPIC_API_KEY=… python3 scripts/build_newsletter.py
cd docs && python3 -m http.server 8000        # dann http://localhost:8000
```
