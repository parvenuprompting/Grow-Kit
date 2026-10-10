"""Eén blijvend dossier per opdracht, van bevestigd plan tot resultaat."""
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import time
import uuid

from kern import growkit_route
from kern.growkit_opslag import transactie, voeg_gebeurtenissen_toe
from kern.growkit_resultaat import bewijsrapport
from kern.growkit_motor import voer_uit, machine_deel_voltooid, uitkomst
from kern.growkit_hervat import reconstructie
from kern.growkit_ratificatie import ratificeer_bulk, wacht_ratificatie_stappen
from kern.growkit_panic import activeer_panic, herstel_na_panic, lees_status


def _root():
    return Path(os.environ.get('GROWKIT_OPDRACHTEN', str(Path.home() / '.growkit' / 'opdrachten')))


def _pad(opdracht_id):
    if not isinstance(opdracht_id, str) or str(uuid.UUID(opdracht_id)) != opdracht_id:
        raise ValueError('Ongeldig opdracht-id')
    return _root() / opdracht_id / 'opdracht.json'


def _hash(plan):
    return hashlib.sha256(json.dumps(plan, sort_keys=True).encode()).hexdigest()


def nieuw(titel, criteria, profiel, sjablonen=None):
    if not titel.strip() or not criteria or not all(isinstance(c, str) and c.strip() for c in criteria):
        raise ValueError('Geef een titel en ten minste één acceptatiecriterium')
    if not profiel.get('stappen'):
        raise ValueError('Het plan bevat geen stappen')
    opdracht_id = str(uuid.uuid4())
    pad = _pad(opdracht_id)
    profiel = {**profiel, 'acceptatiecriteria': criteria}
    with transactie(pad, {}) as data:
        data.update(id=opdracht_id, titel=titel.strip(), profiel=profiel,
                    sjablonen=str(sjablonen) if sjablonen else None,
                    doel=str(pad.parent / 'resultaat'), status='concept',
                    aangemaakt=time.time(), seconden=0, ingrepen=0,
                    kosten_eur=0 if profiel.get('demo') else None,
                    gegevensroute=growkit_route.route(profiel)['soort'],
                    cloud_toestemming=False,
                    geschiedenis=[{'actie': 'concept', 'tijd': time.time()}])
    return lees(opdracht_id)


def lees(opdracht_id):
    data = json.loads(_pad(opdracht_id).read_text())
    log = Path(data['doel']) / 'logboek.json'
    entries = json.loads(log.read_text()) if log.exists() else []
    data['rapport'] = bewijsrapport(data['profiel'], entries)
    data['geschiedenis_stappen'] = entries
    data['plan_hash'] = _hash(data['profiel'])
    data['panic'] = lees_status(Path(data['doel']))
    data['wachtende_stappen'] = wacht_ratificatie_stappen(log)
    data['gegevensroute'] = growkit_route.route(data['profiel'])
    return data


def lijst():
    items, fouten = [], []
    for pad in sorted(_root().glob('*/opdracht.json')):
        try:
            data = lees(pad.parent.name)
            items.append({k: data[k] for k in ('id', 'titel', 'status', 'aangemaakt', 'seconden', 'ingrepen', 'kosten_eur')})
        except (ValueError, OSError, KeyError) as e:
            fouten.append(f'{pad.parent.name}: {e}')
    return {'opdrachten': sorted(items, key=lambda x: x['aangemaakt'], reverse=True), 'fouten': fouten}


def _wijzig(opdracht_id, actie, **velden):
    with transactie(_pad(opdracht_id), {}) as data:
        data.update(velden)
        data['geschiedenis'].append({'actie': actie, 'tijd': time.time(), **velden})


