"""Build an immutable Looking Glass candidate with a grounded matte floor."""

import json
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
SOURCE_MAP = "/Game/Gahyeon/Character2/Diana/v398/Runtime/L_DianaMacRuntimeOriginalMaterialSafeFrame_v398"
OUTPUT_MAP = "/Game/Gahyeon/Character2/Diana/v449/Runtime/L_DianaLookingGlassFloor_v449"
MATERIAL = "/Game/Gahyeon/Character2/Diana/v449/Materials/M_LookingGlassFloor_v449"
REPORT = ROOT / "artifacts/gahyeon-ch/iterations/v449-diana-looking-glass-floor/report.json"


if unreal.EditorAssetLibrary.does_asset_exist(OUTPUT_MAP) or REPORT.exists():
    raise RuntimeError("refusing to overwrite immutable Diana v449 Looking Glass runtime")

unreal.EditorLoadingAndSavingUtils.load_map(SOURCE_MAP)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
actors = actor_subsystem.get_all_level_actors()
characters = [actor for actor in actors if isinstance(actor, unreal.SkeletalMeshActor)]
if world is None or len(characters) != 1:
    raise RuntimeError("v398 character composition changed unexpectedly")

character = characters[0]
origin, extent = character.get_actor_bounds(False, True)
floor_z = origin.z - extent.z + 0.5

tools = unreal.AssetToolsHelpers.get_asset_tools()
material = tools.create_asset(
    "M_LookingGlassFloor_v449",
    "/Game/Gahyeon/Character2/Diana/v449/Materials",
    unreal.Material,
    unreal.MaterialFactoryNew(),
)
if material is None:
    raise RuntimeError("failed to create v449 floor material")

base_color = unreal.MaterialEditingLibrary.create_material_expression(
    material, unreal.MaterialExpressionConstant3Vector, -220, -40
)
base_color.set_editor_property("constant", unreal.LinearColor(0.105, 0.125, 0.155, 1.0))
roughness = unreal.MaterialEditingLibrary.create_material_expression(
    material, unreal.MaterialExpressionConstant, -220, 60
)
roughness.set_editor_property("r", 0.82)
specular = unreal.MaterialEditingLibrary.create_material_expression(
    material, unreal.MaterialExpressionConstant, -220, 140
)
specular.set_editor_property("r", 0.22)
unreal.MaterialEditingLibrary.connect_material_property(
    base_color, "", unreal.MaterialProperty.MP_BASE_COLOR
)
unreal.MaterialEditingLibrary.connect_material_property(
    roughness, "", unreal.MaterialProperty.MP_ROUGHNESS
)
unreal.MaterialEditingLibrary.connect_material_property(
    specular, "", unreal.MaterialProperty.MP_SPECULAR
)
unreal.MaterialEditingLibrary.recompile_material(material)
unreal.EditorAssetLibrary.save_loaded_asset(material)

plane = unreal.EditorAssetLibrary.load_asset("/Engine/BasicShapes/Plane.Plane")
if plane is None:
    raise RuntimeError("engine plane mesh unavailable")
floor = actor_subsystem.spawn_actor_from_class(
    unreal.StaticMeshActor,
    unreal.Vector(origin.x, origin.y, floor_z),
    unreal.Rotator(),
)
if floor is None:
    raise RuntimeError("failed to spawn Looking Glass floor")
floor.set_actor_label("FLOOR_Diana_LookingGlass_v449")
floor.set_actor_scale3d(unreal.Vector(12.0, 12.0, 12.0))
floor_component = floor.get_component_by_class(unreal.StaticMeshComponent)
floor_component.set_editor_property("static_mesh", plane)
floor_component.set_material(0, material)
floor_component.set_editor_property("cast_shadow", True)

if not unreal.EditorLoadingAndSavingUtils.save_map(world, OUTPUT_MAP):
    raise RuntimeError("failed to save Diana v449 Looking Glass floor map")

report = {
    "schemaVersion": 1,
    "iteration": "v449-diana-looking-glass-floor",
    "status": "candidate",
    "sourceMap": SOURCE_MAP,
    "map": OUTPUT_MAP,
    "hypothesis": "a matte physical floor supplies contact, shadow, and parallax cues without competing with the character",
    "action": "add a 12m cool-neutral rough floor at the measured character foot plane",
    "expectedResult": "stronger grounding and depth readability in the Looking Glass while preserving Diana framing and materials",
    "actualResult": "structurally authored; physical-display review pending",
    "decision": "candidate; v398 remains the canonical desktop fallback",
    "floor": {
        "z": floor_z,
        "scaleMeters": 12.0,
        "baseColorLinear": [0.105, 0.125, 0.155],
        "roughness": 0.82,
        "specular": 0.22,
    },
}
REPORT.parent.mkdir(parents=True, exist_ok=False)
REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
unreal.log("DIANA_LOOKING_GLASS_FLOOR_V449=" + json.dumps(report, sort_keys=True))
unreal.SystemLibrary.quit_editor()
