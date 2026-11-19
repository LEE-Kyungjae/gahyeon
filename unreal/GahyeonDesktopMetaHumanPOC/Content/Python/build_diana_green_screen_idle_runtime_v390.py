"""Build an immutable green-screen Diana runtime for lossless macOS alpha keying."""

import json
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
SOURCE_MAP = "/Game/Gahyeon/Character2/Diana/v388/Runtime/L_DianaMacRuntimeIdle_v388"
OUTPUT_MAP = "/Game/Gahyeon/Character2/Diana/v390/Runtime/L_DianaMacRuntimeIdleGreen_v390"
MATERIAL = "/Game/Gahyeon/Character2/Diana/v390/Materials/M_DesktopGreenScreen_v390"
REPORT = ROOT / "artifacts/gahyeon-ch/iterations/v390-diana-macos-green-screen-runtime/report.json"


if unreal.EditorAssetLibrary.does_asset_exist(OUTPUT_MAP) or REPORT.exists():
    raise RuntimeError("refusing to overwrite immutable Diana v390 runtime")
unreal.EditorLoadingAndSavingUtils.load_map(SOURCE_MAP)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
if world is None or not unreal.EditorLoadingAndSavingUtils.save_map(world, OUTPUT_MAP):
    raise RuntimeError(f"failed to save immutable copy {OUTPUT_MAP}")
asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
material = unreal.EditorAssetLibrary.load_asset(MATERIAL)
if material is None:
    material = asset_tools.create_asset(
        "M_DesktopGreenScreen_v390",
        "/Game/Gahyeon/Character2/Diana/v390/Materials",
        unreal.Material,
        unreal.MaterialFactoryNew(),
    )
    if material is None:
        raise RuntimeError("failed to create green-screen material")
    material.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    color = unreal.MaterialEditingLibrary.create_material_expression(
        material, unreal.MaterialExpressionConstant3Vector, -180, 0
    )
    color.set_editor_property("constant", unreal.LinearColor(0.0, 1.0, 0.0, 1.0))
    unreal.MaterialEditingLibrary.connect_material_property(
        color, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR
    )
    unreal.MaterialEditingLibrary.recompile_material(material)
    unreal.EditorAssetLibrary.save_loaded_asset(material)

actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
character = next(
    actor for actor in actors.get_all_level_actors() if isinstance(actor, unreal.SkeletalMeshActor)
)
origin, extent = character.get_actor_bounds(False, True)
backdrop = actors.spawn_actor_from_class(
    unreal.StaticMeshActor,
    unreal.Vector(origin.x, origin.y - 160.0, origin.z),
    unreal.Rotator(90.0, 0.0, 0.0),
)
if backdrop is None:
    raise RuntimeError("failed to spawn green-screen backdrop")
backdrop.set_actor_label("BACKDROP_DesktopGreen_v390")
backdrop.set_actor_scale3d(unreal.Vector(20.0, 20.0, 20.0))
component = backdrop.get_component_by_class(unreal.StaticMeshComponent)
plane = unreal.EditorAssetLibrary.load_asset("/Engine/BasicShapes/Plane.Plane")
if plane is None:
    raise RuntimeError("engine plane mesh unavailable")
component.set_editor_property("static_mesh", plane)
component.set_material(0, material)

if not unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True):
    raise RuntimeError("failed to save v390 green-screen runtime")

report = {
    "schemaVersion": 1,
    "iteration": "v390",
    "status": "candidate-macos-green-screen-idle-runtime",
    "sourceMap": SOURCE_MAP,
    "map": OUTPUT_MAP,
    "characterPreserved": True,
    "animationPreserved": True,
    "hypothesis": "a saturated green backdrop allows color-distance alpha keying without deleting dark body materials",
    "expectedResult": "opaque dark costume/body pixels and higher fidelity native-resolution capture",
    "runtimeVisualValidationPending": True,
}
REPORT.parent.mkdir(parents=True, exist_ok=False)
REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
unreal.log("DIANA_MACOS_GREEN_SCREEN_RUNTIME_V390=" + json.dumps(report, sort_keys=True))
unreal.SystemLibrary.quit_editor()
