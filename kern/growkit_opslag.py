"""Procesveilige JSON-transacties voor bestaande Grow Kit-bestanden.

De lock staat naast het bestand (blijft stabiel bij os.replace). Een commit
schrijft en fsynct eerst een tijdelijk bestand, vervangt atomair de snapshot,
en fsynct de map. Een exception vóór replace bewaart de vorige snapshot.
Corruptie wordt nooit als een lege geschiedenis behandeld.
"""
from contextlib import contextmanager
from copy import deepcopy
import fcntl
import json
import os
from pathlib import Path
import tempfile


def schrijf_atomair(pad: Path, waarde) -> None:
    pad = Path(pad)
    pad.parent.mkdir(parents=True, exist_ok=True)
    fd, naam = tempfile.mkstemp(prefix=f'.{pad.name}.', dir=pad.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(waarde, f, ensure_ascii=False, indent=2)
            f.write('\n')
            f.flush()
            os.fsync(f.fileno())
        os.replace(naam, pad)
        map_fd = os.open(pad.parent, os.O_RDONLY)
        try:
            os.fsync(map_fd)
        finally:
            os.close(map_fd)
    finally:
        if os.path.exists(naam):
            os.unlink(naam)


@contextmanager
def transactie(pad: Path, standaard=None, *, append_only=False):
    pad = Path(pad)
    pad.parent.mkdir(parents=True, exist_ok=True)
    with open(pad.with_name(pad.name + '.lock'), 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            waarde = json.loads(pad.read_text(encoding='utf-8')) if pad.exists() else deepcopy(standaard if standaard is not None else [])
            if not isinstance(waarde, type(standaard if standaard is not None else [])):
                raise ValueError(f'Ongeldig opslagformaat: {pad}')
            origineel = deepcopy(waarde)
            yield waarde
            if append_only and waarde[:len(origineel)] != origineel:
                raise ValueError('Bestaande gebeurtenissen mogen niet gewijzigd worden')
            schrijf_atomair(pad, waarde)
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def voeg_gebeurtenissen_toe(pad: Path, gebeurtenissen: list[dict]) -> None:
    with transactie(pad, append_only=True) as entries:
        entries.extend(gebeurtenissen)
