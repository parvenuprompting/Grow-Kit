#!/usr/bin/env python3
"""GrowKit goedkeurings-audit — wat heb je een code-agent allemaal laten doen?

Leest de sessie-logboeken van Codex (~/.codex/sessions/*.jsonl) en Claude Code
(~/.claude/projects/*/*.jsonl), haalt er alle uitgevoerde commando's en
bestandsacties uit, en legt per actie uit wat hij deed — in simpele taal,
zonder jargon. Kritische acties (wissen, pushen, secrets lezen, systeem-
aanpassingen) worden gemarkeerd zodat je ze kunt nalopen.

Kernregel (GrowKit-filosofie): de uitleg is een *weergave van wat er gebeurde*,
geen oordeel. De mens leest en beslist.

Gebruik:
    python3 kern/growkit_goedkeuring.py --rapport           # samenvatting per agent
    python3 kern/growkit_goedkeuring.py --agent codex       # alle acties, met uitleg
    python3 kern/growkit_goedkeuring.py --kritiek           # alleen de opvallende acties
"""
import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

HOME = Path.home()

# ---------------------------------------------------------------- categorieën
# Elke actie krijgt: soort (lezen/schrijven/wissen/uitvoeren/netwerk/git),
# risico (groen/geel/rood) en een simpele uitleg.

_LEES = ("ls", "cat ", "head", "tail", "sed -n", "nl ", "rg ", "grep", "find ",
         "wc ", "file ", "which ", "du ", "stat ", "pwd", "echo", "tree",
         "Read", "Glob", "Grep", "rg --files", "git log", "git status",
         "git diff", "git show", "git log ", "git remote", "git branch",
         "git ls-files", "git status", "git fetch", "git stash list")
_NETWERK = ("curl", "wget", "ping", "ssh ", "scp ", "gh api", "npx prisma db seed")
_GIT_CHANGED = ("git add", "git commit", "git merge", "git checkout -b",
                "git push", "git branch -d", "git branch -D", "git reset",
                "git rebase", "git checkout main", "git rm", "git cherry-pick")
_WIS = ("rm ", "rm -", "rmdir", "git push origin --delete", "trash ", "unlink")
_SECRETS = (".env", "secret", "credential", "id_ed25519", "private key",
            "api_key", "apikey", "token", "password", "auth.json")
_SYSTEEM = ("sudo ", "launchctl", "defaults write", "killall", "kill -9",
            "chmod ", "chown ", "mv ", "mkdir", "pip install", "npm install",
            "brew ", "docker ", "prisma migrate", "git push")
_BOUW = ("npm ", "npx ", "tsc", "jest", "pytest", "python3 -m unittest",
         "make ", "cargo ", "swift build", "xcodebuild", "prisma generate",
         "prisma format", "prisma validate", "prisma db seed", "prisma studio")


