"""LiveMind — Remote Script per Ableton Live: server TCP + accesso diretto alla
Live Object Model (LOM), senza passare da AbletonOSC. Copre qualunque proprieta'/
metodo LOM tramite path generico (dispatch() in lom.py) — rack chains, automation
envelope, browser, freeze/flatten inclusi, senza bisogno di un wrapper per ognuno.

INSTALLAZIONE (vedi anche README.md):
1. Copiare l'intera cartella 'LiveMind' (questa) dentro:
     Windows: %USERPROFILE%\\Documents\\Ableton\\User Library\\Remote Scripts\\LiveMind
2. Riavviare Ableton Live.
3. Preferences > Link/Tempo/MIDI > Control Surface > selezionare "LiveMind".
4. Verificare nel Log.txt di Live la riga "LiveMind: in ascolto su 127.0.0.1:9005".

Il resto (client Python esterno, server MCP) vive in livemind/lom_client.py e
livemind/mcp_server_lom.py, nella cartella principale del progetto.
"""
from _Framework.ControlSurface import ControlSurface

from .server import CommandServer
from .lom import dispatch, LomError

HOST = "127.0.0.1"
PORT = 9005  # porta dedicata a LiveMind, diversa da AbletonOSC (11000/11001)


def create_instance(c_instance):
    return LiveMind(c_instance)


class LiveMind(ControlSurface):
    def __init__(self, c_instance):
        ControlSurface.__init__(self, c_instance)
        self._server = CommandServer(HOST, PORT, self._on_command, log=self.log_message)
        self._server.start()
        self.log_message("LiveMind Remote Script avviato")

    def _on_command(self, cmd: dict) -> dict:
        try:
            return dispatch(cmd, get_song=self.song, get_app=self.application)
        except LomError as e:
            return {"ok": False, "error": str(e)}

    def update_display(self) -> None:
        # Live chiama questo metodo periodicamente sul thread principale:
        # e' il punto sicuro per eseguire i comandi accumulati dal thread socket.
        ControlSurface.update_display(self)
        self._server.drain()

    def disconnect(self) -> None:
        self._server.stop()
        ControlSurface.disconnect(self)
