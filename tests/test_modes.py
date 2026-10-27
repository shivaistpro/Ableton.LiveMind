from livemind.vision.modes import (MacroMode, MacroTarget, AirMidiMode,
                                   GestureMode, smooth)
from tests.test_gestures import make_hand


def test_smooth_converges():
    v = 0.0
    for _ in range(60):
        v = smooth(v, 1.0)
    assert v > 0.95


def test_macro_mode_maps_hand_position():
    m = MacroMode(targets={"rx": MacroTarget(0, 0, 1), "ry": MacroTarget(0, 0, 2)})
    hands = {"right": [(0.8, 0.2)] * 21}
    out = m.process(hands)
    assert len(out) == 2
    for tgt, v in out:
        assert 0.0 <= v <= 1.0
    # X alto → rx tende verso 0.8; Y=0.2 (alto sullo schermo) → ry alto
    d = {t.param: v for t, v in out}
    assert d[2] > 0.5


def test_airmidi_note_on_off():
    a = AirMidiMode(cols=4, rows=2, base_note=36)
    hand = make_hand([True, False, False, False])  # POINT
    # forza l'indice in alto a sinistra
    hand[8] = (0.05, 0.05)
    ev = a.process(hand)
    assert ev == ("note_on", 36)
    # mano sparita → note_off
    ev = a.process([])
    assert ev == ("note_off", 36)


def test_airmidi_grid_mapping():
    a = AirMidiMode(cols=4, rows=2, base_note=36)
    assert a.cell_to_note(0, 0) == 36
    assert a.cell_to_note(3, 1) == 43


def test_gesture_mode_debounced_action():
    gm = GestureMode(hold_frames=2)
    h = make_hand([True] * 4)  # OPEN_PALM → stop_all
    assert gm.process(h) is None
    act = gm.process(h)
    assert act is not None and act.action == "stop_all"