def _soort_en_risico(commando: str, tool: str) -> tuple[str, str, bool]:
    """Retourneer (soort, risico, kritiek) voor één actie."""
    c = commando
    cl = c.lower()
    # Bestandswijziging via apply_patch (Codex) — altijd vóór de rest beoordelen
    if "apply_patch" in c[:40]:
        return "bestand schrijven", "geel", False
    # Wissen of onherstelbaar
    if any(c.startswith(w) or f" {w}" in c or c == w.strip() for w in ("rm ", "rm -", "rmdir")):
        return "wissen", "rood", True
    if "push origin --delete" in c:
        return "wissen (branch op de server)", "rood", True
    # Git-acties die geschiedenis veranderen
    if any(w in c for w in ("git push", "git merge", "git rebase", "git reset")):
        if "--delete" in c or "-D " in c:
            return "wissen (branch op de server)", "rood", True
        if "git push" in c:
            return "git delen (push)", "geel", False
        return "git samenvoegen/terugdraaien", "geel", True if "reset" in c else False
    # Secrets lezen — alleen bij écht lezen; schrijven (cat > x.env) is geen secret-lezen.
    if any(s in cl for s in (".env", "secret", "credential")) and any(
            w in cl for w in ("cat ", "grep ", "less ", "head ", "tail ")) \
            and ">" not in c and "<<" not in c:
        return "geheimbestand lezen", "rood", True
    # Schrijven naar bestanden
    if tool in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
        return "bestand schrijven", "geel", False
    if any(w in c for w in ("> ", ">> ", "tee ", "cat <<", "sed -i", "sed -i ''")):
        return "bestand schrijven", "geel", False
    # Systeem / installeren
    if any(cl.startswith(w) for w in ("sudo ", "launchctl", "defaults write")):
        return "systeem aanpassen", "rood", True
    if any(w in cl for w in ("pip install", "npm install", "brew install", "gem install")):
        return "software installeren", "geel", False
    if "docker" in cl:
        return "docker (containers)", "geel", False
    # Script uitvoeren (node/python zonder bestandswijziging). Eerst venv-activatie
    # afstrippen, dan opnieuw kijken. Heredoc (<<) is een inline script — geen
    # omleiding naar een bestand, dus prima groen. `cat <<'X' > bestand` wél schrijven.
    # Samengestelde regels met echo-tekst ("no .env tracked") vals-niet in de
    # secret-leesval: alleen reageren als het .env-bestand zelf geopend wordt.
    if cl.startswith("cat .gitignore"):
        return "lezen", "groen", False
    # Vooraf gezette omgevingsvariabelen afstrippen: FOO=bar node ... blijft
    # een script-run (de waarden hier zijn testwaarden, geen echte secrets).
    werk = re.sub(r"^(source|\.\s+)\s+\.?[A-Za-z0-9_./-]*bin/activate\s*&&\s*", "", cl)
    werk = re.sub(r"^([A-Z_][A-Z0-9_]*=\S+\s+)+", "", werk)
    is_script = re.match(r"^(\.?[A-Za-z0-9_./-]*(venv|env)?/?bin/)?(node|npm (run|start|test)|python3?)", werk)
    schrijft = re.search(r">>>?>|[^<>]>\s*\S", werk.replace("2>&1", "").replace("&>", ""))
    if is_script and (schrijft is None or "<<" in werk):
        return "script uitvoeren", "groen", False
    # Bestandswijziging via apply_patch (Codex)
    if c.startswith("apply_patch:") or "apply_patch" in c[:20]:
        return "bestand schrijven", "geel", False
    # Onschuldige huishoudelijke acties die vaak als 'overig' zouden vallen
    if cl.startswith(("mkdir ", "touch ", "list_mcp", "update_plan", "pwd", "true", "sleep ")):
        return "lezen", "groen", False
    # Interactie met een draaiend proces / hulpvragen — geen wijziging
    if cl.startswith("write_stdin") or cl.startswith(("codex mcp", "codex --help", "lsof ")):
        return "lezen", "groen", False
    if " && " in cl or " || " in cl or ";" in cl:
        # Samengesteld commando: kritiek als één onderdeel kritiek is.
        delen = re.split(r"&&|\|\||;", c)
        uitslagen = [_soort_en_risico(d.strip(), tool) for d in delen if d.strip()]
        slechtste = max(uitslagen, key=lambda u: ("rood", "geel", "groen").index(u[1]))
        soort, risico, _ = slechtste
        return soort, risico, risico == "rood"
    if cl.startswith("kill ") or " lsof " in cl:
        return "script uitvoeren", "groen", False
    if cl.startswith(("ps ", "cp ", "mv ")):
        return "lezen" if cl.startswith("ps ") else "bestand schrijven", \
               "groen" if cl.startswith("ps ") else "geel", False
    if cl.startswith(("uvicorn", "gunicorn", "flask", "npm run dev", "npm start", "vite")) \
            or "uvicorn " in cl:
        return "server starten", "groen", False
    if cl.startswith("mcp__") or cl.startswith("request_user_input"):
        return "lezen", "groen", False
    if cl.startswith(("./node_modules/.bin/", ".venv/bin/", "venv/bin/", "./venv/bin/")) \
            or "tsx " in cl[:60] or re.search(r"\bnode\b", cl[:40]):
        return "script uitvoeren", "groen", False
    if cl.startswith(("md5", "shasum", "openssl dgst", "diff ", "cmp ")):
        return "lezen", "groen", False
    if cl.startswith("chmod "):
        return "bestand schrijven", "geel", False
    # awk/grep over .env dat alleen sleutelNAMEN toont (waarde gemaskeerd) is lezen
    if cl.startswith("awk") and ("print $1" in c or "<configured>" in c or "=<" in c):
        return "geheimbestand lezen", "rood", True
    # Eigen commit-hulpscript met git-argumenten = git delen (lokaal committen)
    if "committer" in cl[:30] or (cl.startswith("scripts/") and "commit" in cl):
        return "git delen (push)", "geel", False
    # Eigen scripts in de projectmap (./run_*.sh) = server starten
    if cl.startswith(("./run_", "./start", "./dev")):
        return "server starten", "groen", False
    if cl.startswith("senduserfile"):
        return "lezen", "groen", False
    # Versies/omgeving opvragen, afbeeldingen bekijken, wachten, tekstconversie
    if cl.startswith(("--version", "uname", "rustc", "xcode-select -p", "pgrep",
                      "ffmpeg -version", "gh --version", "textutil -help",
                      "wait_agent", "view_image", "ps ", "git branch --show-current")):
        return "lezen", "groen", False
    if cl.startswith(("perl -0pi", "sed -i", "perl -pi")):
        return "bestand schrijven", "geel", False
    if cl.startswith("tar ") or cl.startswith("unzip "):
        return "uitpakken", "geel", False
    # Netwerk
    if any(cl.startswith(w) for w in ("curl ", "wget ", "ssh ", "scp ", "gh api", "gh repo", "gh pr", "gh release", "gh auth")):
        return "netwerk", "geel", False
    # Bouwen en testen
    if any(w in cl for w in _BOUW):
        return "bouwen/testen", "groen", False
    # Git-lezen
    if any(c.startswith(w) for w in _GIT_CHANGED) or c.startswith("git "):
        return "git lezen", "groen", False
    # Lezen
    if any(c.startswith(w) for w in _LEES) or tool in ("Read", "Glob", "Grep"):
        return "lezen", "groen", False
    return "overig", "geel", True