@contextlib.contextmanager
def _uitvoerslot(opdracht_id):
    with open(_pad(opdracht_id).with_name('uitvoering.lock'), 'a') as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('Deze opdracht wordt al uitgevoerd') from None
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def uitvoeren(opdracht_id, plan_hash, bevestig=False):
    if bevestig is not True:
        raise ValueError('Bevestig eerst het getoonde plan en de grenzen')
    with _uitvoerslot(opdracht_id):
        data = lees(opdracht_id)
        if plan_hash != data['plan_hash']:
            raise ValueError('Plan gewijzigd — bekijk en bevestig het actuele plan')
        if data['status'] in ('resultaat', 'goedgekeurd'):
            raise ValueError('Resultaat bestaat al; maak een nieuwe opdracht voor een nieuwe run')
        doel = Path(data['doel'])
        doel.mkdir(parents=True, exist_ok=True)
        if data['panic']['actief']:
            raise ValueError('PANIC actief — herstel handmatig vóór hervatten')
        if (growkit_route.heeft_toestemming_nodig(data['profiel'])
                and data.get('cloud_toestemming') is not True):
            raise ValueError('Deze opdracht stuurt gegevens naar buiten (cloud) — '
                             'geef eerst je toestemming op de opdrachtpagina')
        log = doel / 'logboek.json'
        herstel = reconstructie(log, data['profiel'])
        if herstel.get('fout'):
            raise ValueError('Logboek corrupt; uitvoering geblokkeerd')
        if data['wachtende_stappen']:
            raise ValueError('Beoordeel eerst de wachtende mens-stappen')
        rest = [s for s in data['profiel']['stappen'] if herstel['stappen'][s['id']]['beslissing'] != 'overslaan']
        start = time.monotonic()
        _wijzig(opdracht_id, 'plan_bevestigd', status='bezig', ingrepen=data['ingrepen'] + 1)
        try:
            ok = voer_uit({**data['profiel'], 'stappen': rest}, doel, log,
                          Path(data['sjablonen']) if data['sjablonen'] else None)
            status = 'resultaat' if ok else ('wacht_op_mens' if wacht_ratificatie_stappen(log) else 'gepauzeerd')
        except Exception as e:
            _wijzig(opdracht_id, 'onderbroken', status='gepauzeerd', fout=str(e))
            raise
        finally:
            _wijzig(opdracht_id, 'looptijd', seconden=data['seconden'] + time.monotonic() - start)
        _wijzig(opdracht_id, 'uitvoering', status=status)
    return lees(opdracht_id)


def beoordeel(opdracht_id, goedgekeurd, toelichting):
    if type(goedgekeurd) is not bool or not toelichting.strip():
        raise ValueError('Geef je oordeel en een inhoudelijke toelichting')
    with _uitvoerslot(opdracht_id):
        data = lees(opdracht_id)
        if data['status'] not in ('resultaat', 'wacht_op_mens'):
            raise ValueError('Er is geen resultaat of mens-stap om te beoordelen')
        log = Path(data['doel']) / 'logboek.json'
        wacht = data['wachtende_stappen']
        if wacht:
            ratificeer_bulk(log, wacht if goedgekeurd else [],
                            [] if goedgekeurd else [{'stap_id': s, 'reden': toelichting} for s in wacht])
            # Keur je de laatste mens-stappen goed en is er daarna niets meer te
            # draaien, dan ís dat het eindresultaat: één bevestiging, geen tweede
            # herstart-ronde. Staat er nog machinewerk open, dan blijft het bij
            # 'gepauzeerd' — eerst draaien, daarna het resultaat beoordelen.
            if goedgekeurd and machine_deel_voltooid(data['profiel'], log):
                status = 'goedgekeurd'
                voeg_gebeurtenissen_toe(log, [{'type': 'acceptatie', 'status': status,
                                               'bewijs': toelichting, 'tijdstip': time.time()}])
            else:
                status = 'gepauzeerd'
        else:
            status = 'goedgekeurd' if goedgekeurd else 'afgekeurd'
            voeg_gebeurtenissen_toe(log, [{'type': 'acceptatie', 'status': status,
                                        'bewijs': toelichting, 'tijdstip': time.time()}])
        _wijzig(opdracht_id, 'menselijk_oordeel', status=status, toelichting=toelichting,
                ingrepen=data['ingrepen'] + 1)
    return lees(opdracht_id)


def toestemming(opdracht_id, akkoord, toelichting):
    """Expliciete toestemming voor een cloudroute (advies 6) — mét reden.

    Zonder jouw akkoord start een cloud-opdracht niet. Het besluit landt in de
    geschiedenis, dus intrekken (akkoord=False) is net zo zichtbaar als geven.
    """
    if type(akkoord) is not bool or not str(toelichting).strip():
        raise ValueError('Geef je besluit en een korte reden')
    with _uitvoerslot(opdracht_id):
        data = lees(opdracht_id)
        _wijzig(opdracht_id, 'cloudtoestemming', cloud_toestemming=akkoord,
                toelichting=str(toelichting).strip(), ingrepen=data['ingrepen'] + 1)
    return lees(opdracht_id)


def panic(opdracht_id, herstel=False):
    data = lees(opdracht_id)
    doel = Path(data['doel'])
    doel.mkdir(parents=True, exist_ok=True)
    if herstel:
        herstel_na_panic(doel)
    else:
        activeer_panic(doel, 'Handmatig gepauzeerd vanuit opdrachtpagina')
    return lees(opdracht_id)
