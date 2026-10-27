from livemind.vision.gestures import (classify, Gesture, GestureDebouncer,
                                      fingers_extended)


def make_hand(fingers_up: list[bool], thumb_out: bool = False):
    """Mano sintetica 21 landmark. Polso in basso (y=0.9), dita su/giù."""
    lm = [(0.5, 0.9)] * 21
    lm = list(lm)
    lm[0] = (0.5, 0.9)
    lm[2] = (0.5, 0.7)                      # thumb mcp
    lm[4] = (0.75 if thumb_out else 0.52, 0.6)  # thumb tip
    lm[12] = (0.5, 0.3)  # riferimento hand size (medio tip provvisorio)
    pip_y, up_y, down_y = 0.5, 0.3, 0.65
    for i, (tip, pip) in enumerate([(8, 6), (12, 10), (16, 14), (20, 18)]):
        lm[pip] = (0.4 + i * 0.05, pip_y)
        lm[tip] = (0.4 + i * 0.05, up_y if fingers_up[i] else down_y)
    return lm


def test_open_palm():
    assert classify(make_hand([True] * 4)) == Gesture.OPEN_PALM


def test_fist():
    assert classify(make_hand([False] * 4, thumb_out=False)) == Gesture.FIST


def test_point():
    assert classify(make_hand([True, False, False, False])) == Gesture.POINT


def test_two():
    assert classify(make_hand([True, True, False, False])) == Gesture.TWO


def test_short_landmarks_unknown():
    assert classify([(0.5, 0.5)] * 10) == Gesture.UNKNOWN


def test_debouncer_fires_once_after_hold():
    d = GestureDebouncer(hold_frames=3)
    h = make_hand([False] * 4)
    g = classify(h)
    assert d.update(g) is None
    assert d.update(g) is None
    assert d.update(g) == g        # 3° frame stabile: scatta
    assert d.update(g) is None     # non ri-scatta