# ------------------------------------------------- simpele uitleg per soort
_UITLEG = {
    "lezen": "De agent heeft gelezen. Ongevaarlijk — hij kon alleen kijken, niets veranderen.",
    "bouwen/testen": "De agent heeft code gebouwd of tests gedraaid. Dit verandert niets in je bestanden (hooguit tijdelijke bouwbestanden).",
    "bestand schrijven": "De agent heeft een bestand aangemaakt of aangepast. Meestal precies wat je vroeg — check bij twijfel het bestand in je project.",
    "bestand schrijven (sjabloon)": "De agent heeft een nieuw bestand neergezet (bijv. een sjabloon of config).",
    "git delen (push)": "De agent heeft werk naar GitHub gestuurd. Anderen (en andere machines) kunnen het nu zien.",
    "git samenvoegen/terugdraaien": "De agent heeft git-historie samengevoegd of teruggedraaid.",
    "wissen": "De agent heeft iets verwijderd. Kijk even of het terecht was — wissen kan je werk verliezen.",
    "wissen (branch op de server)": "De agent heeft een branch op GitHub verwijderd. Die zit niet meer op de server.",
    "geheimbestand lezen": "De agent heeft in een bestand met wachtwoorden of sleutels gekeken. Meestal onschuldig (bijv. database-check), maar dit mag je weten.",
    "systeem aanpassen": "De agent heeft iets op je Mac zelf aangepast (instellingen of systeem). Dit soort acties verdient extra aandacht.",
    "software installeren": "De agent heeft software geïnstalleerd (pakketten). Meestal nodig om te bouwen, maar het komt op je Mac terecht.",
    "netwerk": "De agent heeft contact gezocht met buiten (downloaden, API, server).",
    "docker (containers)": "De agent heeft Docker gebruikt (containers gestart/gestopt).",
    "git lezen": "De agent heeft git-geschiedenis bekeken. Ongevaarlijk.",
    "uitvoeren": "De agent heeft een programma gestart of een script gedraaid.",
    "onduidelijk": "De agent deed iets dat we niet simpel konden benoemen. Kijk even zelf.",
}


