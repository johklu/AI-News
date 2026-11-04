# AI-News

Ein ruhiger, täglicher Überblick über Entwicklungen in der künstlichen Intelligenz –
mit Schwerpunkt **Deutschland und EU** und einem kleinen Abschnitt **Weltweit**.
Gedacht als App fürs Handy (installierbare Web-App, funktioniert auch offline).

## So funktioniert es

Jeden Morgen läuft auf GitHub der Workflow `.github/workflows/newsletter.yml`:

1. `scripts/build_newsletter.py sammeln` liest rund 15 Nachrichtenfeeds (`scripts/feeds.json`),
   behält KI-Meldungen der letzten 36 Stunden und entfernt Dubletten → `build/meldungen.json`.
2. **Claude Code** (über dein Claude-Abo) folgt dem Auftrag in `scripts/redaktion.md`:
   fasst auf Deutsch zusammen, legt Doppelmeldungen zusammen, ordnet nach Deutschland / EU / Welt
   und schreibt eine kurze „Lage“ des Tages → `build/ausgabe.json`.
3. `scripts/build_newsletter.py fertigstellen` prüft das Ergebnis und speichert es in `docs/data/`
   (90 Tage Archiv). Klappt Schritt 2 nicht, erscheinen an dem Tag nur die Schlagzeilen.
4. GitHub Pages liefert die App aus `docs/` aus.

## Einrichtung (einmalig)

1. **Abo-Token erzeugen** – auf einem Computer mit [Claude Code](https://code.claude.com/docs/en/setup):
   ```bash
   claude setup-token
   ```
   Im Browser bestätigen, den angezeigten Token kopieren. Er gilt ein Jahr.
2. **Token hinterlegen:** Repository → Settings → Secrets and variables → Actions →
   *New repository secret*, Name `CLAUDE_CODE_OAUTH_TOKEN`, Wert = der Token.
3. **GitHub Pages einschalten:** Settings → Pages → *Source*: **GitHub Actions**.
4. **Erste Ausgabe erzeugen:** Actions → *Newsletter erstellen und veröffentlichen* → *Run workflow*.
5. **Aufs Handy holen:** `https://johklu.github.io/AI-News/` öffnen, dann
   - iPhone (Safari): Teilen → *Zum Home-Bildschirm*
   - Android (Chrome): Menü ⋮ → *App installieren*

## Kosten

Keine Zusatzkosten: Claude läuft über dein Claude-Abo (ein Lauf pro Tag verbraucht etwas von deinem
Nutzungskontingent), GitHub Actions und Pages sind für öffentliche Repositories kostenlos.
Nach einem Jahr läuft der Token ab – dann Schritt 1 und 2 wiederholen.

## Anpassen

- **Quellen:** `scripts/feeds.json` (Region `de`, `eu` oder `welt`; `nur_ki: false` filtert nach KI-Stichworten).
- **Ton, Umfang, Schwerpunkte:** `scripts/redaktion.md`.
- **Uhrzeit:** `cron` in `.github/workflows/newsletter.yml` (UTC).

## Lokal ausprobieren

```bash
python3 -m unittest discover -s tests
python3 scripts/build_newsletter.py sammeln
python3 scripts/build_newsletter.py fertigstellen   # ohne build/ausgabe.json: nur Schlagzeilen
cd docs && python3 -m http.server 8000             # dann http://localhost:8000
```
