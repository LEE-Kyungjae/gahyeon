"""Replace the rejected one-sided v390 plane with a guaranteed visible cube backdrop."""

import json
from pathlib import Path
import unreal

ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
SOURCE_MAP = "/Game/Gahyeon/Character2/Diana/v390/Runtime/L_DianaMacRuntimeIdleGreen_v390"
OUTPUT_MAP = "/Game/Gahyeon/Character2/Diana/v391/Runtime/L_DianaMacRuntimeIdleGreen_v391"
SOURCE_MATERIAL = "/Game/Gahyeon/Character2/Diana/v390/Materials/M_DesktopGreenScreen_v390"
MATERIAL = "/Game/Gahyeon/Character2/Diana/v391/Materials/M_DesktopGreenScreen_v391"
REPORT = ROOT / "artifacts/gahyeon-ch/iterations/v391-diana-macos-green-screen-runtime/report.json"

if unreal.EditorAssetLibrary.does_asset_exist(OUTPUT_MAP) or REPORT.exists():
    raise RuntimeError("refusing to overwrite immutable Diana v391 runtime")
unreal.EditorLoadingAndSavingUtils.load_map(SOURCE_MAP)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
if world is None or not unreal.EditorLoadingAndSavingUtils.save_map(world, OUTPUT_MAP):
    raise RuntimeError("failed to save v391 map copy")
if not unreal.EditorAssetLibrary.duplicate_asset(SOURCE_MATERIAL, MATERIAL):
    raise RuntimeError("failed to duplicate v391 green material")
material = unreal.EditorAssetLibrary.load_asset(MATERIAL)
material.set_editor_property("two_sided", True)
unreal.EditorAssetLibrary.save_loaded_asset(material)

actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
backdrops = [actor for actor in actors.get_all_level_actors() if actor.get_actor_label().startswith("BACKDROP_DesktopGreen")]
if len(backdrops) != 1:
    raise RuntimeError(f"expected one v390 backdrop, found {len(backdrops)}")
backdrop = backdrops[0]
backdrop.set_actor_label("BACKDROP_DesktopGreenCube_v391")
backdrop.set_actor_rotation(unreal.Rotator(), False)
backdrop.set_actor_scale3d(unreal.Vector(20.0, 0.1, 20.0))
component = backdrop.get_component_by_class(unreal.StaticMeshComponent)
cube = unreal.EditorAssetLibrary.load_asset("/Engine/BasicShapes/Cube.Cube")
component.set_editor_property("static_mesh", cube)
component.set_material(0, material)

if not unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True):
    raise RuntimeError("failed to save v391 runtime")
report = {
    "schemaVersion": 1,
    "iteration": "v391",
    "status": "candidate-macos-green-screen-cube-runtime",
    "sourceMap": SOURCE_MAP,
    "map": OUTPUT_MAP,
    "hypothesis": "a two-sided cube backdrop guarantees full-frame chroma coverage",
    "expectedResult": "transparent desktop background with opaque dark character materials",
    "runtimeVisualValidationPending": True,
}
REPORT.parent.mkdir(parents=True, exist_ok=False)
REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
unreal.log("DIANA_MACOS_GREEN_SCREEN_RUNTIME_V391=" + json.dumps(report, sort_keys=True))
unreal.SystemLibrary.quit_editor()
