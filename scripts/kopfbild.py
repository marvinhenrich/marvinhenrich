"""Erzeugt das Kopfbild der Profil-README in Hell und Dunkel (docs/kopf-hell.svg, docs/kopf-dunkel.svg).

Die Schrift ist Instrument Sans, dieselbe wie auf net-evolution.de. Sie steckt als Umrisslinien im SVG,
nicht als Schriftdatei: GitHub zeigt README-Bilder als <img>, und dort lädt kein Browser zuverlässig
eingebettete Schriften nach. Umrisse sehen überall gleich aus.

Grundsatz: Der Ruhezustand ist der fertige Zustand. Die Bewegung (ein Punkt läuft durch den Ablauf,
die Freigabe bestätigt) ist Zugabe. Läuft sie nicht, weil jemand Bewegung abbestellt hat oder ein
Vorschaubild entsteht, ist trotzdem alles da.

Aufruf: uv run --with fonttools --with brotli --with uharfbuzz python scripts/kopfbild.py
"""
import io
from pathlib import Path

import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont

WURZEL = Path(__file__).resolve().parent.parent
SCHRIFT = WURZEL / "scripts/schrift/instrument-sans-latin-wdth-normal.woff2"

_tt = TTFont(SCHRIFT)
_tt.flavor = None
_puffer = io.BytesIO()
_tt.save(_puffer)
GESICHT = hb.Face(_puffer.getvalue())
EINHEITEN = _tt["head"].unitsPerEm


GLYPHEN = {}  # (glyphe, gewicht, breite) -> (id, pfad); jede Form steht nur einmal im SVG


def satz(text, x, y, groesse, gewicht=400, breite=100, sperrung=0.0, wortabstand=0.0):
    """Setzt Text als Verweise auf Glyphenpfade. Liefert (svg, rechte Kante). sperrung, wortabstand in em."""
    font = hb.Font(GESICHT)
    font.set_variations({"wght": gewicht, "wdth": breite})
    puffer = hb.Buffer()
    puffer.add_str(text)
    puffer.guess_segment_properties()
    hb.shape(font, puffer, {"kern": True, "liga": True})
    s = groesse / EINHEITEN
    stift_x = 0.0
    teile = []
    for info, pos in zip(puffer.glyph_infos, puffer.glyph_positions):
        schluessel = (info.codepoint, gewicht, breite)
        if schluessel not in GLYPHEN:
            stift = SVGPathPen(None, ntos=lambda v: str(round(v)))  # ganze Schrifteinheiten reichen
            font.draw_glyph_with_pen(info.codepoint, stift)
            GLYPHEN[schluessel] = (f"g{len(GLYPHEN)}", stift.getCommands())
        gid, d = GLYPHEN[schluessel]
        if d:
            ox = x + (stift_x + pos.x_offset) * s
            teile.append(f'<use href="#{gid}" transform="translate({ox:.2f} {y:.2f}) scale({s:.5f} {-s:.5f})"/>')
        stift_x += pos.x_advance + sperrung * EINHEITEN
        if text[info.cluster] == " ":
            stift_x += wortabstand * EINHEITEN
    return "".join(teile), x + stift_x * s


FARBEN = {
    "hell": dict(flaeche="#F0F2EF", rand="#E1E4DF", tinte="#121416", text="#3D4348", leise="#5A6167",
                 akzent="#0F6E56", linie="#C7CCC5", knoten="#F0F2EF", haken="#FFFFFF"),
    "dunkel": dict(flaeche="#0E1315", rand="#202A2E", tinte="#F2F5F3", text="#C9D3CE", leise="#A9B7B1",
                   akzent="#6FD3AE", linie="#33424A", knoten="#0E1315", haken="#0E1315"),
}

STUFEN = [  # Ablauf: Titel, Unterzeile
    ("Neue Mail", "Anfrage, Rückfrage"),
    ("KI bereitet vor", "ordnet ein, schreibt den Entwurf"),
    ("Mensch gibt frei", "erst dann geht es raus"),
]

