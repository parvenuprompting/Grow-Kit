"""Projecteer bewijs zonder technische checks als inhoudelijke waarheid te presenteren."""


def bewijsrapport(profiel: dict, gebeurtenissen: list[dict]) -> dict:
    stappen = []
    for stap in profiel.get('stappen', []):
        regels = [e for e in gebeurtenissen if e.get('stap') == stap['id']]
        laatste = regels[-1] if regels else {}
        technisch = [e for e in regels if e.get('status') in ('geslaagd', 'gefaald')]
        reviews = [e for e in regels if e.get('review_oordeel')]
        mens = [e for e in regels if e.get('status') in ('geratificeerd', 'herziening_nodig')]
        is_mens = bool(stap.get('mens_nodig'))
        stappen.append({
            'id': stap['id'],
            'criterium': stap.get('verwacht') or stap.get('mens_nodig', {}).get('instructie') or 'Geen inhoudelijk criterium opgegeven',
            'controle': stap.get('bewijs', {}).get('type', 'mens_verificatie'),
            'status': laatste.get('status', 'nog_niet_uitgevoerd'),
            'technisch': 'niet_van_toepassing' if is_mens else ('geslaagd' if technisch and technisch[-1]['status'] == 'geslaagd' else 'niet_bewezen'),
            'inhoudelijk': reviews[-1]['review_oordeel'] if reviews else 'niet_beoordeeld',
            'mens': mens[-1]['status'] if mens else 'niet_goedgekeurd',
            'bewijs': technisch[-1].get('bewijs', '') if technisch else '',
        })
    technische_stappen = [s for s in stappen if s['technisch'] != 'niet_van_toepassing']
    return {'criteria': profiel.get('acceptatiecriteria', []), 'stappen': stappen,
            'technisch_gecontroleerd': bool(technische_stappen) and all(s['technisch'] == 'geslaagd' for s in technische_stappen),
            'inhoudelijk_beoordeeld': bool(stappen) and all(s['inhoudelijk'] == 'geslaagd' for s in stappen),
            'mens_goedgekeurd': bool(stappen) and all(s['mens'] == 'geratificeerd' for s in stappen),
            'uitleg': 'Technisch bewijs geldt uitsluitend voor de genoemde controle. Inhoudelijke kwaliteit en menselijke goedkeuring worden apart vastgelegd.'}