def _uitleg_actie(soort: str, commando: str, tool: str) -> str:
    basis = _UITLEG.get(soort, _UITLEG["onduidelijk"])
    # Voeg object toe: welk bestand of welke map?
    m = re.search(r"([~/][^\s'\"]+|[A-Za-z0-9_\-./]+\.[a-zA-Z]{1,6})", commando)
    object_str = ""
    if m and soort in ("bestand schrijven", "wissen", "geheimbestand lezen",
                       "lezen", "bestand schrijven (sjabloon)"):
        pad = m.group(1)
        naam = Path(pad).name or pad
        if naam and naam not in basis_pad_gelijkenissen(pad):
            object_str = f" Het ging om: {naam}."
    return basis + object_str


def basis_pad_gelijkenissen(pad: str) -> list[str]:
    """Kleine paden die geen informatie dragen (bijv. '/', '.')."""
    return ["/", ".", "..", "~"]


# ------------------------------------------------------------------ parsers
def _parse_codex(bestand: Path) -> list[dict]:
    """Codex-sessiebestand (JSONL) → lijst acties.

    Twee vormen: `function_call` (shell_command met commando-JSON) en
    `custom_tool_call` (apply_patch — bestandswijzigingen)."""
    acties = []
    try:
        for regel in bestand.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                d = json.loads(regel)
            except json.JSONDecodeError:
                continue
            p = d.get("payload", {})
            if not isinstance(p, dict):
                continue
            ts = d.get("timestamp", "")
            ptype = p.get("type")
            naam = p.get("name")
            # exec_command (event_msg-vorm): {"cmd": "...", "workdir": ...}
            if ptype == "exec_command" and p.get("cmd"):
                acties.append({"bron": "codex", "sessie": bestand.stem,
                               "tijdstip": ts, "tool": "shell",
                               "actie": str(p.get("cmd", ""))})
            elif ptype == "function_call" and naam in ("shell_command", "exec_command"):
                try:
                    args = json.loads(p.get("arguments", "{}"))
                    cmd = str(args.get("command") or args.get("cmd") or "")
                except json.JSONDecodeError:
                    cmd = str(p.get("arguments", ""))[:200]
                if cmd:
                    acties.append({"bron": "codex", "sessie": bestand.stem,
                                   "tijdstip": ts, "tool": "shell", "actie": cmd})
            elif ptype == "function_call":
                args = str(p.get("arguments", ""))[:200]
                acties.append({"bron": "codex", "sessie": bestand.stem,
                               "tijdstip": ts, "tool": str(naam), "actie": f"{naam}: {args}"})
            elif ptype == "custom_tool_call":
                invoer = str(p.get("input", ""))[:200]
                acties.append({"bron": "codex", "sessie": bestand.stem,
                               "tijdstip": ts, "tool": str(naam),
                               "actie": f"{naam}: {invoer}"})
    except Exception as e:
        print(f"  (kon {bestand.name} niet volledig lezen: {e})", file=sys.stderr)
    return acties


def _parse_claude(bestand: Path) -> list[dict]:
    """Claude Code-sessiebestand (JSONL) → lijst acties."""
    acties = []
    try:
        for regel in bestand.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                d = json.loads(regel)
            except json.JSONDecodeError:
                continue
            msg = d.get("message", {})
            cont = msg.get("content")
            ts = d.get("timestamp", "")
            if not isinstance(cont, list):
                continue
            for item in cont:
                if isinstance(item, dict) and item.get("type") == "tool_use":
                    naam = str(item.get("name", ""))
                    invoer = item.get("input", {}) or {}
                    cmd = str(invoer.get("command", "")) if "command" in invoer else str(invoer.get("file_path", naam))
                    acties.append({"bron": "claude", "sessie": bestand.parent.name + "/" + bestand.stem[:8],
                                   "tijdstip": ts, "tool": naam, "actie": cmd})
    except Exception as e:
        print(f"  (kon {bestand.name} niet volledig lezen: {e})", file=sys.stderr)
    return acties


# --------------------------------------------------------------- verwerking
def verzamel(bron: str | None = None) -> list[dict]:
    """Verzamel alle acties uit alle gevonden sessiebestanden."""
    alles = []
    if bron in (None, "codex"):
        for f in (HOME / ".codex" / "sessions").rglob("*.jsonl"):
            alles.extend(_parse_codex(f))
    if bron in (None, "claude"):
        for f in (HOME / ".claude" / "projects").rglob("*.jsonl"):
            alles.extend(_parse_claude(f))
    return alles


