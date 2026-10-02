"""Run the sealed v709 capture protocol as immutable v718 after cache recovery."""

from __future__ import annotations

from pathlib import Path


SOURCE = Path(__file__).with_name("capture_ururu_ue_animation_qa_v709.py")


def capture_ururu_ue_animation_qa_v718() -> None:
    if not SOURCE.is_file():
        raise FileNotFoundError(SOURCE)
    source = SOURCE.read_text(encoding="utf-8")
    if source.count("v709") < 10:
        raise RuntimeError("sealed v709 capture protocol changed unexpectedly")
    source = source.replace("v709", "v718").replace("V709", "V718")
    exec(compile(source, str(SOURCE) + "::v718", "exec"), {"__name__": "__main__"})


capture_ururu_ue_animation_qa_v718()
