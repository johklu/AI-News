"use strict";

const ABSCHNITTE = [
  { id: "deutschland", titel: "Deutschland" },
  { id: "eu", titel: "Europäische Union" },
  { id: "welt", titel: "Weltweit", klein: true },
];

const $ = (sel) => document.querySelector(sel);
const el = (tag, attrs = {}, ...kinder) => {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") e.className = v;
    else e.setAttribute(k, v);
  }
  for (const k of kinder) if (k != null) e.append(k);
  return e;
};
const sichereUrl = (u) => (/^https?:\/\//i.test(u || "") ? u : null);

function datumLang(iso) {
  const d = new Date(iso + "T12:00:00");
  return d.toLocaleDateString("de-DE", { weekday: "long", day: "numeric", month: "long" });
}
function datumKurz(iso) {
  const d = new Date(iso + "T12:00:00");
  return d.toLocaleDateString("de-DE", { weekday: "short", day: "2-digit", month: "2-digit", year: "numeric" });
}

async function laden(pfad) {
  const r = await fetch(pfad, { cache: "no-cache" });
  if (!r.ok) throw new Error(r.status);
  return r.json();
}

function karte(s) {
  const quellen = el("div", { class: "quellen" });
  for (const q of s.quellen || []) {
    const url = sichereUrl(q.url);
    if (url) quellen.append(el("a", { href: url, target: "_blank", rel: "noopener" }, q.name));
  }
  return el("article", { class: "karte" },
    s.kategorie ? el("span", { class: "kategorie" }, s.kategorie) : null,
    el("h3", {}, s.titel),
    s.zusammenfassung ? el("p", {}, s.zusammenfassung) : null,
    s.warum_wichtig ? el("p", { class: "wichtig" }, el("b", {}, "Warum wichtig: "), s.warum_wichtig) : null,
    quellen,
  );
}

function zeigen(a, istArchiv) {
  $("#datum").textContent = datumLang(a.datum);
  document.title = `AI-News · ${datumKurz(a.datum)}`;
  $("#hinweis-archiv").hidden = !istArchiv;
  $("#leer").hidden = true;

  $("#lage").hidden = !a.lage;
  $("#lage-text").textContent = a.lage || "";

  const ziel = $("#abschnitte");
  ziel.replaceChildren();
  for (const ab of ABSCHNITTE) {
    const storys = a[ab.id] || [];
    document.querySelector(`[data-zahl="${ab.id}"]`).textContent = storys.length || "";
    const sek = el("section", { class: `abschnitt ${ab.id}`, id: ab.id },
      el("div", { class: "abschnitt-kopf" },
        el("h2", {}, ab.titel),
        el("small", {}, storys.length === 1 ? "1 Thema" : `${storys.length} Themen`)));
    if (storys.length) storys.forEach((s) => sek.append(karte(s)));
    else sek.append(el("p", { class: "leer-abschnitt" }, "Heute nichts Nennenswertes."));
    ziel.append(sek);
  }

  const erstellt = a.erstellt ? new Date(a.erstellt) : null;
  $("#fuss").replaceChildren(
    el("p", {}, erstellt
      ? `Stand: ${erstellt.toLocaleString("de-DE", { dateStyle: "medium", timeStyle: "short" })} Uhr`
      : ""),
    el("p", {}, `${a.anzahl_meldungen ?? "?"} Meldungen ausgewertet` +
      (a.modus === "ki" ? " · zusammengefasst von Claude" : " · nur Schlagzeilen")),
  );
  beobachteAbschnitte();
}

function leer(text) {
  $("#abschnitte").replaceChildren();
  $("#lage").hidden = true;
  $("#fuss").replaceChildren();
  $("#datum").textContent = "AI-News";
  const box = $("#leer");
  box.hidden = false;
  box.replaceChildren(el("h2", {}, "Noch keine Ausgabe"), el("p", {}, text));
}

let aktuellesDatum = null;

async function heute() {
  const knopf = $("#btn-neu");
  knopf.classList.add("dreht");
  try {
    const a = await laden("data/latest.json");
    aktuellesDatum = a.datum;
    zeigen(a, false);
  } catch {
    leer("Die erste Ausgabe wird beim nächsten geplanten Lauf erstellt. Schau morgen früh wieder vorbei.");
  } finally {
    knopf.classList.remove("dreht");
  }
}

async function archivOeffnen() {
  const liste = $("#archiv-liste");
  liste.replaceChildren(el("li", {}, el("button", { disabled: "" }, "Lädt …")));
  $("#archiv").showModal();
  try {
    const { ausgaben } = await laden("data/index.json");
    liste.replaceChildren(...ausgaben.map((tag) => {
      const b = el("button", { class: tag === aktuellesDatum ? "aktiv" : "" }, datumKurz(tag));
      b.addEventListener("click", async () => {
        $("#archiv").close();
        try {
          const a = await laden(`data/archive/${tag}.json`);
          zeigen(a, tag !== aktuellesDatum);
          scrollTo({ top: 0 });
        } catch { leer("Diese Ausgabe ist offline nicht verfügbar."); }
      });
      return el("li", {}, b);
    }));
  } catch {
    liste.replaceChildren(el("li", {}, el("button", { disabled: "" }, "Archiv nicht erreichbar")));
  }
}

// Markiert beim Scrollen den passenden Reiter.
let beobachter;
function beobachteAbschnitte() {
  beobachter?.disconnect();
  const links = [...document.querySelectorAll(".reiter a")];
  beobachter = new IntersectionObserver((eintraege) => {
    for (const e of eintraege) {
      if (e.isIntersecting) links.forEach((l) => l.classList.toggle("aktiv", l.hash === `#${e.target.id}`));
    }
  }, { rootMargin: "-140px 0px -60% 0px" });
  document.querySelectorAll(".abschnitt").forEach((s) => beobachter.observe(s));
}

$("#btn-neu").addEventListener("click", heute);
$("#btn-heute").addEventListener("click", () => { heute(); scrollTo({ top: 0 }); });
$("#btn-archiv").addEventListener("click", archivOeffnen);
$("#archiv-zu").addEventListener("click", () => $("#archiv").close());
$("#archiv").addEventListener("click", (e) => { if (e.target.id === "archiv") e.target.close(); });

// Beim Zurückkehren in die App nach längerer Pause neu laden.
let verstecktSeit = 0;
document.addEventListener("visibilitychange", () => {
  if (document.hidden) verstecktSeit = Date.now();
  else if (verstecktSeit && Date.now() - verstecktSeit > 30 * 60 * 1000) heute();
});

if ("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js").catch(() => {});
heute();