def verrijk(acties: list[dict]) -> list[dict]:
    """Voeg soort, risico, kritisch en simpele uitleg toe per actie."""
    for a in acties:
        soort, risico, kritisch = _soort_en_risico(a["actie"], a.get("tool", ""))
        a["soort"] = soort
        a["risico"] = risico
        a["kritisch"] = kritisch
        a["uitleg"] = _uitleg_actie(soort, a["actie"], a.get("tool", ""))
    return acties


def samenvatting(acties: list[dict]) -> str:
    """Menselijke samenvatting: wat is er gedaan, en wat verdient aandacht."""
    if not acties:
        return "Geen agent-acties gevonden in de sessielogboeken."
    from collections import Counter
    soorten = Counter(a["soort"] for a in acties)
    per_bron = Counter(a["bron"] for a in acties)
    regels = []
    regels.append(f"Samengevat: {len(acties)} acties gevonden "
                  f"({', '.join(f'{v} via {k}' for k, v in per_bron.most_common())}).")
    regels.append("")
    regels.append("Wat de agenten allemaal hebben gedaan, in gewone taal:")
    NL_NAMEN = {"lezen": "gelezen", "bouwen/testen": "gebouwd/getest",
                "bestand schrijven": "bestanden geschreven",
                "bestand schrijven (sjabloon)": "sjablonen neergezet",
                "git delen (push)": "naar GitHub gestuurd (push)",
                "git samenvoegen/terugdraaien": "git samengevoegd/teruggedraaid",
                "wissen": "gewist",
                "wissen (branch op de server)": "branches op GitHub gewist",
                "geheimbestand lezen": "geheimbestanden gelezen",
                "systeem aanpassen": "je Mac-systeem aangepast",
                "software installeren": "software geïnstalleerd",
                "netwerk": "netwerkcontact gezocht",
                "docker (containers)": "Docker gebruikt",
                "script uitvoeren": "scripts uitgevoerd",
                "uitpakken": "archieven uitgepakt",
                "server starten": "servers gestart (testomgevingen)",
                "git lezen": "git-geschiedenis bekeken",
                "uitvoeren": "scripts uitgevoerd",
                "onduidelijk": "onduidelijke acties"}
    for soort, aantal in soorten.most_common():
        naam = NL_NAMEN.get(soort, soort)
        regels.append(f"  - {aantal}× {naam}")
    kritiek = [a for a in acties if a["kritisch"]]
    if kritiek:
        regels.append("")
        regels.append(f"⚠️  {len(kritiek)} acties verdienen je aandacht (wissen, secrets, systeem of onduidelijk):")
        for a in kritiek[:15]:
            ts = (a.get("tijdstip") or "")[:16]
            cmd = a["actie"][:90]
            regels.append(f"  [{a['bron']} · {ts}] {a['soort']}: {cmd}")
        if len(kritiek) > 15:
            regels.append(f"  ... en nog {len(kritiek) - 15} — draai met --kritiek voor de volledige lijst.")
    else:
        regels.append("")
        regels.append("Geen kritische acties gevonden — alles was lezen, bouwen of bestanden schrijven binnen je projecten.")
    return "\n".join(regels)


# -------------------------------------------------------------------- CLI
def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Wat heeft de code-agent gedaan?")
    parser.add_argument("--rapport", action="store_true", help="simpele samenvatting (standaard)")
    parser.add_argument("--agent", choices=["codex", "claude"], help="alleen één agent")
    parser.add_argument("--kritiek", action="store_true", help="alleen kritische acties")
    parser.add_argument("--json", action="store_true", help="machinelijst (voor tests)")
    args = parser.parse_args(argv)

    acties = verzamel(args.agent)
    verrijk(acties)
    if args.json:
        print(json.dumps(acties, ensure_ascii=False, indent=2))
        return 0
    if args.kritiek:
        kritiek = [a for a in acties if a["kritisch"]]
        for a in kritiek:
            ts = (a.get("tijdstip") or "")[:16]
            print(f"[{a['bron']} · {ts}] {a['soort']} — {a['actie'][:140]}")
        if not kritiek:
            print("Geen kritische acties gevonden.")
        return 0
    print(samenvatting(acties))
    return 0


if __name__ == "__main__":
    sys.exit(main())
