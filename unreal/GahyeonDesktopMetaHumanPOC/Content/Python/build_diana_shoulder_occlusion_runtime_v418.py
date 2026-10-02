"""Build Diana's shoulder-occluded runtime from the safely imported v417 mesh."""

import json
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
SOURCE_MAP = "/Game/Gahyeon/Character2/Diana/v410/Runtime/L_DianaMacRuntimeHighKeyClearance_v410"
MESH = "/Game/Gahyeon/Character2/Diana/v417/Source/SK_Diana_ShoulderOccluded_v417"
OUTPUT_MAP = "/Game/Gahyeon/Character2/Diana/v418/Runtime/L_DianaMacRuntimeShoulderOccluded_v418"
REPORT = ROOT / "artifacts/gahyeon-ch/iterations/v418-diana-shoulder-occlusion-runtime/report.json"

if REPORT.exists() or unreal.EditorAssetLibrary.does_asset_exist(OUTPUT_MAP):
    raise RuntimeError("refusing to overwrite immutable Diana v418 outputs")
mesh = unreal.load_asset(MESH)
if mesh is None:
    raise RuntimeError(f"v417 mesh unavailable: {MESH}")
unreal.EditorLoadingAndSavingUtils.load_map(SOURCE_MAP)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
characters = [actor for actor in actors if isinstance(actor, unreal.SkeletalMeshActor)]
if world is None or len(characters) != 1:
    raise RuntimeError("v410 character composition changed unexpectedly")
component = characters[0].get_component_by_class(unreal.SkeletalMeshComponent)
component.set_editor_property("skeletal_mesh_asset", mesh)
characters[0].set_actor_label("Diana_ShoulderOccluded_v418")
if not unreal.EditorLoadingAndSavingUtils.save_map(world, OUTPUT_MAP):
    raise RuntimeError("failed to save v418 runtime")

report = {
    "schemaVersion": 1,
    "iteration": "v418-diana-shoulder-occlusion-runtime",
    "status": "candidate",
    "sourceMap": SOURCE_MAP,
    "map": OUTPUT_MAP,
    "mesh": MESH,
    "geometryIteration": "v417",
    "method": "occlude arm skin beneath jacket sleeves; preserve wrist and hand geometry",
    "humanApproved": False,
    "productionReady": False,
}
REPORT.parent.mkdir(parents=True, exist_ok=False)
REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
unreal.SystemLibrary.quit_editor()
