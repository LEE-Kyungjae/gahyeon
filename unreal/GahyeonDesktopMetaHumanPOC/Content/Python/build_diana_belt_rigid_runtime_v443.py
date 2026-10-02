"""Build Diana's rigid-Hip belt attachment runtime from the imported v441 mesh."""

import json
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
SOURCE_MAP = "/Game/Gahyeon/Character2/Diana/v421/Runtime/L_DianaMacRuntimeAttachmentGravity_v421"
MESH = "/Game/Gahyeon/Character2/Diana/v441/Source/SK_Diana_BeltAttachmentRigidHip_v440"
OUTPUT_MAP = "/Game/Gahyeon/Character2/Diana/v443/Runtime/L_DianaMacRuntimeBeltRigidHip_v443"
REPORT = ROOT / "artifacts/gahyeon-ch/iterations/v443-diana-belt-rigid-hip-runtime/report.json"

if REPORT.exists() or unreal.EditorAssetLibrary.does_asset_exist(OUTPUT_MAP):
    raise RuntimeError("refusing to overwrite immutable Diana v443 outputs")
mesh = unreal.load_asset(MESH)
if mesh is None:
    raise RuntimeError(f"v441 mesh unavailable: {MESH}")
if not unreal.EditorLoadingAndSavingUtils.load_map(SOURCE_MAP):
    raise RuntimeError(f"retained runtime unavailable: {SOURCE_MAP}")
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
characters = [actor for actor in actors if isinstance(actor, unreal.SkeletalMeshActor)]
if world is None or len(characters) != 1:
    raise RuntimeError("retained runtime character composition changed unexpectedly")
component = characters[0].get_component_by_class(unreal.SkeletalMeshComponent)
component.set_editor_property("skeletal_mesh_asset", mesh)
characters[0].set_actor_label("Diana_BeltRigidHip_v443")
if not unreal.EditorLoadingAndSavingUtils.save_map(world, OUTPUT_MAP):
    raise RuntimeError("failed to save Diana v443 runtime")

report = {
    "schemaVersion": 1,
    "iteration": "v443-diana-belt-rigid-hip-runtime",
    "status": "draft-runtime-visual-validation-required",
    "sourceMap": SOURCE_MAP,
    "map": OUTPUT_MAP,
    "mesh": MESH,
    "method": "rigidly reweight waist NeoBelt/weapon islands to Hip while preserving the retained animation and transparent runtime",
    "expectedResult": "belt weapons retain their hanging bind orientation instead of rotating horizontally with thigh/twist bones",
    "humanApproved": False,
    "productionReady": False,
}
REPORT.parent.mkdir(parents=True, exist_ok=False)
REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
unreal.log("DIANA_BELT_RIGID_RUNTIME_V443=" + json.dumps(report, sort_keys=True))
unreal.SystemLibrary.quit_editor()
