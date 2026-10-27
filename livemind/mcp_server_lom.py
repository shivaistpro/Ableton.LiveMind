"""Server MCP sincrono basato sul Remote Script LiveMind (accesso diretto alla
Live Object Model via TCP) — complementare a mcp_server.py (basato AbletonOSC).

Perche' esiste in parallelo a mcp_server.py: AbletonOSC non espone rack chains,
automation envelope sulle clip, browser reale ne' freeze/flatten. Questo server
parla direttamente con un Remote Script (remote_script/LiveMind) che ha accesso
completo alla LOM, tramite un path generico get/set/call/len — qualunque
proprieta' o metodo LOM e' raggiungibile senza dover scrivere un wrapper per
ognuno (vedi remote_script/LiveMind/lom.py per il perche' di questa scelta).

Uso (registrato come server MCP esterno, es. Claude Desktop/Code, Codex CLI; ChatGPT con --http, vedi docs/SETUP.md):
  command: python
  args: ["-m", "livemind.mcp_server_lom"]
  cwd: <LIVEMIND_DIR>

Richiede il Remote Script LiveMind installato e selezionato in Ableton
(Preferences > Link/Tempo/MIDI > Control Surface). Vedi README.md.
"""
from __future__ import annotations
from typing import Callable, Literal, Optional, Union

# Tipo di 'value' per lom_set: deve avere un 'type' JSON-Schema esplicito
# (non 'Any' nudo) altrimenti FastMCP genera uno schema senza 'type' e il
# client MCP, non sapendo come serializzare il parametro, lo manda come
# stringa grezza — setattr() sulla LOM fallisce poi con ArgumentError perche'
# la C++ API si aspetta un float/bool nativo, non str (vedi test relativo).
LomValue = Union[bool, int, float, str, None]


