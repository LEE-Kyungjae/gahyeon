"""Build Diana v392 with backdrop creation preceding the final map save."""

import json
from pathlib import Path
import unreal

ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
SOURCE_MAP = "/Game/Gahyeon/Character2/Diana/v388/Runtime/L_DianaMacRuntimeIdle_v388"
OUTPUT_MAP = "/Game/Gahyeon/Character2/Diana/v392/Runtime/L_DianaMacRuntimeIdleGreen_v392"
SOURCE_MATERIAL = "/Game/Gahyeon/Character2/Diana/v391/Materials/M_DesktopGreenScreen_v391"
MATERIAL = "/Game/Gahyeon/Character2/Diana/v392/Materials/M_DesktopGreenScreen_v392"
REPORT = ROOT / "artifacts/gahyeon-ch/iterations/v392-diana-macos-green-screen-runtime/report.json"

if unreal.EditorAssetLibrary.does_asset_exist(OUTPUT_MAP) or REPORT.exists():
    raise RuntimeError("refusing to overwrite immutable Diana v392 runtime")
unreal.EditorLoadingAndSavingUtils.load_map(SOURCE_MAP)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
character = next(actor for actor in actors.get_all_level_actors() if isinstance(actor, unreal.SkeletalMeshActor))
origin, _ = character.get_actor_bounds(False, True)

if not unreal.EditorAssetLibrary.duplicate_asset(SOURCE_MATERIAL, MATERIAL):
    raise RuntimeError("failed to duplicate v392 green material")
material = unreal.EditorAssetLibrary.load_asset(MATERIAL)
material.set_editor_property("two_sided", True)
unreal.EditorAssetLibrary.save_loaded_asset(material)

backdrop = actors.spawn_actor_from_class(
    unreal.StaticMeshActor,
    unreal.Vector(origin.x, origin.y - 160.0, origin.z),
    unreal.Rotator(),
)
if backdrop is None:
    raise RuntimeError("failed to spawn v392 backdrop")
backdrop.set_actor_label("BACKDROP_DesktopGreenCube_v392")
backdrop.set_actor_scale3d(unreal.Vector(20.0, 0.1, 20.0))
component = backdrop.get_component_by_class(unreal.StaticMeshComponent)
component.set_editor_property("static_mesh", unreal.EditorAssetLibrary.load_asset("/Engine/BasicShapes/Cube.Cube"))
component.set_material(0, material)

if world is None or not unreal.EditorLoadingAndSavingUtils.save_map(world, OUTPUT_MAP):
    raise RuntimeError("failed to save v392 map after backdrop creation")
report = {
    "schemaVersion": 1,
    "iteration": "v392",
    "status": "candidate-macos-green-screen-cube-runtime",
    "sourceMap": SOURCE_MAP,
    "map": OUTPUT_MAP,
    "backdropActor": "BACKDROP_DesktopGreenCube_v392",
    "expectedResult": "transparent desktop background with opaque dark character materials",
    "runtimeVisualValidationPending": True,
}
REPORT.parent.mkdir(parents=True, exist_ok=False)
REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
unreal.log("DIANA_MACOS_GREEN_SCREEN_RUNTIME_V392=" + json.dumps(report, sort_keys=True))
unreal.SystemLibrary.quit_editor()