# Zwei Formate. GitHub zeigt die README etwa 880 px breit (Faktor 0,73 zum breiten Bild), am Handy
# etwa 330 px. Die schmale Fassung ist darum eine eigene Gestaltung, kein verkleinertes Breitbild.
# Zeilen: (Text, y, Größe, Gewicht, Breite, Sperrung, Wortabstand, Rolle)
FORMATE = {
    "breit": dict(
        B=1200, H=330, rand_x=56,
        zeilen=[
            ("KI IM BETRIEB", 67, 15, 600, 100, 0.06, 0, "akzent"),
            ("Marvin Henrich", 135, 72, 600, 92, -0.03, 0.07, "tinte"),
            ("Ich bringe KI in den Betrieb, vom Server bis zum Ablauf,", 187, 27, 500, 100, -0.01, 0, "text"),
            ("den ein Team jeden Tag nutzt.", 223, 27, 500, 100, -0.01, 0, "text"),
            ("Fachinformatiker für Systemintegration in Ausbildung. Inhaber von Net-Evolution.", 267, 18, 400, 100, 0, 0, "leise"),
        ],
        textgrenze=830,  # rechts davon steht der Ablauf (ausgenommen die letzte, leise Zeile)
        ablauf=dict(kx=870, y0=78, abstand=80, titel=21, unter=16, unter_dy=24, trenner=None),
    ),
    "schmal": dict(
        B=420, H=447, rand_x=24,
        zeilen=[
            ("KI IM BETRIEB", 37, 12.5, 600, 100, 0.06, 0, "akzent"),
            ("Marvin Henrich", 79, 40, 600, 92, -0.03, 0.07, "tinte"),
            ("Ich bringe KI in den Betrieb,", 113, 19, 500, 100, -0.01, 0, "text"),
            ("vom Server bis zum Ablauf,", 139, 19, 500, 100, -0.01, 0, "text"),
            ("den ein Team jeden Tag nutzt.", 165, 19, 500, 100, -0.01, 0, "text"),
            ("Fachinformatiker für Systemintegration", 197, 15, 400, 100, 0, 0, "leise"),
            ("in Ausbildung. Inhaber von Net-Evolution.", 217, 15, 400, 100, 0, 0, "leise"),
        ],
        textgrenze=420 - 24,
        ablauf=dict(kx=32, y0=275, abstand=60, titel=17, unter=14, unter_dy=20, trenner=241),
    ),
}


