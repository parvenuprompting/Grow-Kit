"""growkit_breinzoeker — Trede 1: familie-brein-zoeker als Grow Kit-kernmodule.

Beantwoordt vragen uit de EIGEN familie-geschiedenis (besluiten, Academy-corpus,
curatie) via een lokale embedding-index. Embedding-berekening via OpenRouter;
zoekwerk (cosine, ranking, filtering) lokaal en offline testbaar.

Publieke functies:
- cosine(a, b) — gelijkenis tussen twee vectors
- zoek_in_index(index, query_vector, top, min_score) — ranking over een geladen index
- laad_index(pad) — index-bestand inlezen
- bouw_index(bron_pad, doel_pad, ...) — (her)bouw via embeddings (API-calls, niet getest hier)
"""
import json
from pathlib import Path


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(x * x for x in b) ** 0.5
    return dot / (na * nb) if na and nb else 0.0


def laad_index(pad: str) -> dict:
    p = Path(pad)
    if not p.exists():
        raise FileNotFoundError(f"brein-index niet gevonden: {pad}")
    return json.loads(p.read_text())


def zoek_in_index(index: dict, query_vector: list[float],
                  top: int = 5, min_score: float = 0.0) -> list[dict]:
    scores = []
    for i, vec in enumerate(index["vectors"]):
        s = cosine(query_vector, vec)
        if s >= min_score:
            scores.append({"score": s, **index["chunks"][i]})
    scores.sort(key=lambda x: x["score"], reverse=True)
    return scores[:top]


def bouw_index(bron_bestanden: list[str], doel_pad: str,
               key: str, model: str = "qwen/qwen3-embedding-8b",
               max_chunk: int = 1500, log=print) -> dict:
    """(Her)bouw de index uit bron-bestanden. Embedding via OpenRouter API.

    Deze functie doet netwerk-calls; testscenario's mocken embed() via injectie
    (zie familie_zoeker op de VPS voor de werkende implementatie).
    """
    raise NotImplementedError(
        "bouw_index vereist de VPS-implementatie (/root/familie_zoeker.py); "
        "deze module levert de testbare zoek-kern.")
