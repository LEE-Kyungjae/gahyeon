"""Capture Ururu's exact UE-imported facial curve peaks as immutable v720."""

from __future__ import annotations

from pathlib import Path


SOURCE = Path(__file__).with_name("capture_ururu_ue_animation_qa_v709.py")
OLD_STATES = 'STATES = (("neutral", 1), ("blink", 10), ("gaze-left", 20), ("gaze-right", 30))'
PEAK_STATES = 'STATES = (("neutral", 0), ("blink", 9), ("gaze-left", 19), ("gaze-right", 29))'


def capture_ururu_ue_animation_qa_v720() -> None:
    if not SOURCE.is_file():
        raise FileNotFoundError(SOURCE)
    source = SOURCE.read_text(encoding="utf-8")
    if source.count("v709") < 10 or OLD_STATES not in source:
        raise RuntimeError("sealed v709 capture protocol changed unexpectedly")
    source = source.replace(OLD_STATES, PEAK_STATES)
    source = source.replace("v709", "v720").replace("V709", "V720")
    exec(compile(source, str(SOURCE) + "::v720", "exec"), {"__name__": "__main__"})


capture_ururu_ue_animation_qa_v720()
