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
    """Eén voorstellingsbestand naar dict. geldig=False bij >3 opties of geen aanbeveling."""
    titel = ""
    opties: list[str] = []
    aanbeveling = ""
    for regel in tekst.splitlines():
        s = regel.strip()
        if s.startswith("# ") and not titel:
            titel = s[2:].strip()
        elif re.match(r"^(Optie|optie)\s+[A-Za-z0-9]+:", s):
            opties.append(s)
        elif re.match(r"^(Aanbeveling|aanbeveling):", s):
            aanbeveling = s.split(":", 1)[1].strip()
    geldig = len(opties) <= MAX_OPTIES and bool(aanbeveling)
    return {
        "titel": titel or bron,
        "opties": opties,
        "aanbeveling": aanbeveling,
        "geldig": geldig,
        "bron": bron,
    }


def render(index_tekst: str, voorstellen: list[dict], bevestigd: list[str]) -> str:
    """De besluitenzaal-kamer: wacht-op-baas → voorstellen → register."""
    wacht = onbevestigd_uit_index(index_tekst)

    wacht_html = "".join(
        f'<div class="wacht-item">{_html.escape(s)}</div>' for s in wacht
    ) or "<p><i>niets wacht op de Baas</i></p>"

    voor_html = ""
    for v in voorstellen:
        cls = "voor" if v["geldig"] else "voor voor-ongeldig"
        opts = "".join(f"<li>{_html.escape(o)}</li>" for o in v["opties"])
        adv = _html.escape(v["aanbeveling"]) or "<i>geen aanbeveling — ongeldig voorstel</i>"
        voor_html += (
            f'<div class="{cls}"><h3>{_html.escape(v["titel"])}</h3>'
            f"<ul>{opts}</ul><p><strong>Aanbeveling:</strong> {adv}</p></div>"
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
