"""Recursively inspect official Groom group LOD/card/mesh/material structures."""

import json
from pathlib import Path

import unreal


GROOM = (
    "/Game/Gahyeon/CharacterPipeline/v088/AssembledMedium/"
    "Skotukeda_WardrobeGroomQA_v088/Grooms/Hair_L_StraightBangs."
    "Hair_L_StraightBangs"
)
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v093-groom-group-diagnostic/group-structures.json"
)


def serialize(value, depth=0):
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if depth >= 4:
        return str(value)
    if isinstance(value, (list, tuple)):
        return [serialize(item, depth + 1) for item in value]
    try:
        return {"asset": value.get_path_name(), "class": value.get_class().get_name()}
    except Exception:
        pass
    result = {"type": type(value).__name__, "repr": str(value)}
    for name in sorted(item for item in dir(value) if not item.startswith("_") and item not in {"cast", "copy"}):
        try:
            child = getattr(value, name)
        except Exception as error:
            result[name] = {"error": str(error)}
            continue
        if callable(child):
            continue
        result[name] = serialize(child, depth + 1)
    return result


def inspect_groom_group_structures():
    if OUTPUT.exists():
        raise RuntimeError(f"refusing to overwrite immutable v093 inventory: {OUTPUT}")
    groom = unreal.load_asset(GROOM)
    if groom is None:
        raise RuntimeError(f"Groom asset unavailable: {GROOM}")
    sections = {}
    for name in (
        "hair_groups_lod", "hair_groups_cards", "hair_groups_meshes",
        "hair_groups_materials", "hair_groups_rendering", "hair_groups_info",
    ):
        sections[name] = serialize(groom.get_editor_property(name))
    OUTPUT.parent.mkdir(parents=True, exist_ok=False)
    OUTPUT.write_text(json.dumps({
        "schemaVersion": 1,
        "iteration": "v093",
        "state": "read-only-groom-group-diagnostic",
        "groomAsset": GROOM,
        "sections": sections,
        "automaticApproval": False,
        "productionReady": False,
    }, indent=2) + "\n", encoding="utf-8")
    unreal.log(f"Gahyeon v093 Groom group structures written: {OUTPUT}")
    unreal.SystemLibrary.quit_editor()


inspect_groom_group_structures()
