"""Dispatcher generico sulla Live Object Model (LOM).

Nessuna dipendenza da 'Live' o '_Framework': opera per getattr/setattr/call su
QUALSIASI oggetto Python, quindi e' testabile al 100% fuori da Ableton con dei
mock. Dentro Ableton, root e' self.song() o self.application() (vedi __init__.py).

Path syntax: lista di step stringa, ognuno "nome" o "nome:indice", es.
["tracks:0", "devices:1", "parameters:2"] equivale al canonical path LOM
'live_set tracks 0 devices 1 parameters 2' (rack chain: ["tracks:0","devices:1",
"chains:0","devices:0"]).

Questo e' il nucleo che rende il controllo "100% automatizzato": qualunque
proprieta'/metodo esista nella Live Object Model (rack chains, automation_state
dei parametri, browser, freeze/flatten se disponibili, ecc.) e' raggiungibile
senza dover scrivere un wrapper dedicato per ognuno.
"""
from __future__ import annotations
from typing import Any, Callable, Optional


class LomError(Exception):
    pass


def _step(obj: Any, step: str) -> Any:
    if ":" in step:
        name, idx_s = step.split(":", 1)
        try:
            idx = int(idx_s)
        except ValueError:
            raise LomError(f"indice non numerico in step '{step}'")
    else:
        name, idx = step, None
    if not hasattr(obj, name):
        raise LomError(f"'{type(obj).__name__}' non ha '{name}'")
    val = getattr(obj, name)
    if idx is not None:
        try:
            val = val[idx]
        except (IndexError, TypeError, KeyError) as e:
            raise LomError(f"indice {idx} non valido su '{name}' ({e})")
    return val


def resolve(root: Any, path: Optional[list]) -> Any:
    """Naviga root seguendo path (lista di step). path vuoto/None -> root stesso."""
    obj = root
    for step in path or []:
        obj = _step(obj, step)
    return obj


def lom_get(root: Any, path: Optional[list], prop: str) -> Any:
    obj = resolve(root, path)
    if not hasattr(obj, prop):
        raise LomError(f"'{type(obj).__name__}' non ha proprieta' '{prop}'")
    return getattr(obj, prop)


def lom_set(root: Any, path: Optional[list], prop: str, value: Any) -> None:
    obj = resolve(root, path)
    if not hasattr(obj, prop):
        raise LomError(f"'{type(obj).__name__}' non ha proprieta' '{prop}'")
    setattr(obj, prop, value)


def lom_call(root: Any, path: Optional[list], method: str, args: Optional[list] = None) -> Any:
    obj = resolve(root, path)
    if not hasattr(obj, method):
        raise LomError(f"'{type(obj).__name__}' non ha metodo '{method}'")
    fn = getattr(obj, method)
    if not callable(fn):
        raise LomError(f"'{method}' su '{type(obj).__name__}' non e' chiamabile")
    return fn(*(args or ()))


def lom_len(root: Any, path: Optional[list]) -> int:
    obj = resolve(root, path)
    try:
        return len(obj)
    except TypeError as e:
        raise LomError(f"'{type(obj).__name__}' non ha lunghezza ({e})")


def _jsonable(val: Any) -> Any:
    """Rende serializzabile in JSON il risultato di una chiamata LOM. Oggetti
    LOM non primitivi (Track, Device, Clip...) diventano una rappresentazione
    minima invece di far fallire json.dumps."""
    if val is None or isinstance(val, (int, float, str, bool)):
        return val
    if isinstance(val, dict):
        return {k: _jsonable(v) for k, v in val.items()}
    if isinstance(val, (list, tuple)):
        return [_jsonable(v) for v in val]
    # Le collezioni della LOM (StringVector di value_items, vettori di device
    # o di clip) non sono list/tuple Python ma sono iterabili: senza questo
    # ramo diventavano un {"__lom_object__": ...} opaco e illeggibile.
    if hasattr(val, "__iter__") and not isinstance(val, (bytes, bytearray)):
        try:
            return [_jsonable(v) for v in val]
        except Exception:
            pass
    return {"__lom_object__": True, "class": type(val).__name__, "repr": str(val)}


def _tupleize(val: Any) -> Any:
    """Converte ricorsivamente le liste (sempre 'list' dopo un json.loads,
    JSON non ha il concetto di tupla) in tuple Python. Necessario perche'
    diverse API della LOM (es. Clip.set_notes) hanno firme C++ che accettano
    solo boost::python::tuple e rifiutano una list con un ArgumentError."""
    if isinstance(val, dict):
        return {k: _tupleize(v) for k, v in val.items()}
    if isinstance(val, list):
        return tuple(_tupleize(v) for v in val)
    return val


def _resolve_args(root: Any, args: Optional[list]) -> list:
    """Risolve gli argomenti di una call() che devono essere oggetti LOM (non
    JSON), es. Track.duplicate_clip_to_arrangement(clip, time) — clip e' un
    riferimento, non un valore. Un arg {"__lom_ref__": [...]} viene risolto
    via resolve(); tutti gli altri passano invariati (numeri/stringhe/bool),
    con le liste annidate convertite in tuple (vedi _tupleize)."""
    out = []
    for a in args or []:
        if isinstance(a, dict) and "__lom_ref__" in a:
            out.append(resolve(root, a["__lom_ref__"]))
        else:
            out.append(_tupleize(a))
    return out


def dispatch(cmd: dict, get_song: Callable[[], Any], get_app: Callable[[], Any]) -> dict:
    """Punto unico di ingresso: riceve il comando JSON gia' deserializzato,
    ritorna un dict pronto per essere serializzato in risposta.

    get_song/get_app sono callable pigri (risolti solo se root li richiede):
    nei test si passano mock, dentro Ableton self.song()/self.application()."""
    action = cmd.get("cmd")
    if action == "ping":
        return {"ok": True, "pong": True}

    root_name = cmd.get("root", "song")
    if root_name == "song":
        root = get_song()
    elif root_name == "app":
        root = get_app()
    else:
        return {"ok": False, "error": f"root sconosciuto: '{root_name}' (usa 'song' o 'app')"}

    path = cmd.get("path") or []
    try:
        if action == "get":
            return {"ok": True, "value": _jsonable(lom_get(root, path, cmd["prop"]))}
        if action == "set":
            lom_set(root, path, cmd["prop"], cmd["value"])
            return {"ok": True}
        if action == "call":
            args = _resolve_args(root, cmd.get("args"))
            result = lom_call(root, path, cmd["method"], args)
            return {"ok": True, "value": _jsonable(result)}
        if action == "len":
            return {"ok": True, "value": lom_len(root, path)}
        if action == "link":
            # setattr con un VALORE non-JSON: un altro oggetto LOM risolto
            # da value_path (es. Song.view.selected_track = tracks[i]).
            value = resolve(root, cmd.get("value_path") or [])
            lom_set(root, path, cmd["prop"], value)
            return {"ok": True}
        return {"ok": False, "error": f"comando sconosciuto: '{action}'"}
    except LomError as e:
        return {"ok": False, "error": str(e)}
    except KeyError as e:
        return {"ok": False, "error": f"campo mancante nel comando: {e}"}
    except Exception as e:  # ultima rete di sicurezza: mai far cadere il dispatcher
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}
