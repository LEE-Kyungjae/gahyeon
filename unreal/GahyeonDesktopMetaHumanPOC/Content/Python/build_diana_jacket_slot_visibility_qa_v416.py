"""Create two immutable QA maps that alternately hide Diana jacket slots 9 and 13."""

import json
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
SOURCE_MAP = "/Game/Gahyeon/Character2/Diana/v410/Runtime/L_DianaMacRuntimeHighKeyClearance_v410"
MASK = "/Game/Gahyeon/Character2/Diana/v414/Materials/M_Diana_UnderJacket_Invisible_v414"
MAPS = {
    9: "/Game/Gahyeon/Character2/Diana/v416/QA/L_DianaHideJacketSlot09_v416",
    13: "/Game/Gahyeon/Character2/Diana/v416/QA/L_DianaHideJacketSlot13_v416",
}
REPORT = ROOT / "artifacts/gahyeon-ch/iterations/v416-diana-jacket-slot-visibility-qa/report.json"

if REPORT.exists() or any(unreal.EditorAssetLibrary.does_asset_exist(path) for path in MAPS.values()):
    raise RuntimeError("refusing to overwrite immutable Diana v416 QA assets")
mask = unreal.load_asset(MASK)
if mask is None:
    raise RuntimeError(f"mask material unavailable: {MASK}")
for slot, output_map in MAPS.items():
    unreal.EditorLoadingAndSavingUtils.load_map(SOURCE_MAP)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    characters = [actor for actor in actors if isinstance(actor, unreal.SkeletalMeshActor)]
    if world is None or len(characters) != 1:
        raise RuntimeError("v410 character composition changed unexpectedly")
    characters[0].get_component_by_class(unreal.SkeletalMeshComponent).set_material(slot, mask)
    characters[0].set_actor_label(f"Diana_HideJacketSlot{slot:02d}_v416")
    if not unreal.EditorLoadingAndSavingUtils.save_map(world, output_map):
        raise RuntimeError(f"failed to save {output_map}")

report = {
    "schemaVersion": 1,
    "iteration": "v416-diana-jacket-slot-visibility-qa",
    "status": "diagnostic",
    "sourceMap": SOURCE_MAP,
    "maps": {str(slot): path for slot, path in MAPS.items()},
    "method": "alternate zero-opacity isolation of the two jacket material sections",
    "decisionRule": "the shoulder protrusion belongs to the slot whose hidden map removes it",
    "mutatedProductionAssets": [],
    "productionReady": False
}
REPORT.parent.mkdir(parents=True, exist_ok=False)
REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
unreal.SystemLibrary.quit_editor()
