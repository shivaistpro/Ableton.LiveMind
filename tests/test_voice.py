import numpy as np
from livemind.voice.wake import extract_command
from livemind.voice.vad import UtteranceSegmenter


def test_wake_exact():
    assert extract_command("Livemind, porta il tempo a 145") == "porta il tempo a 145"


def test_wake_two_words():
    assert extract_command("Live mind lancia la scena 2") == "lancia la scena 2"


def test_wake_misspelled():
    assert extract_command("laiv maind ferma tutto") == "ferma tutto"


def test_no_wake_word_ignored():
    assert extract_command("alza il volume della cassa") is None
    assert extract_command("che bello questo groove") is None


def test_wake_only_returns_empty():
    assert extract_command("Livemind") == ""


def test_empty():
    assert extract_command("") is None


def test_segmenter_detects_utterance():
    seg = UtteranceSegmenter(threshold=0.1, silence_blocks=5, min_speech_blocks=3)
    out = None
    for _ in range(10):                      # parlato
        out = seg.feed(0.5, np.zeros(4))
        assert out is None
    for i in range(5):                       # silenzio → chiude
        out = seg.feed(0.01, np.zeros(4))
    assert out is not None and len(out) == 15


def test_segmenter_rejects_short_blip():
    seg = UtteranceSegmenter(threshold=0.1, silence_blocks=3, min_speech_blocks=5)
    seg.feed(0.5, np.zeros(4))               # 1 solo blocco di "parlato"
    out = None
    for _ in range(3):
        out = seg.feed(0.01, np.zeros(4))
    assert out is None                       # troppo corto: scartato


def test_segmenter_idle_stays_none():
    seg = UtteranceSegmenter(threshold=0.1)
    for _ in range(50):
        assert seg.feed(0.01, np.zeros(4)) is None
