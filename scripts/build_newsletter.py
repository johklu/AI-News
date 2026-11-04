"""Sammelt KI-Nachrichten aus RSS/Atom-Feeds und baut daraus die Tagesausgabe.

  python scripts/build_newsletter.py sammeln
      (GitHub Actions, frühmorgens) Feeds abrufen, KI-Meldungen der letzten STUNDEN
      (Standard 36) behalten, Dubletten entfernen -> eingang/meldungen.json

  Danach schreibt eine geplante Claude-Code-Sitzung (über das Claude-Abo) nach
  scripts/redaktion.md die Datei eingang/ausgabe.json und pusht sie.

  python scripts/build_newsletter.py fertigstellen
      eingang/ausgabe.json prüfen (muss zum "stand" der Meldungen passen), Quellen-Nummern
      in Links umwandeln und nach docs/data/ schreiben. Ohne passende Ausgabe entsteht
      eine Schlagzeilen-Ausgabe.
"""
from __future__ import annotations

import html
import json
import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
FEEDS_FILE = ROOT / "scripts" / "feeds.json"
EINGANG = ROOT / "eingang"
DATA_DIR = ROOT / "docs" / "data"
ARCHIVE_DIR = DATA_DIR / "archive"
BERLIN = ZoneInfo("Europe/Berlin")

STUNDEN = int(os.environ.get("STUNDEN", "36"))
ARCHIV_TAGE = 90
MAX_PRO_FEED = 15
MAX_MELDUNGEN = 100
USER_AGENT = "Mozilla/5.0 (compatible; AI-News-Newsletter/1.0)"

# Groß-/Kleinschreibung zählt hier, damit "Ski" oder "Kai" nicht als KI durchgehen.
KI_STRENG = re.compile(r"\b(KI|AI|A\.I\.|LLMs?|GenAI)\b|\bKI-|-KI\b")
KI_LOCKER = re.compile(
    r"künstliche[nmrs]? intelligenz|artificial intelligence|machine learning|maschinelle[sn]? lernen"
    r"|deep learning|sprachmodell|language model|chatgpt|openai|anthropic|\bclaude\b|gemini"
    r"|mistral ai|aleph alpha|deepl|copilot|chatbot|generative|neuronale|ai act|ki-verordnung"
    r"|deepmind|llama|nvidia|agentic|ki-agent",
    re.IGNORECASE,
)

WOCHENTAGE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
KATEGORIEN = ["Politik & Regulierung", "Wirtschaft & Startups", "Forschung",
              "Produkte & Modelle", "Gesellschaft", "Sicherheit"]


# --------------------------------------------------------------------------- Feeds

def _lokal(tag: str) -> str:
    """'{namespace}title' -> 'title'"""
    return tag.rsplit("}", 1)[-1].lower()


def _kind(el: ET.Element, *namen: str) -> ET.Element | None:
    for c in el:
        if _lokal(c.tag) in namen:
            return c
    return None


def _text(el: ET.Element | None) -> str:
    if el is None:
        return ""
    return "".join(el.itertext()).strip()


def bereinigen(text: str, maxlen: int = 500) -> str:
    text = html.unescape(re.sub(r"<[^>]+>", " ", text or ""))
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= maxlen else text[: maxlen - 1].rsplit(" ", 1)[0] + "…"


def _datum(text: str) -> datetime | None:
    if not text:
        return None
    try:
        d = parsedate_to_datetime(text)
    except (TypeError, ValueError):
        try:
            d = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def parse_feed(xml_bytes: bytes, quelle: str) -> list[dict]:
    """Versteht RSS 2.0, RSS 1.0 (RDF) und Atom."""
    root = ET.fromstring(xml_bytes)
    eintraege = [e for e in root.iter() if _lokal(e.tag) in ("item", "entry")]
    out = []
    for e in eintraege:
        titel = bereinigen(_text(_kind(e, "title")), 300)
        link_el = _kind(e, "link")
        link = ""
        if link_el is not None:
            link = (link_el.get("href") or _text(link_el)).strip()
        for c in e:  # Atom: rel="alternate" bevorzugen
            if _lokal(c.tag) == "link" and c.get("rel", "alternate") == "alternate" and c.get("href"):
                link = c.get("href")
                break
        text = _text(_kind(e, "description", "summary", "encoded", "content"))
        datum = _datum(_text(_kind(e, "pubdate", "published", "updated", "date")))
        if titel and link:
            out.append({"titel": titel, "link": link, "text": bereinigen(text),
                        "datum": datum, "quelle": quelle})
    return out


