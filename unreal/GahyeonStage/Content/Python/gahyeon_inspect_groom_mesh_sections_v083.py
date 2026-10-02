"""Inspect source and target skeletal material sections for Groom transfer."""

import json
from pathlib import Path

import unreal


SOURCE_PATH = "/MetaHumanCharacter/Optional/Grooms/GroomMesh/SKM_Groom_Head_Legacy01"
TARGET_PATH = "/Game/Gahyeon/CharacterPipeline/v027/AssembledMedium/Skotukeda_Medium_v027/Face/SKM_MHC_Skotukeda_Baseline_v026_FaceMesh"
OUTPUT = Path("/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/v083-groom-sections/inspection.json")


def slots(mesh):
    result = []
    for index, skeletal_material in enumerate(mesh.get_editor_property("materials")):
        material = skeletal_material.get_editor_property("material_interface")
        result.append({
            "index": index,
            "slotName": str(skeletal_material.get_editor_property("material_slot_name")),
            "importedSlotName": str(skeletal_material.get_editor_property("imported_material_slot_name")),
            "material": material.get_path_name() if material else None,
        })
    return result


if OUTPUT.exists():
    raise RuntimeError(f"refusing to overwrite v083 inspection: {OUTPUT}")
source = unreal.EditorAssetLibrary.load_asset(SOURCE_PATH)
target = unreal.EditorAssetLibrary.load_asset(TARGET_PATH)
if source is None or target is None:
    raise RuntimeError("Groom transfer mesh unavailable")
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(json.dumps({
    "schemaVersion": 1,
    "iteration": "v083",
    "state": "read-only-groom-section-inspection",
    "sourceMesh": source.get_path_name(),
    "sourceSlots": slots(source),
    "targetMesh": target.get_path_name(),
    "targetSlots": slots(target),
    "automaticApproval": False,
    "productionReady": False,
}, indent=2) + "\n", encoding="utf-8")
unreal.SystemLibrary.quit_editor()
