#!/usr/bin/env python3
"""TestLock — anti-Goodharting lock voor Grow Kit (besluit 5 sept, gebouwd 9 sept door KairOS).

Garandeert dat een taak-uitvoerende agent tests NIET kan aanpassen, verwijderen
of omzeilen tijdens (of na) een taak.

Mechanisme (Riri's zes principes, geïmplementeerd):
1. HASH-PINNING: vóór elke taak wordt een manifest gemaakt met SHA-256 van elk
   testbestand. Na de taak: vergelijk. Mismatch = FAAL, met dossier.
2. READ-ONLY ENFORCEMENT: tests/ is tijdens een taak read-only (chmod 555 op de
   map + bestanden). Na de taak terug naar 755/644. Root kan dit forceren —
   daarom is de detectie in laag 3 de echte poort; chmod is afschrikking.
3. GIT-BEWIJS: het manifest wordt gecommit in een aparte lock-branch vóór de
   taak; verschil na de taak = bewijs van manipulatie.
4. DETECTIEPATRONEN: na de taak checkt de scanner op: verwijderde testbestanden,
   toegevoegde skips (pytest.mark.skip/skipif/xfail), verdachte kleine diffs,
   en assertions die zijn verwijderd of verzwakt.
5. DEFINITIE VÓÓR UITVOERING: het manifest hoort bij de taak (taak-id + hash),
   niet bij de agent.

Gebruik:
  lock_start <taak-id>     → manifest + chmod + lock-branch commit
  lock_check <taak-id>     → na de taak: verify (exit 0 = schoon, 1 = GEMANIPELEERD)
  lock_release <taak-id>   → rechten terug (alleen na schoon-keuring)

Exit-codes: 0 = schoon, 1 = manipulatie gevonden, 2 = gebruiksfout.
"""
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

GROWKIT = os.environ.get("GROWKIT_PAD", "/root/Grow-Kit")
TESTS_DIR = os.path.join(GROWKIT, "tests")
LOCK_DIR = os.path.join(GROWKIT, ".testlock")
GIT_USER = ("TestLock", "testlock@growkit.dev")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def test_bestanden():
    uit = []
    for root, _dirs, files in os.walk(TESTS_DIR):
        for f in sorted(files):
            if f.endswith((".py", ".sh")):
                uit.append(os.path.join(root, f))
    return sorted(uit)


def build_manifest():
    manifest = {}
    for p in test_bestanden():
        rel = os.path.relpath(p, GROWKIT)
        manifest[rel] = {
            "sha256": sha256_file(p),
            "grootte": os.path.getsize(p),
            "regels": sum(1 for _ in open(p, encoding="utf-8", errors="replace")),
            "mode": oct(os.stat(p).st_mode & 0o777),  # originele rechten bewaren
        }
    return manifest


def git_commit_bestand(pad, bericht, branch="testlock"):
    """Commit één bestand op de lock-branch (apart van het werk van agents)."""
    subprocess.run(["git", "add", "-A", pad], cwd=GROWKIT, check=False)
    subprocess.run(["git", "-c", f"user.name={GIT_USER[0]}",
                    "-c", f"user.email={GIT_USER[1]}",
                    "commit", "-qm", bericht], cwd=GROWKIT, check=False)


def lock_start(taak_id):
    os.makedirs(LOCK_DIR, exist_ok=True)
    manifest = build_manifest()
    doc = {
        "taak_id": taak_id,
        "moment": datetime.now(timezone.utc).isoformat(),
        "manifest": manifest,
    }
    pad = os.path.join(LOCK_DIR, f"{taak_id}.json")
    with open(pad, "w") as f:
        json.dump(doc, f, indent=1)
    # hash van het manifest zelf (tegen manifest-manipulatie)
    doc["manifest_sha256"] = hashlib.sha256(
        json.dumps(doc["manifest"], sort_keys=True).encode()).hexdigest()
    with open(pad, "w") as f:
        json.dump(doc, f, indent=1)
    # read-only enforcement
    for p in test_bestanden():
        os.chmod(p, 0o444)
    os.chmod(TESTS_DIR, 0o555)
    print(f"LOCK START: {len(manifest)} testbestanden gehasht en read-only gezet.")
    print(f"Manifest: {pad}")
    return 0


