# AI-News

Ein ruhiger, täglicher Überblick über Entwicklungen in der künstlichen Intelligenz –
mit Schwerpunkt **Deutschland und EU** und einem kleinen Abschnitt **Weltweit**.
Gedacht als App fürs Handy (installierbare Web-App, funktioniert auch offline).

## So funktioniert es

1. **GitHub Actions, ca. 4–5 Uhr:** `scripts/build_newsletter.py sammeln` liest rund 15 Nachrichtenfeeds
   (`scripts/feeds.json`), behält KI-Meldungen der letzten 36 Stunden, entfernt Dubletten und legt sie in
   `eingang/meldungen.json` ab. Sofort erscheint eine Ausgabe mit den Schlagzeilen.
2. **Claude, 6:41 Uhr:** Eine geplante Aufgabe in Claude Code (über das Claude-Abo, ohne Zusatzkosten)
   folgt `scripts/redaktion.md`: fasst auf Deutsch zusammen, legt Doppelmeldungen zusammen, ordnet nach
   Deutschland / EU / Welt, schreibt die „Lage“ des Tages und pusht `eingang/ausgabe.json`.
3. **GitHub Actions:** prüft die Ausgabe streng, ersetzt die Schlagzeilen-Ausgabe und veröffentlicht sie.
   Ältere Ausgaben bleiben 90 Tage im Archiv.

## Einrichtung

- **GitHub Pages:** Settings → Pages → *Source*: **GitHub Actions**.
- **App aufs Handy:** `https://johklu.github.io/AI-News/` öffnen, dann
  - iPhone (Safari): Teilen → *Zum Home-Bildschirm*
  - Android (Chrome): Menü ⋮ → *App installieren*
- Die geplante Claude-Aufgabe verwaltest du unter claude.ai/code (geplante Aufgaben).

## Kosten

Keine Zusatzkosten: Claude läuft über dein Abo (ein Lauf pro Tag verbraucht etwas Nutzungskontingent),
GitHub Actions und Pages sind für öffentliche Repositories kostenlos.

## Anpassen

- **Quellen:** `scripts/feeds.json` (Region `de`, `eu` oder `welt`; `nur_ki: false` filtert nach KI-Stichworten).
- **Ton, Umfang, Schwerpunkte:** `scripts/redaktion.md`.
- **Uhrzeit:** `cron` in `.github/workflows/newsletter.yml` (UTC).

## Lokal ausprobieren

```bash
python3 -m unittest discover -s tests
python3 scripts/build_newsletter.py sammeln
python3 scripts/build_newsletter.py fertigstellen   # ohne eingang/ausgabe.json: nur Schlagzeilen
cd docs && python3 -m http.server 8000             # dann http://localhost:8000
```
