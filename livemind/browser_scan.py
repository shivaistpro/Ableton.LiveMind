"""Elenca le cartelle del browser plugin di Live (categorie e produttori).

Serve a trovare il percorso esatto di un plugin quando due installazioni hanno
lo stesso nome. Tenuto come script separato perche' il `python -c` multilinea
lanciato da cmd non stampa nulla.

Uso:  python -m livemind.browser_scan            (categorie e produttori)
      python -m livemind.browser_scan BankBreaker  (cerca dentro i produttori)
"""
from __future__ import annotations
import sys

from livemind.lom_client import LomClient

lom = LomClient(timeout=20.0)


def name(path):
    return lom.get(path, "name", root="app").get("value")


def count(path):
    return int(lom.length(path, root="app").get("value", 0) or 0)


def main() -> None:
    """Senza argomenti elenca categorie e produttori (poche chiamate).
    Con un produttore elenca i suoi plugin. NON scandire tutti i produttori
    alla ricerca di un nome: sono migliaia di round trip e bloccano il bridge
    per minuti (gia' successo due volte)."""
    if len(sys.argv) > 1:
        vendor = sys.argv[1].lower()
        ncat = count(["browser", "plugins", "children"])
        for c in range(ncat):
            cat = ["browser", "plugins", f"children:{c}"]
            for i in range(count(cat + ["children"])):
                vend = cat + [f"children:{i}"]
                if vendor in (name(vend) or "").lower():
                    print(f"== {name(vend)}  ->  plugins/children:{c}/children:{i}")
                    for j in range(count(vend + ["children"])):
                        print(f"   [{j}] {name(vend + [f'children:{j}'])}")
                    return
        print(f"produttore '{sys.argv[1]}' non trovato")
        return

    ncat = count(["browser", "plugins", "children"])
    for c in range(ncat):
        cat = ["browser", "plugins", f"children:{c}"]
        print(f"== categoria {c}: {name(cat)}")
        for i in range(count(cat + ["children"])):
            print(f"   [{i}] {name(cat + [f'children:{i}'])}")


if __name__ == "__main__":
    main()
