"""growkit_besluitenzaal — Slice: besluitenzaal-kamer (optie C, KairOS 9 sept).

Rendert de 'wacht op de Baas'-kamer uit register + voorstellen-wachtrij.
Data blijft bij de aanroeper (privé); de kern is puur tekst → HTML, offline testbaar.

Bronnen:
- besluiten-index.md: ONBEVESTIGD-regels staan onder de kop
  'ONBEVESTIGD (...)' en beginnen met [BSL-xxx] (ingesprongen toegestaan).
- voorstellen: elk item {titel, opties[], aanbeveling, geldig, bron}.
  HARD: max 3 opties en een verplichte aanbeveling — anders ongeldig.
- bevestigd: lijst register-regels voor het 'loopt automatisch'-blok.

Huisstijl: papier #F4F1E9, inkt #19202C, oranje #F2673F (wacht-accent),
lime #D9F65C (register-accent). Kamervolgorde: wacht → voorstellen → register.
"""
import html as _html
import re

MAX_OPTIES = 3

_ONB_KOP = re.compile(r"^ONBEVESTIGD", re.I)
_BSL = re.compile(r"^\s*(\[BSL-\d+\].+)$")


def onbevestigd_uit_index(tekst: str) -> list[str]:
    """Regels [BSL-...] onder de ONBEVESTIGD-kop; de rest niet."""
    wacht: list[str] = []
    in_onb = False
    for regel in tekst.splitlines():
        s = regel.strip()
        if _ONB_KOP.match(s) and not s.startswith("[BSL-"):
            in_onb = True
            continue
        if s.startswith("[BSL-") or _BSL.match(regel):
            if in_onb:
                wacht.append(_BSL.match(regel).group(1).strip())
            continue
        if s and not s.startswith(("#", "-", " ", "<!--")) and not _ONB_KOP.match(s):
            in_onb = False
    return wacht


def parseer_voorstel(tekst: str, bron: str) -> dict:
    """Eén voorstellingsbestand naar dict. geldig=False bij >3 opties of geen aanbeveling.

    Vijf tegenpositie-velden (BSL-040 / Claude's besluit 1):
    keuze (max 3 opties) + aanbeveling (bestaand), plus vervaldatum,
    verstek en omkeerbaar (nieuw).
    """
    titel = ""
    opties: list[str] = []
    aanbeveling = ""
    vervaldatum = ""
    verstek = ""
    omkeerbaar_raw = ""
    for regel in tekst.splitlines():
        s = regel.strip()
        if s.startswith("# ") and not titel:
            titel = s[2:].strip()
        elif re.match(r"^(Optie|optie)\s+[A-Za-z0-9]+:", s):
            opties.append(s)
        elif re.match(r"^(Aanbeveling|aanbeveling):", s):
            aanbeveling = s.split(":", 1)[1].strip()
        elif re.match(r"^(Vervaldatum|vervaldatum):", s):
            vervaldatum = s.split(":", 1)[1].strip()
        elif re.match(r"^(Verstek|verstek):", s):
            verstek = s.split(":", 1)[1].strip()
        elif re.match(r"^(Omkeerbaar|omkeerbaar):", s):
            omkeerbaar_raw = s.split(":", 1)[1].strip()
    geldig = len(opties) <= MAX_OPTIES and bool(aanbeveling)
    omkeerbaar_ja = bool(omkeerbaar_raw) and bool(
        re.match(r"^(ja|yes|true|1)\b", omkeerbaar_raw.strip(), re.I)
    )
    omkeerbaar_hoe = ""
    omkeerbaar_ja_match = re.match(r"^ja\s*[—–-]\s*(.+)$", omkeerbaar_raw.strip(), re.I) if omkeerbaar_ja else None
    if omkeerbaar_ja_match:
        omkeerbaar_hoe = omkeerbaar_ja_match.group(1).strip()
    elif omkeerbaar_ja:
        omkeerbaar_hoe = omkeerbaar_raw.strip()
    return {
        "titel": titel or bron,
        "opties": opties,
        "aanbeveling": aanbeveling,
        "geldig": geldig,
        "bron": bron,
        "vervaldatum": vervaldatum,
        "verstek": verstek,
        "omkeerbaar": omkeerbaar_ja,
        "omkeerbaar_hoe": omkeerbaar_hoe,
    }


_DATUM = re.compile(r"^(\d{2})-(\d{2})-(\d{4})$")


def _naar_iso(datum: str) -> str:
    """DD-MM-JJJJ → ISO JJJJ-MM-DD; anders onveranderd."""
    m = _DATUM.match(datum.strip())
    if not m:
        return datum.strip()
    d, mnd, jr = m.groups()
    return f"{jr}-{mnd}-{d}"


def is_verlopen(voorstel: dict, vandaag: str) -> bool:
    """True als het voorstel een vervaldatum heeft die vóór vandaag ligt (DD-MM-JJJJ)."""
    verval = voorstel.get("vervaldatum", "")
    if not verval:
        return False
    try:
        return _naar_iso(verval) < _naar_iso(vandaag)
    except Exception:
        return False


_VELD_SUFFIX = re.compile(
    r"\|\s*vervaldatum:\s*(?P<vervaldatum>[^|]+)"
    r"(?:\|\s*verstek:\s*(?P<verstek>[^|]+))?"
    r"(?:\|\s*omkeerbaar:\s*(?P<omkeerbaar>[^|]+))?",
    re.I,
)


