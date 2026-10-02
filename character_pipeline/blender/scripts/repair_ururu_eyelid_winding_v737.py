#!/usr/bin/env python3
"""Rebuild corrected eyelids with the exact v688 FBX export contract."""

from __future__ import annotations

from pathlib import Path


SOURCE = Path(__file__).with_name("repair_ururu_eyelid_winding_v733.py")
SMOOTHING_OVERRIDE = '        mesh_smooth_type="FACE",\n'


def repair_ururu_eyelid_winding_v737() -> None:
    if not SOURCE.is_file():
        raise FileNotFoundError(SOURCE)
    source = SOURCE.read_text(encoding="utf-8")
    if source.count("v733") != 6 or source.count(SMOOTHING_OVERRIDE) != 1:
        raise RuntimeError("sealed v733 repair protocol changed unexpectedly")
    source = source.replace(SMOOTHING_OVERRIDE, "")
    source = source.replace("v733", "v737").replace("V733", "V737")
    exec(compile(source, str(SOURCE) + "::v737", "exec"), {"__name__": "__main__"})


repair_ururu_eyelid_winding_v737()
