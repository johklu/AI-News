import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import build_newsletter as b  # noqa: E402

FIX = Path(__file__).parent / "fixtures"


class ParseTests(unittest.TestCase):
    def test_rss(self):
        e = b.parse_feed((FIX / "rss.xml").read_bytes(), "Test")
        self.assertEqual(len(e), 3)
        self.assertEqual(e[0]["link"], "https://example.org/1")
        self.assertNotIn("<", e[0]["text"])
        self.assertIn("künstliche Intelligenz", e[0]["text"])
        self.assertEqual(e[0]["datum"], datetime(2026, 11, 4, 6, 0, tzinfo=timezone.utc))

    def test_atom_bevorzugt_alternate_link(self):
        e = b.parse_feed((FIX / "atom.xml").read_bytes(), "Test")
        self.assertEqual(e[0]["link"], "https://example.eu/a")
        self.assertEqual(e[0]["datum"].year, 2026)


class FilterTests(unittest.TestCase):
    def t(self, titel, text=""):
        return b.ist_ki({"titel": titel, "text": text})

    def test_erkennt_ki(self):
        self.assertTrue(self.t("Neue KI-Verordnung tritt in Kraft"))
        self.assertTrue(self.t("OpenAI stellt Modell vor"))
        self.assertTrue(self.t("Was der AI Act für Startups bedeutet"))
        self.assertTrue(self.t("Firmen setzen auf KI"))

    def test_keine_falschen_treffer(self):
        self.assertFalse(self.t("Ski-Saison beginnt früher"))
        self.assertFalse(self.t("Kai gewinnt Kochwettbewerb"))
        self.assertFalse(self.t("Bahn erhöht die Preise", "Mehr Kosten für Pendler"))

    def test_dubletten_schluessel(self):
        self.assertEqual(b._schluessel("Mistral sammelt Milliarden ein - heise online"),
                         b._schluessel("Mistral sammelt Milliarden ein – Handelsblatt"))


class AufbereitungTests(unittest.TestCase):
    def test_ohne_claude_und_quellen(self):
        m = [{"titel": "A", "text": "x", "quelle": "Q1", "link": "https://a", "region": "de"},
             {"titel": "B", "text": "y", "quelle": "Q2", "link": "https://b", "region": "welt"}]
        aus = b.quellen_aufloesen(b.ohne_claude(m, "Hinweis"), m)
        self.assertEqual(aus["deutschland"][0]["quellen"], [{"name": "Q1", "url": "https://a"}])
        self.assertEqual(len(aus["welt"]), 1)
        self.assertEqual(aus["eu"], [])

    def test_ungueltige_quellennummern_werden_verworfen(self):
        m = [{"titel": "A", "text": "x", "quelle": "Q1", "link": "https://a", "region": "de"}]
        aus = {"lage": "", "deutschland": [{"titel": "T", "zusammenfassung": "", "warum_wichtig": "",
                                            "kategorie": "Forschung", "quellen": [7]}], "eu": [], "welt": []}
        self.assertEqual(b.quellen_aufloesen(aus, m)["deutschland"], [])


if __name__ == "__main__":
    unittest.main()