def ist_ki(eintrag: dict) -> bool:
    s = f"{eintrag['titel']} {eintrag['text']}"
    return bool(KI_STRENG.search(s) or KI_LOCKER.search(s))


def abrufen(feed: dict) -> list[dict]:
    req = urllib.request.Request(feed["url"], headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=25) as r:
        daten = r.read()
    eintraege = parse_feed(daten, feed["name"])
    for e in eintraege:
        e["region"] = feed["region"]
    if not feed.get("nur_ki"):
        eintraege = [e for e in eintraege if ist_ki(e)]
    return eintraege


def _schluessel(titel: str) -> str:
    # Google News hängt " - Quelle" an; für den Dublettenvergleich abschneiden.
    titel = re.sub(r"\s+[-–|]\s+[^-–|]{2,40}$", "", titel)
    return re.sub(r"[^a-z0-9äöüß]+", "", titel.lower())[:80]


def sammeln(feeds: list[dict], jetzt: datetime) -> tuple[list[dict], dict]:
    grenze = jetzt - timedelta(hours=STUNDEN)
    status: dict[str, str] = {}

    def holen(feed):
        try:
            return feed, abrufen(feed), None
        except Exception as ex:  # ein kaputter Feed soll nie den ganzen Lauf stoppen
            return feed, [], f"{type(ex).__name__}: {ex}"

    alle: list[dict] = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        for feed, eintraege, fehler in pool.map(holen, feeds):
            frisch = [e for e in eintraege if e["datum"] is None or e["datum"] >= grenze]
            frisch.sort(key=lambda e: e["datum"] or jetzt, reverse=True)
            alle.extend(frisch[:MAX_PRO_FEED])
            status[feed["name"]] = fehler or f"{len(frisch)} Meldungen"
            print(f"  {feed['name']:<32} {status[feed['name']]}", file=sys.stderr)

    gesehen, eindeutig = set(), []
    for e in sorted(alle, key=lambda e: e["datum"] or jetzt, reverse=True):
        k = _schluessel(e["titel"])
        if k and k not in gesehen:
            gesehen.add(k)
            eindeutig.append(e)
    return eindeutig, status


# --------------------------------------------------------------------------- Aufbereitung

def pruefen(roh: object, anzahl: int) -> dict | None:
    """Prüft Claudes Ausgabe streng; bei Formfehlern None (dann greift die Schlagzeilen-Ausgabe)."""
    if not isinstance(roh, dict) or not isinstance(roh.get("lage"), str):
        return None
    aus = {"lage": roh["lage"].strip()}
    for region in ("deutschland", "eu", "welt"):
        liste = roh.get(region)
        if not isinstance(liste, list):
            return None
        sauber = []
        for s in liste:
            if not isinstance(s, dict) or not isinstance(s.get("titel"), str) or not s["titel"].strip():
                continue
            quellen = [i for i in s.get("quellen", []) if isinstance(i, int) and 0 <= i < anzahl]
            if not quellen:
                continue
            sauber.append({
                "titel": s["titel"].strip()[:200],
                "zusammenfassung": str(s.get("zusammenfassung", "")).strip()[:1200],
                "warum_wichtig": str(s.get("warum_wichtig", "")).strip()[:500],
                "kategorie": s.get("kategorie") if s.get("kategorie") in KATEGORIEN else "",
                "quellen": quellen,
            })
        aus[region] = sauber
    if not any(aus[r] for r in ("deutschland", "eu", "welt")):
        return None
    return aus


