import re

import pytest

from livemind.brain import kb
from livemind.brain.tools import TOOLS, dispatch
from livemind.mastering.ozone_chains import (
    DESTINATIONS, GENRES, chain_for, comp_release_hint_ms, delay_ms, describe)

OZONE_MODULES = ["Clarity", "Dynamic EQ", "Dynamics", "Equalizer", "Exciter", "Imager",
                 "Impact", "Low End Focus", "Master Rebalance", "Match EQ", "Maximizer",
                 "Spectral Shaper", "Stabilizer", "Vintage Compressor", "Vintage EQ",
                 "Vintage Limiter", "Vintage Tape", "Dither", "Codec Preview",
                 "Master Assistant", "Stem Focus"]


def test_topics_present():
    t = kb.list_topics()
    for name in ("mastering/ozone11", "mastering/mastering-techniques",
                 "mastering/compression", "mastering/return-fx", "mastering/span-plus"):
        assert name in t


def test_ozone_doc_covers_every_module():
    text = kb.read("ozone11")
    for m in OZONE_MODULES:
        assert m in text, m


def test_search_finds_maximizer_for_irc():
    hits = kb.search("IRC 4 Transient Soft Clip")
    assert hits and "Maximizer" in hits[0]["section"]


def test_search_rumble_kick_in_return_fx():
    hits = kb.search("rumble kick sidechain riverbero")
    assert hits[0]["topic"] == "mastering/return-fx"


def test_search_span_sigma():
    hits = kb.search("RT Sigma dinamica per banda")
    assert hits[0]["topic"] == "mastering/span-plus"


def test_search_empty_query():
    assert kb.search("   ") == []


def test_read_unknown_topic():
    with pytest.raises(FileNotFoundError):
        kb.read("non-esiste")


@pytest.mark.parametrize("genre", GENRES)
@pytest.mark.parametrize("dest", DESTINATIONS)
def test_chains_are_sane(genre, dest):
    c = chain_for(genre, dest)
    mods = c["modules"]
    assert mods[-1]["module"] == "Maximizer"          # limiter sempre ultimo
    mx = mods[-1]
    assert mx["true_peak"] is True and mx["output_db"] <= -1.0
    assert c["true_peak_max_dbtp"] <= -1.0
    imager = next(m for m in mods if m["module"] == "Imager")
    low = min(imager["bands"], key=lambda b: b["range_hz"][0])
    assert low["width"] == -100 and low["range_hz"][1] >= 100   # bassi mono
    assert imager["stereoize"] is False
    lo, hi = c["drop_short_term_lufs"]
    assert -12 < lo < hi < -4
    assert describe(c).startswith("Ozone 11")


def test_streaming_is_less_limited_than_club():
    for g in GENRES:
        club = chain_for(g, "club")["modules"][-1]
        stream = chain_for(g, "streaming")["modules"][-1]
        assert stream["target_gr_db"][1] <= club["target_gr_db"][1]
        assert stream["soft_clip"]["amount_pct"] <= club["soft_clip"]["amount_pct"]


def test_chain_is_a_copy():
    a = chain_for("acid")
    a["modules"][-1]["output_db"] = 0.0
    assert chain_for("acid")["modules"][-1]["output_db"] == -1.0


def test_unknown_genre_and_destination():
    with pytest.raises(ValueError):
        chain_for("dubstep")
    with pytest.raises(ValueError):
        chain_for("acid", "radio")


def test_genre_aliases():
    assert chain_for("tekno-tribe")["genre"] == "tekno_tribe"


def test_delay_ms_values():
    assert delay_ms(120, "1/4") == 500.0
    assert delay_ms(120, "1/8d") == 375.0
    assert delay_ms(120, "1/8t") == pytest.approx(166.7)
    assert delay_ms(175, "1/64") == pytest.approx(21.4)
    with pytest.raises(ValueError):
        delay_ms(0)
    with pytest.raises(ValueError):
        delay_ms(120, "1/5")


def test_delay_table_in_doc_matches_function():
    text = kb.read("return-fx")
    header = None
    rows = 0
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cells and cells[0] == "BPM":
            header = cells[1:]
            continue
        if header and cells and re.fullmatch(r"\d+", cells[0]):
            bpm = int(cells[0])
            for div, val in zip(header, cells[1:]):
                assert float(val) == pytest.approx(delay_ms(bpm, div), abs=0.11), (bpm, div)
            rows += 1
    assert rows >= 5


def test_release_hint():
    lo, hi = comp_release_hint_ms(175)
    assert 90 < lo < hi < 260


def test_knowledge_tool_registered_and_dispatch():
    assert any(t["name"] == "knowledge" for t in TOOLS)
    out = dispatch("knowledge", {"action": "ozone_chain", "genre": "hardtek"}, live=None)
    assert "Maximizer" in out and "IRC 3" in out
    assert dispatch("knowledge", {"action": "delay_ms", "bpm": 150,
                                  "division": "1/16"}, live=None) == "100.0 ms"
    assert "mastering/ozone11" in dispatch("knowledge", {"action": "topics"}, live=None)
    assert "Stabilizer" in dispatch("knowledge", {"action": "search",
                                                  "query": "stabilizer cut 303"}, live=None)
