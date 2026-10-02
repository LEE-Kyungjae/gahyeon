"""Inspect whether v585 materials can safely preview the neutral v525 Ururu mesh."""

import json
from pathlib import Path

import unreal


NEUTRAL = "/Game/LivingCharacterPOC/v525/Characters/UruruPreview/Ururu_Normalized_v523"
TEXTURED = (
    "/Game/LivingCharacterPOC/v585/Characters/UruruCentimeterNormalized/"
    "Ururu_CentimeterNormalized_v584"
)
REPORT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/"
    "living-character-poc-v672-ururu-material-compatibility/report.json"
)


def _slots(mesh):
    result = []
    for index, slot in enumerate(mesh.get_editor_property("materials")):
        material = slot.get_editor_property("material_interface")
        result.append({
            "index": index,
            "slotName": str(slot.get_editor_property("material_slot_name")),
            "material": material.get_path_name() if material else None,
        })
    return result


def inspect_ururu_material_compatibility_v672():
    if REPORT.exists():
        raise RuntimeError("refusing to overwrite immutable v672 report")
    neutral = unreal.load_asset(NEUTRAL)
    textured = unreal.load_asset(TEXTURED)
    if neutral is None or textured is None:
        raise RuntimeError("required Ururu meshes are unavailable")
    neutral_slots = _slots(neutral)
    textured_slots = _slots(textured)
    neutral_names = [slot["slotName"] for slot in neutral_slots]
    textured_names = [slot["slotName"] for slot in textured_slots]
    skeleton_match = neutral.skeleton.get_path_name() == textured.skeleton.get_path_name()
    compatible = skeleton_match and neutral_names == textured_names
    REPORT.parent.mkdir(parents=True, exist_ok=False)
    REPORT.write_text(json.dumps({
        "schemaVersion": 1,
        "iteration": "v672",
        "state": "inspected-neutral-textured-material-compatibility",
        "neutralMesh": NEUTRAL,
        "texturedMesh": TEXTURED,
        "skeletonMatch": skeleton_match,
        "slotOrderMatch": neutral_names == textured_names,
        "compatibleForTransientMaterialBorrow": compatible,
        "neutralSlots": neutral_slots,
        "texturedSlots": textured_slots,
        "automaticApproval": False,
    }, indent=2) + "\n", encoding="utf-8")
    unreal.log(f"Ururu v672 material compatibility: {compatible}")
    unreal.SystemLibrary.quit_editor()


inspect_ururu_material_compatibility_v672()