def ohne_claude(meldungen: list[dict], hinweis: str) -> dict:
    grenzen = {"de": 15, "eu": 10, "welt": 5}
    ziel = {"de": "deutschland", "eu": "eu", "welt": "welt"}
    aus = {"lage": hinweis, "deutschland": [], "eu": [], "welt": []}
    for i, m in enumerate(meldungen):
        liste = aus[ziel[m["region"]]]
        if len(liste) < grenzen[m["region"]]:
            liste.append({"titel": m["titel"], "zusammenfassung": m["text"], "warum_wichtig": "",
                          "kategorie": "", "quellen": [i]})
    return aus


def quellen_aufloesen(ausgabe: dict, meldungen: list[dict]) -> dict:
    for region in ("deutschland", "eu", "welt"):
        for s in ausgabe[region]:
            s["quellen"] = [{"name": meldungen[i]["quelle"], "url": meldungen[i]["link"]}
                            for i in s["quellen"] if isinstance(i, int) and 0 <= i < len(meldungen)]
        ausgabe[region] = [s for s in ausgabe[region] if s["quellen"]]
    return ausgabe


# --------------------------------------------------------------------------- Speichern

def speichern(ausgabe: dict) -> None:
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    datum = ausgabe["datum"]
    inhalt = json.dumps(ausgabe, ensure_ascii=False, indent=1)
    (DATA_DIR / "latest.json").write_text(inhalt, encoding="utf-8")
    (ARCHIVE_DIR / f"{datum}.json").write_text(inhalt, encoding="utf-8")

    grenze = (datetime.fromisoformat(datum) - timedelta(days=ARCHIV_TAGE)).date().isoformat()
    for f in ARCHIVE_DIR.glob("*.json"):
        if f.stem < grenze:
            f.unlink()
    tage = sorted((f.stem for f in ARCHIVE_DIR.glob("*.json")), reverse=True)
    (DATA_DIR / "index.json").write_text(json.dumps({"ausgaben": tage}), encoding="utf-8")