def ontleed_registerregel(regel: str) -> dict:
    """Registerregel met optionele vijf-veld-suffix → dict met de nieuwe velden."""
    m = _VELD_SUFFIX.search(regel)
    velden = {"vervaldatum": "", "verstek": "", "omkeerbaar": False, "omkeerbaar_hoe": ""}
    if not m:
        return velden
    velden["vervaldatum"] = m.group("vervaldatum").strip()
    if m.group("verstek"):
        velden["verstek"] = m.group("verstek").strip()
    omk = (m.group("omkeerbaar") or "").strip()
    if re.match(r"^(ja|yes|true|1)\b", omk, re.I):
        velden["omkeerbaar"] = True
        hoe = re.match(r"^(ja|yes|true|1)\s*[—–-]\s*(.+)$", omk, re.I)
        velden["omkeerbaar_hoe"] = hoe.group(2).strip() if hoe else omk
    return velden


def render(index_tekst: str, voorstellen: list[dict], bevestigd: list[str], vandaag: str = "") -> str:
    """De besluitenzaal-kamer: wacht-op-baas → voorstellen → register.

    Vijf velden per voorstel in de UI (BSL-040): opties (max 3), aanbeveling,
    vervaldatum, verstek, omkeerbaar. Een voorstel waarvan de vervaldatum vóór
    `vandaag` ligt rendert met label 'VERVALLEN' + verstek-uitkomst.
    """
    wacht = onbevestigd_uit_index(index_tekst)

    wacht_html = "".join(
        f'<div class="wacht-item">{_html.escape(s)}</div>' for s in wacht
    ) or "<p><i>niets wacht op de Baas</i></p>"

    voor_html = ""
    for v in voorstellen:
        verlopen = bool(vandaag) and is_verlopen(v, vandaag)
        cls = "voor" if v["geldig"] and not verlopen else "voor voor-ongeldig"
        opts = "".join(f"<li>{_html.escape(o)}</li>" for o in v["opties"])
        adv = _html.escape(v["aanbeveling"]) or "<i>geen aanbeveling — ongeldig voorstel</i>"

        velden = []
        if v.get("vervaldatum"):
            velden.append(f'<span class="veld"><label>Vervaldatum</label> {_html.escape(v["vervaldatum"])}</span>')
        if v.get("verstek"):
            velden.append(f'<span class="veld"><label>Verstek</label> {_html.escape(v["verstek"])}</span>')
        if v.get("omkeerbaar"):
            hoe = _html.escape(v.get("omkeerbaar_hoe", ""))
            velden.append(f'<span class="veld"><label>Omkeerbaar</label> ja' + (f" — {hoe}" if hoe else "") + "</span>")
        elif v.get("vervaldatum") or v.get("verstek"):
            velden.append('<span class="veld"><label>Omkeerbaar</label> nee</span>')
        velden_html = " ".join(velden)

        kop = _html.escape(v["titel"])
        if verlopen:
            verstek_txt = v.get("verstek") or "geen verstek-afspraken vastgelegd"
            kop += ' <span class="vervallen-label">VERVALLEN</span>'
            velden_html += (
                f'<p class="verstek-uitkomst"><strong>Verstek treedt in:</strong> '
                f"{_html.escape(verstek_txt)}</p>"
            )

        voor_html += (
            f'<div class="{cls}"><h3>{kop}</h3>'
            f"<ul>{opts}</ul><p><strong>Aanbeveling:</strong> {adv}</p>"
            f"{velden_html}</div>"
        )
    if not voor_html:
        voor_html = "<p><i>geen open voorstellen</i></p>"

    reg_html = "".join(
        f'<div class="bsl-item">{_html.escape(s)}</div>' for s in bevestigd
    ) or "<p><i>—</i></p>"

    return f"""<!doctype html><html><head><meta charset="utf-8"><title>Besluitenzaal — Agent Family</title>
<style>
:root{{--papier:#F4F1E9;--inkt:#19202C;--oranje:#F2673F;--lime:#D9F65C}}
body{{font-family:'DM Sans',sans-serif;background:var(--papier);color:var(--inkt);max-width:1100px;margin:2em auto;padding:0 1em;line-height:1.55}}
h1,h2,h3{{font-family:'Space Grotesk',sans-serif}}h1{{color:var(--oranje)}}
.kamer-wacht{{border-left:4px solid var(--oranje);background:#fff;padding:1em;margin:1em 0}}
.wacht-item{{padding:.5em .8em;border-bottom:1px solid #eee}}
.voor{{border-left:4px solid var(--lime);background:#fff;padding:1em;margin:1em 0}}
.voor-ongeldig{{opacity:.6}}
.veld{{margin-right:1em;font-size:.92em}}
.veld label{{display:inline;font-size:.72em}}
.vervallen-label{{background:var(--oranje);color:#fff;font-size:.65em;padding:.15em .5em;border-radius:3px;vertical-align:middle;margin-left:.4em;letter-spacing:.06em}}
.verstek-uitkomst{{border-top:1px dashed var(--oranje);margin-top:.6em;padding-top:.5em}}
.kamer-register{{border-left:4px solid var(--lime);background:#fff;padding:1em;margin:1em 0}}
label{{font-family:'DM Mono',monospace;font-size:.8em;text-transform:uppercase;letter-spacing:.08em}}
</style></head><body>
<h1>Besluitenzaal</h1>
<section class="kamer-wacht"><label>Wacht op de Baas ({len(wacht)})</label>
{wacht_html}</section>
<section class="kamer-voor"><label>Voorstellen met opties</label>
{voor_html}</section>
<section class="kamer-register"><label>Loopt automatisch — register</label>
{reg_html}</section>
</body></html>"""
