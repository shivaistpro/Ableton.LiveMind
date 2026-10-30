from livemind.samples import load


class FakeLom:
    def __init__(self, ok=True):
        self.calls, self.sets, self.ok = [], [], ok

    def call(self, path, method, args=None, root="song"):
        self.calls.append((path, method, args))
        return {"ok": self.ok, "error": "boom"}

    def set(self, path, prop, value, root="song"):
        self.sets.append((path, prop, value))
        return {"ok": True}


def test_session_slot(tmp_path):
    f = tmp_path / "kick.wav"; f.write_bytes(b"x")
    lom = FakeLom()
    out = load(lom, str(f), 2, clip=3, name="KICK")
    assert lom.calls == [(["tracks:2", "clip_slots:3"], "create_audio_clip", [str(f)])]
    assert lom.sets == [(["tracks:2", "clip_slots:3", "clip"], "name", "KICK")]
    assert "session [2,3]" in out


def test_arrangement_position(tmp_path):
    f = tmp_path / "loop.wav"; f.write_bytes(b"x")
    lom = FakeLom()
    load(lom, str(f), 1, position=16)
    assert lom.calls == [(["tracks:1"], "create_audio_clip", [str(f), 16.0])]


def test_missing_file_and_error(tmp_path):
    assert "non trovato" in load(FakeLom(), "rel.wav", 0, clip=0)
    f = tmp_path / "a.wav"; f.write_bytes(b"x")
    assert "ERRORE" in load(FakeLom(ok=False), str(f), 0, clip=0)
    assert "LOM non disponibile" in load(None, str(f), 0)
