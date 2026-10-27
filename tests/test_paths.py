"""livemind.paths: default relativi alla repo, override da variabili d'ambiente."""
import importlib
from pathlib import Path

import pytest

import livemind.paths as paths


def _reload(monkeypatch, **env):
    for k in ("LIVEMIND_ROOT", "LIVEMIND_OUT", "LIVEMIND_PROJECT_DIRS", "LIVEMIND_MASTER_SRC"):
        monkeypatch.delenv(k, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    return importlib.reload(paths)


def test_defaults_relative_to_repo(monkeypatch):
    p = _reload(monkeypatch)
    assert p.ROOT == Path(__file__).resolve().parents[1]
    assert p.OUT == p.ROOT / "out"


def test_env_override(monkeypatch, tmp_path):
    p = _reload(monkeypatch, LIVEMIND_OUT=str(tmp_path),
                LIVEMIND_PROJECT_DIRS=str(tmp_path / "a") + __import__("os").pathsep + str(tmp_path / "b"))
    assert p.OUT == tmp_path
    assert p.PROJECT_DIRS == [tmp_path / "a", tmp_path / "b"]
    f = p.out_path("shots", "x.png")
    assert Path(f).parent.is_dir() and Path(f).parent == tmp_path / "shots"


def test_master_src_required(monkeypatch):
    p = _reload(monkeypatch)
    with pytest.raises(SystemExit):
        p.master_src()


def test_no_machine_paths_in_code():
    root = Path(paths.__file__).resolve().parents[1]
    bad = ("CLAUDE SPACE", "\\Users\\", "/Users/")
    hits = [str(f) for d in ("livemind", "tools", "scripts", "remote_script") for f in (root / d).rglob("*.py")
            if f.name != "test_paths.py" and any(b in f.read_text(encoding="utf-8", errors="ignore") for b in bad)]
    tracked = __import__("subprocess").run(["git", "ls-files"], cwd=root, capture_output=True, text=True).stdout.split("\n")
    assert [h for h in hits if Path(h).relative_to(root).as_posix() in tracked] == []
