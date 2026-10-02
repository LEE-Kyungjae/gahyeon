#!/usr/bin/env python3
"""Fail closed when a groom iteration bypasses the UE 5.8 MetaHuman pipeline."""

from pathlib import Path
import sys


REQUIRED = (
    "try_add_item_from_wardrobe_item",
    "MetaHumanPipelineSlotSelection",
    "try_add_slot_selection",
    "MetaHumanCharacterEditorSubsystem",
    "assemble_for_preview",
)
FORBIDDEN = (
    "set_groom_asset(",
    "set_binding_asset(",
    "set_relative_location(",
    "set_world_location(",
    "attachment_name",
)


def verify(path: Path) -> None:
    source = path.read_text()
    missing = [token for token in REQUIRED if token not in source]
    forbidden = [token for token in FORBIDDEN if token in source]
    if missing or forbidden:
        raise ValueError(f"missing={missing}, forbidden={forbidden}")


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: verify_gahyeon_official_groom_route.py SCRIPT")
    verify(Path(sys.argv[1]))
    print("Official UE 5.8 MetaHuman Wardrobe groom route verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
