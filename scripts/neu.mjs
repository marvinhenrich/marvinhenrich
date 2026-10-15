// Übernimmt die neuesten Ratgeber- und Branchenseiten von net-evolution.de in die README
// (Abschnitt zwischen NEU:START und NEU:ENDE). Quelle ist die Sitemap der Website, das
// Datum ist ihr lastmod. Ohne Abhängigkeiten, läuft mit Node 20+.
import { readFile, writeFile } from "node:fs/promises";

const SITE = "https://net-evolution.de";
const ANZAHL = 3;

const holen = async (url) => {
  const r = await fetch(url, { headers: { "user-agent": "github.com/marvinhenrich Profil-Aktualisierung" } });
  if (!r.ok) throw new Error(`${url}: HTTP ${r.status}`);
  return r.text();
};
const entities = (s) => s.replace(/&amp;/g, "&").replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&nbsp;|&#160;/g, " ");

const xml = await holen(`${SITE}/sitemap.xml`);
const seiten = [...xml.matchAll(/<loc>([^<]+)<\/loc>(?:<lastmod>([^<]+)<\/lastmod>)?/g)]
  .map(([, loc, lastmod = ""]) => ({ loc, lastmod }))
  .filter((s) => /\/(wissen|branchen)\/[^/]+$/.test(s.loc))
  .sort((a, b) => b.lastmod.localeCompare(a.lastmod))
  .slice(0, ANZAHL);

const zeilen = [];
for (const s of seiten) {
  const html = await holen(s.loc);
  const titel = entities(html.match(/<title>([^<]+)<\/title>/)?.[1] ?? s.loc).replace(/\s*\|\s*Net-Evolution\s*$/, "").trim();
  const datum = s.lastmod
    ? new Date(s.lastmod).toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit", year: "numeric", timeZone: "Europe/Berlin" })
    : "";
  zeilen.push(`- [${titel}](${s.loc})${datum ? ` · ${datum}` : ""}`);
}
if (!zeilen.length) throw new Error("Keine Ratgeber oder Branchenseiten in der Sitemap gefunden, README bleibt unverändert.");

const readme = await readFile("README.md", "utf8");
if (!readme.includes("<!-- NEU:START -->")) throw new Error("Markierung NEU:START fehlt in der README.");
const neu = readme.replace(/<!-- NEU:START -->[\s\S]*?<!-- NEU:ENDE -->/, `<!-- NEU:START -->\n${zeilen.join("\n")}\n<!-- NEU:ENDE -->`);
if (neu === readme) console.log("Unverändert.");
else { await writeFile("README.md", neu); console.log(`README aktualisiert:\n${zeilen.join("\n")}`); }