def build_tools(client) -> dict[str, Callable[..., str]]:
    """Ritorna {nome_tool: funzione pura}, testabile con un client fittizio
    (vedi test_mcp_server_lom.py) senza rete ne' Ableton."""

    def connection_status() -> str:
        r = client.ping()
        if r.get("ok"):
            return "connesso: Remote Script LiveMind risponde su porta LOM"
        return f"NON risponde: {r.get('error', r)}. Verifica che 'LiveMind' sia selezionato in Live > Preferences > Control Surface."

    def lom_get(path: Optional[list] = None, prop: str = "", root: Literal["song", "app"] = "song") -> str:
        """Legge una proprieta' della Live Object Model per path generico.
        path: lista di step "nome" o "nome:indice", es. ["tracks:0","devices:1"].
        root: 'song' (Live Set, default) o 'app' (Application/browser).
        Esempio: lom_get(path=["tracks:0"], prop="name") -> nome della traccia 0."""
        r = client.get(path, prop, root=root)
        return str(r["value"]) if r.get("ok") else f"ERRORE: {r.get('error')}"

    def lom_set(path: Optional[list], prop: str, value: LomValue, root: Literal["song", "app"] = "song") -> str:
        """Scrive una proprieta' della LOM per path generico. Esempio:
        lom_set(path=["tracks:0","devices:1","chains:0"], prop="mute", value=True)."""
        r = client.set(path, prop, value, root=root)
        return "ok" if r.get("ok") else f"ERRORE: {r.get('error')}"

    def lom_call(path: Optional[list], method: str, args: Optional[list] = None,
                 root: Literal["song", "app"] = "song") -> str:
        """Chiama un metodo della LOM per path generico. Copre cio' che OSC non
        espone: rack (insert_chain, delete_chain), automation
        (parameter.automation_state via lom_get, re_enable_automation via qui),
        freeze/unfreeze/flatten (se esposti dalla LOM — verificare in Live: alcune
        build espongono solo lo stato, non l'azione), browser
        (application.browser... load_item()). Esempio: creare una scena:
        lom_call(path=[], method="create_scene", args=[-1])."""
        r = client.call(path, method, args=args, root=root)
        return str(r["value"]) if r.get("ok") else f"ERRORE: {r.get('error')}"

    def lom_len(path: Optional[list] = None, root: Literal["song", "app"] = "song") -> str:
        """Lunghezza di una collezione LOM (tracks, devices, chains, clip_slots...)."""
        r = client.length(path, root=root)
        return str(r["value"]) if r.get("ok") else f"ERRORE: {r.get('error')}"

    def _note_to_tuple(n: dict) -> list:
        return [n["pitch"], n.get("start_time", 0), n["duration"], n.get("velocity", 100), n.get("mute", False)]

    def _tuple_to_note(t: list) -> dict:
        pitch, start_time, duration, velocity, mute = t[0], t[1], t[2], t[3], t[4]
        return {"pitch": pitch, "start_time": start_time, "duration": duration, "velocity": velocity, "mute": mute}

    def lom_notes(action: Literal["get_extended", "add", "set_extended", "remove"],
                  path: list, notes: Optional[list] = None) -> str:
        """Note MIDI su una clip (formato dict: pitch/start_time/duration/
        velocity/mute). path punta alla Clip, es. ["tracks:1","clip_slots:0",
        "clip"]. action='get_extended' legge tutte le note; 'add' aggiunge
        senza toccare le esistenti; 'set_extended' sovrascrive tutte le note
        della clip; 'remove' le cancella tutte.

        Usa l'API 'legacy' get_notes/set_notes (tuple pitch/start_time/
        duration/velocity/mute), non get_notes_extended/add_new_notes: in
        questa build della LOM add_new_notes rifiuta sia dict che tuple per
        TNoteSpecification ("No registered converter ... from this Python
        object of type dict/tuple/str" a seconda dell'incapsulamento
        provato) — bug verificato, non reintrodurre. get_notes/set_notes
        sono verificati funzionanti e restano JSON-serializzabili (niente
        MidiNoteVector opaco da dover reinterpretare)."""
        if action == "get_extended":
            r = client.call(path, "get_notes", args=[0, 0, 100000, 128])
            if not r.get("ok"):
                return f"ERRORE: {r.get('error')}"
            return str([_tuple_to_note(t) for t in (r.get("value") or [])])
        elif action == "add":
            existing = client.call(path, "get_notes", args=[0, 0, 100000, 128])
            if not existing.get("ok"):
                return f"ERRORE: {existing.get('error')}"
            merged = (existing.get("value") or []) + [_note_to_tuple(n) for n in (notes or [])]
            r = client.call(path, "set_notes", args=[merged])
        elif action == "set_extended":
            r = client.call(path, "set_notes", args=[[_note_to_tuple(n) for n in (notes or [])]])
        elif action == "remove":
            r = client.call(path, "set_notes", args=[[]])
        else:
            return f"azione sconosciuta: {action}"
        if not r.get("ok"):
            return f"ERRORE: {r.get('error')}"
        return str(r.get("value", "ok"))

    return {
        "connection_status": connection_status,
        "lom_get": lom_get,
        "lom_set": lom_set,
        "lom_call": lom_call,
        "lom_len": lom_len,
        "lom_notes": lom_notes,
    }


def create_server(client):
    """Costruisce il FastMCP server registrando i tool. Import di 'mcp' qui
    dentro cosi' i test possono importare build_tools() senza il pacchetto 'mcp'."""
    from mcp.server.fastmcp import FastMCP

    server = FastMCP(
        "livemind-lom",
        instructions=(
            "Controllo diretto di Ableton Live via un Remote Script proprietario "
            "(remote_script/LiveMind), accesso completo alla Live Object Model — "
            "complementare a livemind-ableton (basato AbletonOSC). Usa questo server "
            "quando serve: rack chains/macro, automation envelope sulle clip, "
            "browser, freeze/flatten, o qualunque proprieta'/metodo LOM non coperto "
            "da un tool dedicato in livemind-ableton. Chiama sempre connection_status "
            "per primo. path e' una lista di step 'nome' o 'nome:indice' a partire da "
            "root ('song'=Live Set, 'app'=Application/browser), es. "
            "['tracks:0','devices:1','chains:0'] per la prima chain del rack in "
            "posizione 1 sulla traccia 0."
        ),
    )
    for name, func in build_tools(client).items():
        server.tool(name=name)(func)
    return server


def main() -> None:
    from .lom_client import LomClient
    print("[livemind-mcp-lom] connessione al Remote Script LiveMind (porta 9005)...")
    client = LomClient()
    server = create_server(client)
    print("[livemind-mcp-lom] server pronto")
    from livemind.mcp_transport import run
    run(server)


if __name__ == "__main__":
    main()
