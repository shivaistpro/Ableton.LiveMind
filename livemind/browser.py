"""Ricerca e caricamento di device dal browser di Live, via LOM.

Il tool 'load_device' cerca nel browser con la UI e carica il PRIMO risultato:
inutile quando due plugin hanno lo stesso nome (es. BankBreaker esiste sia di
due vendor diversi). Qui si naviga l'albero del browser e si carica
l'item esatto, identificato anche dal produttore.

Uso:
    python -m livemind.browser find BankBreaker
    python -m livemind.browser load BankBreaker <vendor>
"""
from __future__ import annotations
import sys

from livemind.lom_client import LomClient

# Solo 'plugins' di default: ogni passo dell'albero e' una chiamata TCP al
# Remote Script, e scandire anche instruments/audio_effects/midi_effects vuol
# dire migliaia di round trip (minuti). Gli altri rami vanno chiesti a mano.
ROOTS = ["plugins"]


def _name(lom: LomClient, path: list) -> str:
    r = lom.get(path, "name", root="app")
    return r.get("value") if r.get("ok") else ""


def _len(lom: LomClient, path: list) -> int:
    r = lom.length(path, root="app")
    return int(r.get("value", 0)) if r.get("ok") else 0


def walk(lom: LomClient, path: list, depth: int = 0, max_depth: int = 3):
    """Percorre l'albero del browser restituendo (path, nome, profondita')."""
    n = _len(lom, path + ["children"])
    for i in range(n):
        child = path + ["children:%d" % i]
        yield child, _name(lom, child), depth
        if depth < max_depth:
            yield from walk(lom, child, depth + 1, max_depth)


def find(name: str, roots=None, max_depth: int = 2) -> list[tuple[list, str]]:
    """Tutti gli item il cui nome contiene `name`, con il percorso completo."""
    lom = LomClient(timeout=20.0)
    out = []
    for root in (roots or ROOTS):
        for path, nm, _ in walk(lom, ["browser", root], max_depth=max_depth):
            if name.lower() in (nm or "").lower():
                out.append((path, nm))
    return out


def load(name: str, vendor: str | None = None) -> str:
    """Carica sulla traccia selezionata. `vendor` disambigua gli omonimi
    controllando che compaia nel percorso (es. la cartella del vendor)."""
    lom = LomClient(timeout=20.0)
    hits = find(name)
    if not hits:
        return f"nessun item di browser per '{name}'"
    chosen = None
    for path, nm in hits:
        if vendor is None:
            chosen = (path, nm)
            break
        # il produttore e' il nome del nodo padre (cartella del browser)
        parent = path[:-1]
        if vendor.lower() in (_name(lom, parent) or "").lower():
            chosen = (path, nm)
            break
    if chosen is None:
        trovati = ", ".join(nm for _, nm in hits)
        return f"'{name}' trovato ma non sotto '{vendor}' (trovati: {trovati})"
    path, nm = chosen
    r = lom.call(["browser"], "load_item", [{"__lom_ref__": path}], root="app")
    return f"caricato {nm} da {path} -> {r}"


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "find":
        for p, n in find(sys.argv[2]):
            print(n, "|", "/".join(p))
    elif cmd == "load":
        print(load(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None))
