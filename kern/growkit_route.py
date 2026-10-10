"""Wat verlaat je machine? (advies 6)

Elke opdracht hoort vóór het draaien te laten zien waar gegevens heen gaan:
lokaal, via je eigen VPS, of naar een clouddienst. Een profiel mag dat zelf
verklaren (`gegevensroute`); deze module leidt de route ook af uit de commando's.
Wijken die twee van elkaar af, dan melden we dat — kiezen doen we niet stil.
"""
SOORTEN = ("lokaal", "eigen_vps", "cloud")

# Commando's die de machine uitgaan. Eerst de zwaarste: cloud wint van eigen VPS.
_CLOUD = ("curl ", "wget ", "http://", "https://")
_EIGEN_VPS = ("ssh ", "scp ", "rsync ")

UITLEG = {
    "lokaal": "Alles gebeurt op deze machine; er verlaat niets je computer.",
    "eigen_vps": "Er gaat iets naar je eigen server (GROWKIT_HOST); niets naar buiten.",
    "cloud": "Er gaat inhoud naar een clouddienst buiten je eigen systemen.",
}


def _teksten(profiel: dict) -> list[tuple[str, str]]:
    """Alle uitvoerbare commando's uit een profiel, met hun stap-id."""
    regels = []
    for stap in profiel.get("stappen", []):
        if stap.get("commando"):
            regels.append((str(stap.get("id", "?")), str(stap["commando"])))
        alternatief = (stap.get("bij_falen") or {}).get("alternatief_commando")
        if alternatief:
            regels.append((f"{stap.get('id', '?')} (alternatief)", str(alternatief)))
    return regels


def afgeleid(profiel: dict) -> str:
    """De route zoals de commando's die verraden (zonder verklaring)."""
    teksten = [tekst for _, tekst in _teksten(profiel)]
    if any(signaal in tekst for tekst in teksten for signaal in _CLOUD):
        return "cloud"
    if any(signaal in tekst for tekst in teksten for signaal in _EIGEN_VPS):
        return "eigen_vps"
    return "lokaal"


def verzendt(profiel: dict) -> list[str]:
    """De regels die de machine zouden verlaten (leeg = niets)."""
    return [f"{stap_id}: {tekst}" for stap_id, tekst in _teksten(profiel)
            if any(signaal in tekst for signaal in _CLOUD + _EIGEN_VPS)]


def verklaring(profiel: dict) -> dict | None:
    """De route die het profiel zelf opgeeft (mag ontbreken)."""
    blok = profiel.get("gegevensroute")
    if isinstance(blok, dict) and blok.get("soort") in SOORTEN:
        return blok
    return None


def route(profiel: dict) -> dict:
    """De route zoals de app hem toont.

    De verklaring van het profiel wint (een mens heeft die geschreven), maar de
    afgeleide route staat er altijd naast. Is de verklaring lichter dan wat de
    commando's doen, dan volgen we de zwaarste en zeggen we dat luid.
    """
    afgeleide_soort = afgeleid(profiel)
    blok = verklaring(profiel)
    if blok is None:
        return {"soort": afgeleide_soort, "bron": "afgeleid",
                "verzendt": verzendt(profiel), "uitleg": UITLEG[afgeleide_soort],
                "waarschuwing": None}
    verklaarde_soort = blok["soort"]
    zwaarste = verklaarde_soort
    waarschuwing = None
    if SOORTEN.index(afgeleide_soort) > SOORTEN.index(verklaarde_soort):
        zwaarste = afgeleide_soort
        waarschuwing = (f"Het profiel zegt '{verklaarde_soort}', maar een commando gaat "
                        f"verder dan dat ({afgeleide_soort}). Behandeld als '{zwaarste}'.")
    return {"soort": zwaarste, "bron": "verklaard",
            "verzendt": verzendt(profiel),
            "uitleg": blok.get("uitleg") or UITLEG[zwaarste],
            "waarschuwing": waarschuwing}


def heeft_toestemming_nodig(profiel: dict) -> bool:
    """Alleen cloud vraagt om jouw expliciete toestemming."""
    return route(profiel)["soort"] == "cloud"