def sammeln_befehl() -> int:
    jetzt = datetime.now(timezone.utc)
    feeds = json.loads(FEEDS_FILE.read_text(encoding="utf-8"))["feeds"]
    print(f"Rufe {len(feeds)} Feeds ab …", file=sys.stderr)
    meldungen, status = sammeln(feeds, jetzt)
    meldungen = meldungen[:MAX_MELDUNGEN]
    print(f"{len(meldungen)} KI-Meldungen nach Filter und Dublettenprüfung", file=sys.stderr)

    EINGANG.mkdir(exist_ok=True)
    (EINGANG / "ausgabe.json").unlink(missing_ok=True)
    daten = {
        "stand": jetzt.isoformat(timespec="seconds"),
        "heute": f"{WOCHENTAGE[jetzt.astimezone(BERLIN).weekday()]}, {jetzt.astimezone(BERLIN):%d.%m.%Y}",
        "feeds": status,
        "meldungen": [{"id": i, "titel": m["titel"], "quelle": m["quelle"], "region": m["region"],
                       "text": m["text"], "link": m["link"]} for i, m in enumerate(meldungen)],
    }
    (EINGANG / "meldungen.json").write_text(json.dumps(daten, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


def fertigstellen_befehl() -> int:
    daten = json.loads((EINGANG / "meldungen.json").read_text(encoding="utf-8"))
    meldungen = daten["meldungen"]
    if not meldungen:
        print("Keine Meldungen gefunden – bestehende Ausgabe bleibt unverändert.", file=sys.stderr)
        return 0

    ausgabe, modus = None, "ki"
    datei = EINGANG / "ausgabe.json"
    if datei.exists():
        try:
            roh = json.loads(datei.read_text(encoding="utf-8"))
            if isinstance(roh, dict) and roh.get("stand") == daten.get("stand"):
                ausgabe = pruefen(roh, len(meldungen))
                if ausgabe is None:
                    print("eingang/ausgabe.json ist unvollständig – nutze Schlagzeilen.", file=sys.stderr)
            else:
                print("eingang/ausgabe.json gehört zu anderen Meldungen – nutze Schlagzeilen.", file=sys.stderr)
        except json.JSONDecodeError as ex:
            print(f"eingang/ausgabe.json ist kein gültiges JSON: {ex}", file=sys.stderr)
    else:
        print("Noch keine eingang/ausgabe.json von Claude – nutze Schlagzeilen.", file=sys.stderr)
    if ausgabe is None:
        modus = "einfach"
        ausgabe = ohne_claude(meldungen, "Guten Morgen! Hier sind schon mal die Schlagzeilen – "
                                         "die Zusammenfassung von Claude folgt in Kürze.")

    jetzt = datetime.now(timezone.utc).astimezone(BERLIN)
    ausgabe = quellen_aufloesen(ausgabe, meldungen)
    ausgabe.update({
        "datum": jetzt.date().isoformat(),
        "erstellt": jetzt.isoformat(timespec="minutes"),
        "modus": modus,
        "anzahl_meldungen": len(meldungen),
        "feeds": daten.get("feeds", {}),
    })
    speichern(ausgabe)
    print(f"Gespeichert: {ausgabe['datum']} ({modus}) – DE {len(ausgabe['deutschland'])}, "
          f"EU {len(ausgabe['eu'])}, Welt {len(ausgabe['welt'])}", file=sys.stderr)
    return 0


def zeigen_befehl() -> int:
    """Kompakte Übersicht für die Redaktion: eine Zeile pro Meldung, spart Tokens."""
    daten = json.loads((EINGANG / "meldungen.json").read_text(encoding="utf-8"))
    print(f"stand={daten['stand']} | heute={daten['heute']} | {len(daten['meldungen'])} Meldungen")
    for m in daten["meldungen"]:
        text = m["text"] if m["text"] and not m["titel"].startswith(m["text"][:40]) else ""
        print(f"[{m['id']}] {m['region']} | {m['quelle']} | {m['titel']}" + (f" | {text[:220]}" if text else ""))
    return 0


def pruefen_befehl() -> int:
    """Prüft eingang/ausgabe.json wie fertigstellen, ohne etwas zu schreiben."""
    m = json.loads((EINGANG / "meldungen.json").read_text(encoding="utf-8"))
    try:
        a = json.loads((EINGANG / "ausgabe.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as ex:
        print(f"FEHLER: {ex}")
        return 1
    if not isinstance(a, dict) or a.get("stand") != m["stand"]:
        print("FEHLER: 'stand' fehlt oder passt nicht zu eingang/meldungen.json")
        return 1
    geprueft = pruefen(a, len(m["meldungen"]))
    if geprueft is None:
        print("FEHLER: Format ungültig oder keine Geschichte mit gültigen Quellen")
        return 1
    verworfen = sum(len(a.get(r) or []) - len(geprueft[r]) for r in ("deutschland", "eu", "welt"))
    print(f"ok – DE {len(geprueft['deutschland'])}, EU {len(geprueft['eu'])}, Welt {len(geprueft['welt'])}"
          + (f" ({verworfen} Geschichten ohne gültige Quellen verworfen)" if verworfen else ""))
    return 0


if __name__ == "__main__":
    befehle = {"sammeln": sammeln_befehl, "fertigstellen": fertigstellen_befehl,
               "zeigen": zeigen_befehl, "pruefen": pruefen_befehl}
    if len(sys.argv) != 2 or sys.argv[1] not in befehle:
        sys.exit(f"Aufruf: {sys.argv[0]} sammeln|fertigstellen|zeigen|pruefen")
    sys.exit(befehle[sys.argv[1]]())