def kopfbild(thema, format_name):
    f, F = FARBEN[thema], FORMATE[format_name]
    B, H, a = F["B"], F["H"], F["ablauf"]
    text = []
    for i, (zeile, y, groesse, gewicht, breite, sperrung, wort, rolle) in enumerate(F["zeilen"]):
        x = F["rand_x"] - (groesse * 0.045 if groesse > 30 else 0)  # große Schrift optisch an die Kante
        pfad, ende = satz(zeile, x, y, groesse, gewicht=gewicht, breite=breite, sperrung=sperrung, wortabstand=wort)
        letzte = i == len(F["zeilen"]) - 1 and format_name == "breit"
        grenze = B - F["rand_x"] if letzte else F["textgrenze"]
        assert ende <= grenze, f"{format_name}: „{zeile}“ ragt hinaus ({ende:.0f} > {grenze})"
        text.append(f'<g fill="{f[rolle]}">{pfad}</g>')

    KX, KY0, KABSTAND = a["kx"], a["y0"], a["abstand"]
    ablauf = []
    if a["trenner"]:
        ablauf.append(f'<line x1="{F["rand_x"]}" y1="{a["trenner"]}" x2="{B - F["rand_x"]}" y2="{a["trenner"]}" '
                      f'stroke="{f["rand"]}" stroke-width="1"/>')
    ablauf.append(f'<line x1="{KX}" y1="{KY0 - 5}" x2="{KX}" y2="{KY0 + 2 * KABSTAND - 5}" stroke="{f["linie"]}" stroke-width="2"/>')
    for i, (titel, unter) in enumerate(STUFEN):
        y = KY0 + i * KABSTAND
        t, te = satz(titel, KX + 26, y + 1, a["titel"], gewicht=600, sperrung=-0.005)
        u, ue = satz(unter, KX + 26, y + a["unter_dy"], a["unter"], gewicht=400)
        assert max(te, ue) <= B - 24, f"{format_name}: Ablauf „{unter}“ ragt hinaus ({max(te, ue):.0f})"
        ablauf.append(f'<g fill="{f["tinte"]}">{t}</g><g fill="{f["leise"]}">{u}</g>')
        if i < 2:
            ablauf.append(f'<circle cx="{KX}" cy="{y - 5}" r="7" fill="{f["knoten"]}" stroke="{f["akzent"]}" stroke-width="2"/>')
        else:
            freigabe = (
                f'<g class="freigabe"><circle cx="{KX}" cy="{y - 5}" r="12" fill="{f["akzent"]}"/>'
                f'<path d="M{KX - 5.5} {y - 5} l3.8 3.8 l7.2 -7.6" fill="none" stroke="{f["haken"]}" '
                f'stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></g>'
            )
    # Der Punkt läuft unter dem Freigabe-Knoten durch und verschwindet im Haken; deshalb wird der Knoten danach gezeichnet.
    ablauf.append(f'<circle class="punkt" cx="{KX}" cy="{KY0 - 5}" r="4.5" fill="{f["akzent"]}"/>')
    ablauf.append(freigabe)

    stil = f"""
    /* Ohne Bewegung ist der Punkt aus und alles andere steht fertig da. Drei Durchläufe, danach Ruhe. */
    .punkt {{ opacity: 0; }}
    @keyframes fahrt {{
      0%   {{ opacity: 0; transform: translateY(0); }}
      6%   {{ opacity: 1; transform: translateY(0); }}
      28%  {{ opacity: 1; transform: translateY({KABSTAND}px); }}
      46%  {{ opacity: 1; transform: translateY({KABSTAND}px); }}
      66%  {{ opacity: 1; transform: translateY({2 * KABSTAND}px); }}
      72%  {{ opacity: 0; transform: translateY({2 * KABSTAND}px); }}
      100% {{ opacity: 0; transform: translateY({2 * KABSTAND}px); }}
    }}
    .punkt {{ animation: fahrt 6.4s cubic-bezier(.45,0,.25,1) 0.6s 3 both; }}
    @media (prefers-reduced-motion: reduce) {{
      .punkt {{ animation: none; }}
    }}
    """
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {B} {H}" width="{B}" height="{H}" role="img" '
        f'aria-labelledby="t d">'
        f'<title id="t">Marvin Henrich</title>'
        f'<desc id="d">Ich bringe KI in den Betrieb, vom Server bis zum Ablauf, den ein Team jeden Tag '
        f'nutzt. Fachinformatiker für Systemintegration in Ausbildung, Inhaber von Net-Evolution. Ablauf: neue Mail, KI bereitet vor, '
        f'Mensch gibt frei.</desc>'
        f'<style>{stil}</style>'
        f'<rect x="0.5" y="0.5" width="{B - 1}" height="{H - 1}" rx="12" fill="{f["flaeche"]}" stroke="{f["rand"]}"/>'
        + "<defs>" + "".join(f'<path id="{i}" d="{d}"/>' for i, d in GLYPHEN.values() if d) + "</defs>"
        + "".join(text) + "".join(ablauf) + "</svg>\n"
    )


if __name__ == "__main__":
    for format_name in FORMATE:
        for thema in FARBEN:
            GLYPHEN.clear()
            name = f"kopf-{thema}" if format_name == "breit" else f"kopf-{format_name}-{thema}"
            ziel = WURZEL / f"docs/{name}.svg"
            ziel.write_text(kopfbild(thema, format_name), encoding="utf-8")
            print(f"{ziel.relative_to(WURZEL)}  {ziel.stat().st_size / 1024:.1f} KB")
