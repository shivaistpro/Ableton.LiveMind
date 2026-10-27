"""Installer del Remote Script e parsing del trasporto MCP (nessun Live/mcp richiesto)."""
from livemind import install, mcp_transport


def test_install_copies_sources(tmp_path):
    dest = install.install(tmp_path)
    assert (dest / "__init__.py").is_file() and (dest / "lom.py").is_file()
    assert not (dest / "__pycache__").exists()
    assert "LiveMind    OK" in install.check(tmp_path)
    assert "AbletonOSC  MANCA" in install.check(tmp_path)


def test_transport_parse():
    assert mcp_transport.parse([]) == ("stdio", None)
    assert mcp_transport.parse(["--http"]) == ("streamable-http", 8000)
    assert mcp_transport.parse(["--http", "9100"]) == ("streamable-http", 9100)
