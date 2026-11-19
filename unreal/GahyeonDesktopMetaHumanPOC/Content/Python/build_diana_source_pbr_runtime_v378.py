"""Import Diana's supplied textures and build an immutable high-detail runtime."""

import json
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
SOURCE = ROOT / "artifacts/gahyeon-ch/iterations/v377-diana-source-pbr/source-textures"
TEXTURE_ROOT = "/Game/Gahyeon/Character2/Diana/v377/Textures"
MATERIAL_ROOT = "/Game/Gahyeon/Character2/Diana/v377/Materials"
SOURCE_MAP = "/Game/Gahyeon/Character2/Diana/v376/Runtime/L_DianaMacRuntime_v376"
TARGET_MAP = "/Game/Gahyeon/Character2/Diana/v378/Runtime/L_DianaMacRuntimePBR_v378"
REPORT = ROOT / "artifacts/gahyeon-ch/iterations/v378-diana-source-pbr-runtime/report.json"

SLOTS = [
    ("Face", "ch0100_10_Head_Face_ALBD", "ch0100_10_Head_Face_NRMR", False),
    ("Tooth", None, None, False),
    ("EyeLeft", "iris_type1_ALB", None, False),
    ("EyeRight", "iris_type1_ALB", None, False),
    ("EyeShell", None, None, False),
    ("Eyebrows", "ch0100_10_Head_Eyebrows_ALBD", None, True),
    ("Eyelash", "ch0100_10_Head_Eyelash_ALBD", None, True),
    ("EyelashLower", "ch0100_10_Head_Eyelash_lower_ALBD", None, True),
    ("Hair", "ch0100_20_DHair_ALBA", None, True),
    ("Jacket1", "ch0100_40_NeoJacket1_ALBD", "ch0100_40_NeoJacket1_NRMR", False),
    ("Leg", "ch0100_00_Body_Leg_ALBD", "ch0100_00_Body_Leg_NRMR", False),
    ("Body", "ch0100_00_Body_Leg_ALBD", "ch0100_00_Body_Leg_NRMR", False),
    ("Hand", "ch0100_00_Body_Hand_ALBD", "ch0100_00_Body_Hand_NRMR", False),
    ("Jacket2", "ch0100_40_NeoJacket2_ALBD", "ch0100_40_NeoJacket2_NRMR", False),
    ("Belt", "ch0100_40_Belt_ALBD", "ch0100_40_Belt_NRMR", False),
    ("Emissive", None, None, False),
    ("EmissiveNeck", None, None, False),
    ("Reflector", None, None, False),
]


def require(path):
    value = unreal.EditorAssetLibrary.load_asset(path)
    if value is None:
        raise RuntimeError(f"required asset unavailable: {path}")
    return value


def add_constant(material, value, prop, x, y):
    expression = unreal.MaterialEditingLibrary.create_material_expression(
        material, unreal.MaterialExpressionConstant, x, y
    )
    expression.set_editor_property("r", value)
    if not unreal.MaterialEditingLibrary.connect_material_property(expression, "", prop):
        raise RuntimeError(f"failed to connect {prop}")


if unreal.EditorAssetLibrary.does_asset_exist(TARGET_MAP) or REPORT.exists():
    raise RuntimeError("refusing to overwrite immutable Diana v378 runtime")
if not SOURCE.is_dir():
    raise RuntimeError(f"Diana source texture directory missing: {SOURCE}")

texture_files = sorted(str(path) for path in SOURCE.glob("*.png"))
if len(texture_files) != 19:
    raise RuntimeError(f"expected 19 supplied Diana textures, found {len(texture_files)}")
import_data = unreal.AutomatedAssetImportData()
import_data.set_editor_property("destination_path", TEXTURE_ROOT)
import_data.set_editor_property("filenames", texture_files)
import_data.set_editor_property("replace_existing", False)
import_data.set_editor_property("skip_read_only", True)
imported_raw = unreal.AssetToolsHelpers.get_asset_tools().import_assets_automated(import_data)
imported_by_name = {texture.get_name(): texture for texture in imported_raw}
imported = list(imported_by_name.values())
if len(imported) != len(texture_files):
    raise RuntimeError(
        f"expected {len(texture_files)} unique imported textures, got {len(imported)} "
        f"from {len(imported_raw)} importer results"
    )

for texture in imported:
    name = texture.get_name()
    texture.set_editor_property("never_stream", True)
    if name.endswith("_NRMR"):
        texture.set_editor_property("srgb", False)
        texture.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
    unreal.EditorAssetLibrary.save_loaded_asset(texture, only_if_is_dirty=False)

asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
materials = []
for index, (label, albedo_name, normal_name, masked) in enumerate(SLOTS):
    name = f"M_Diana_{index:02d}_{label}_PBR_v377"
    path = f"{MATERIAL_ROOT}/{name}"
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        raise RuntimeError(f"refusing to overwrite material: {path}")
    material = asset_tools.create_asset(name, MATERIAL_ROOT, unreal.Material, unreal.MaterialFactoryNew())
    if material is None:
        raise RuntimeError(f"failed to create {path}")
    if masked:
        material.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED)
        material.set_editor_property("two_sided", True)
        material.set_editor_property("opacity_mask_clip_value", 0.22)
    if albedo_name:
        sample = unreal.MaterialEditingLibrary.create_material_expression(
            material, unreal.MaterialExpressionTextureSample, -520, -80
        )
        sample.set_editor_property("texture", require(f"{TEXTURE_ROOT}/{albedo_name}"))
        unreal.MaterialEditingLibrary.connect_material_property(
            sample, "RGB", unreal.MaterialProperty.MP_BASE_COLOR
        )
        if masked:
            unreal.MaterialEditingLibrary.connect_material_property(
                sample, "A", unreal.MaterialProperty.MP_OPACITY_MASK
            )
    else:
        color = unreal.LinearColor(0.9, 0.9, 0.9, 1.0)
        if label.startswith("Emissive"):
            color = unreal.LinearColor(0.08, 0.3, 1.0, 1.0)
        vector = unreal.MaterialEditingLibrary.create_material_expression(
            material, unreal.MaterialExpressionConstant3Vector, -520, -80
        )
        vector.set_editor_property("constant", color)
        unreal.MaterialEditingLibrary.connect_material_property(
            vector, "", unreal.MaterialProperty.MP_BASE_COLOR
        )
    if normal_name:
        normal = unreal.MaterialEditingLibrary.create_material_expression(
            material, unreal.MaterialExpressionTextureSample, -520, 80
        )
        normal.set_editor_property("texture", require(f"{TEXTURE_ROOT}/{normal_name}"))
        unreal.MaterialEditingLibrary.connect_material_property(
            normal, "RGB", unreal.MaterialProperty.MP_NORMAL
        )
    add_constant(material, 0.48 if label == "Face" else 0.58, unreal.MaterialProperty.MP_ROUGHNESS, -520, 220)
    unreal.MaterialEditingLibrary.recompile_material(material)
    unreal.EditorAssetLibrary.save_loaded_asset(material, only_if_is_dirty=False)
    materials.append(material)

if unreal.EditorAssetLibrary.duplicate_asset(SOURCE_MAP, TARGET_MAP) is None:
    raise RuntimeError("failed to duplicate v376 runtime map")
unreal.EditorLevelLibrary.load_level(TARGET_MAP)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
character = next((actor for actor in actors if actor.get_actor_label() == "Diana_Runtime_v376"), None)
camera = next((actor for actor in actors if actor.get_actor_label() == "CAM_Diana_Runtime_v376"), None)
if character is None or camera is None:
    raise RuntimeError("v376 character or camera actor missing")
character.set_actor_label("Diana_Runtime_PBR_v378")
component = character.get_component_by_class(unreal.SkeletalMeshComponent)
for index, material in enumerate(materials):
    component.set_material(index, material)
origin, extent = character.get_actor_bounds(False, True)
target = unreal.Vector(origin.x, origin.y, origin.z + 3.0)
camera.set_actor_label("CAM_Diana_Runtime_PBR_v378")
camera.set_actor_location(target + unreal.Vector(0.0, 315.0, 3.0), False, False)
camera.set_actor_rotation(unreal.MathLibrary.find_look_at_rotation(camera.get_actor_location(), target), False)
camera.camera_component.set_editor_property("current_focal_length", 58.0)
camera.camera_component.set_editor_property("current_aperture", 8.0)
if not unreal.EditorLevelLibrary.save_current_level():
    raise RuntimeError("failed to save Diana v378 runtime map")

report = {
    "schemaVersion": 1,
    "iteration": "v378",
    "status": "candidate-source-pbr-runtime",
    "map": TARGET_MAP,
    "sourceArchive": "/Users/ze/Downloads/pragmata-diana-textured-and-rigged.zip",
    "textureCount": len(imported),
    "materialCount": len(materials),
    "sourceTextureMaximum": [2048, 2048],
    "animationApprovalInherited": "v375",
    "transparentDesktopOverlayPending": True,
    "runtimeVisualValidationPending": True,
    "productionReady": False,
}
REPORT.parent.mkdir(parents=True, exist_ok=False)
REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
unreal.log("DIANA_SOURCE_PBR_RUNTIME_V378=" + json.dumps(report, sort_keys=True))
unreal.SystemLibrary.quit_editor()