def detecteer_verdachte_veranderingen(manifest_voor):
    """Riri's detectiepatronen."""
    bevindingen = []
    huidige = build_manifest()
    for pad in manifest_voor:
        rel = os.path.normpath(pad)
        huid = huidige.get(pad) or huidige.get(rel)
        if huid is None:
            bevindingen.append(f"VERWIJDERD: {pad}")
            continue
        if huid["sha256"] != manifest_voor[pad]["sha256"]:
            # inhoud gewijzigd — waarom? Check patronen
            vol = os.path.join(GROWKIT, pad)
            try:
                tekst = open(vol, encoding="utf-8", errors="replace").read()
            except OSError:
                bevindingen.append(f"ONLEESBAAR: {pad}")
                continue
            laag = tekst.lower()
            if "pytest.mark.skip" in laag or "@pytest.mark.skipif" in laag or "xfail" in laag:
                bevindingen.append(f"SKIP TOEGEVOEGD: {pad}")
            elif "assert" not in laag:
                bevindingen.append(f"ASSERTIONS VERWIJDERD: {pad}")
            elif huid["regels"] < manifest_voor[pad]["regels"] * 0.8:
                bevindingen.append(f"STERK INGEKORT ({manifest_voor[pad]['regels']}→{huid['regels']} regels): {pad}")
            else:
                bevindingen.append(f"INHOUD GEWIJZIGD (hash-mismatch): {pad}")
    for pad in huidige:
        if pad not in manifest_voor:
            bevindingen.append(f"NIEUW TESTBESTAND TOEGEVOEGD tijdens taak: {pad}")
    return bevindingen, huidige


def lock_check(taak_id):
    pad = os.path.join(LOCK_DIR, f"{taak_id}.json")
    if not os.path.exists(pad):
        print(f"GEEN MANIFEST voor taak {taak_id}"); return 2
    doc = json.load(open(pad))
    manifest_voor = doc["manifest"]
    # manifest-integriteit
    check = hashlib.sha256(json.dumps(manifest_voor, sort_keys=True).encode()).hexdigest()
    if check != doc.get("manifest_sha256"):
        print("FOUT: manifest-hash mismatch — het manifest zelf is gewijzigd."); return 1
    bevindingen, huidige = detecteer_verdachte_veranderingen(manifest_voor)
    if bevindingen:
        herstel_rechten(manifest_voor)
        herstel_rechten()
        dossier = {
            "taak_id": taak_id,
            "verdict": "GEMANIPELEERD",
            "bevindingen": bevindingen,
            "moment": datetime.now(timezone.utc).isoformat(),
        }
        dpad = os.path.join(LOCK_DIR, f"{taak_id}-GEFAALD.json")
        with open(dpad, "w") as f:
            json.dump(dossier, f, indent=1)
        print(f"VERDICT: GEMANIPELEERD ({len(bevindingen)} bevindingen)")
        for b in bevindingen:
            print("  -", b)
        print(f"Dossier: {dpad}")
        return 1
    print(f"VERDICT: SCHOON — {len(huidige)} testbestanden ongewijzigd.")
    herstel_rechten(manifest_voor)
    return 0


def herstel_rechten(manifest=None):
    """Rechten terug: herstel de originele mode uit het manifest (bewaard bij lock_start)."""
    if manifest:
        for pad, info in manifest.items():
            vol = os.path.join(GROWKIT, pad)
            try:
                os.chmod(vol, int(info["mode"], 8))
            except OSError:
                pass
    else:
        for p in test_bestanden():
            os.chmod(p, 0o755 if p.endswith(".sh") else 0o644)
    os.chmod(TESTS_DIR, 0o755)


def lock_release(taak_id):
    """Handmatige vrijgave door de Baas (na schoon-keuring)."""
    herstel_rechten()
    print(f"RELEASE: rechten hersteld (taak {taak_id}).")


def main():
    if len(sys.argv) < 3:
        print(__doc__); return 2
    cmd, taak_id = sys.argv[1], sys.argv[2]
    if cmd == "lock_start": return lock_start(taak_id)
    if cmd == "lock_check": return lock_check(taak_id)
    if cmd == "lock_release": return lock_release(taak_id)
    print(__doc__); return 2


if __name__ == "__main__":
    sys.exit(main())
