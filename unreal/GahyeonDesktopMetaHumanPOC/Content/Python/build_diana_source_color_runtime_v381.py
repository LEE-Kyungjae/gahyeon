"""Build Diana source-color materials with explicit RGB reconstruction and a runtime map."""

import json
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
TEXTURE_ROOT = "/Game/Gahyeon/Character2/Diana/v377/Textures"
MATERIAL_ROOT = "/Game/Gahyeon/Character2/Diana/v380/Materials"
MAP = "/Game/Gahyeon/Character2/Diana/v381/Runtime/L_DianaMacRuntimeSourceColor_v381"
MESH = "/Game/Gahyeon/Character2/Diana/v024/Source/SK_Diana_CM_v024"
ANIMATION = "/Game/Gahyeon/Character2/Diana/v375/Animation/AS_Diana_RunForward_v244_ComponentCopy_v375"
REPORT = ROOT / "artifacts/gahyeon-ch/iterations/v381-diana-source-color-runtime/report.json"

SLOTS = [
    ("Face", "ch0100_10_Head_Face_ALBD", False, (0.82, 0.62, 0.56)),
    ("Tooth", None, False, (0.82, 0.82, 0.78)),
    ("EyeLeft", "iris_type1_ALB", False, (0.15, 0.15, 0.13)),
    ("EyeRight", "iris_type1_ALB", False, (0.15, 0.15, 0.13)),
    ("EyeShell", None, False, (0.12, 0.12, 0.12)),
    ("Eyebrows", "ch0100_10_Head_Eyebrows_ALBD", True, (0.08, 0.06, 0.04)),
    ("Eyelash", "ch0100_10_Head_Eyelash_ALBD", True, (0.03, 0.02, 0.02)),
    ("EyelashLower", "ch0100_10_Head_Eyelash_lower_ALBD", True, (0.03, 0.02, 0.02)),
    ("Hair", "ch0100_20_DHair_ALBA", True, (0.35, 0.29, 0.12)),
    ("Jacket1", "ch0100_40_NeoJacket1_ALBD", False, (0.03, 0.15, 0.8)),
    ("Leg", "ch0100_00_Body_Leg_ALBD", False, (0.72, 0.52, 0.46)),
    ("Body", "ch0100_00_Body_Leg_ALBD", False, (0.72, 0.52, 0.46)),
    ("Hand", "ch0100_00_Body_Hand_ALBD", False, (0.72, 0.52, 0.46)),
    ("Jacket2", "ch0100_40_NeoJacket2_ALBD", False, (0.03, 0.12, 0.65)),
    ("Belt", "ch0100_40_Belt_ALBD", False, (0.08, 0.08, 0.1)),
    ("Emissive", None, False, (0.05, 0.3, 1.0)),
    ("EmissiveNeck", None, False, (0.05, 0.3, 1.0)),
    ("Reflector", None, False, (0.65, 0.72, 0.8)),
]


def require(path):
    value = unreal.EditorAssetLibrary.load_asset(path)
    if value is None:
        raise RuntimeError(f"required asset unavailable: {path}")
    return value


def explicit_rgb(material, sample):
    rg = unreal.MaterialEditingLibrary.create_material_expression(
        material, unreal.MaterialExpressionAppendVector, -270, -60
    )
    rgb = unreal.MaterialEditingLibrary.create_material_expression(
        material, unreal.MaterialExpressionAppendVector, -80, -60
    )
    if not unreal.MaterialEditingLibrary.connect_material_expressions(sample, "R", rg, "A"):
        raise RuntimeError("failed to connect red channel")
    if not unreal.MaterialEditingLibrary.connect_material_expressions(sample, "G", rg, "B"):
        raise RuntimeError("failed to connect green channel")
    if not unreal.MaterialEditingLibrary.connect_material_expressions(rg, "", rgb, "A"):
        raise RuntimeError("failed to connect red-green vector")
    if not unreal.MaterialEditingLibrary.connect_material_expressions(sample, "B", rgb, "B"):
        raise RuntimeError("failed to connect blue channel")
    return rgb


if unreal.EditorAssetLibrary.does_asset_exist(MAP) or REPORT.exists():
    raise RuntimeError("refusing to overwrite immutable Diana v381 runtime")
materials = []
tools = unreal.AssetToolsHelpers.get_asset_tools()
for index, (label, texture_name, masked, fallback) in enumerate(SLOTS):
    name = f"M_Diana_{index:02d}_{label}_SourceColor_v380"
    path = f"{MATERIAL_ROOT}/{name}"
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        raise RuntimeError(f"refusing to overwrite {path}")
    material = tools.create_asset(name, MATERIAL_ROOT, unreal.Material, unreal.MaterialFactoryNew())
    material.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    if masked:
        material.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED)
        material.set_editor_property("two_sided", True)
        material.set_editor_property("opacity_mask_clip_value", 0.18)
    if texture_name:
        sample = unreal.MaterialEditingLibrary.create_material_expression(
            material, unreal.MaterialExpressionTextureSample, -500, -60
        )
        sample.set_editor_property("texture", require(f"{TEXTURE_ROOT}/{texture_name}"))
        rgb = explicit_rgb(material, sample)
        if not unreal.MaterialEditingLibrary.connect_material_property(
            rgb, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR
        ):
            raise RuntimeError(f"failed to connect reconstructed RGB for {label}")
        if masked and not unreal.MaterialEditingLibrary.connect_material_property(
            sample, "A", unreal.MaterialProperty.MP_OPACITY_MASK
        ):
            raise RuntimeError(f"failed to connect opacity for {label}")
    else:
        color = unreal.MaterialEditingLibrary.create_material_expression(
            material, unreal.MaterialExpressionConstant3Vector, -300, -60
        )
        color.set_editor_property("constant", unreal.LinearColor(*fallback, 1.0))
        unreal.MaterialEditingLibrary.connect_material_property(
            color, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR
        )
    unreal.MaterialEditingLibrary.recompile_material(material)
    unreal.EditorAssetLibrary.save_loaded_asset(material, only_if_is_dirty=False)
    materials.append(material)

mesh = require(MESH)
animation = require(ANIMATION)
if not unreal.EditorLevelLibrary.new_level(MAP):
    raise RuntimeError("failed to create Diana v381 runtime map")
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
character = actors.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector())
character.set_actor_label("Diana_Runtime_SourceColor_v381")
component = character.get_component_by_class(unreal.SkeletalMeshComponent)
component.set_editor_property("skeletal_mesh_asset", mesh)
for index, material in enumerate(materials):
    component.set_material(index, material)
component.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
component.set_editor_property(
    "animation_data",
    unreal.SingleAnimationPlayData(
        anim_to_play=animation, saved_looping=True, saved_playing=True,
        saved_position=0.0, saved_play_rate=1.0,
    ),
)

origin, extent = character.get_actor_bounds(False, True)
target = unreal.Vector(origin.x, origin.y, origin.z + 2.0)
camera_location = target + unreal.Vector(0.0, 345.0, 3.0)
camera = actors.spawn_actor_from_class(
    unreal.CineCameraActor, camera_location,
    unreal.MathLibrary.find_look_at_rotation(camera_location, target),
)
camera.set_actor_label("CAM_Diana_Runtime_SourceColor_v381")
camera.set_editor_property("auto_activate_for_player", unreal.AutoReceiveInput.PLAYER0)
camera.camera_component.set_editor_property("current_focal_length", 52.0)
camera.camera_component.set_editor_property("current_aperture", 8.0)
actors.spawn_actor_from_class(
    unreal.PlayerStart, unreal.Vector(2000.0, 2000.0, 1000.0), unreal.Rotator()
)
post = actors.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector())
post.set_editor_property("unbound", True)
settings = post.get_editor_property("settings")
settings.set_editor_property("override_motion_blur_amount", True)
settings.set_editor_property("motion_blur_amount", 0.0)
post.set_editor_property("settings", settings)
if not unreal.EditorLevelLibrary.save_current_level():
    raise RuntimeError("failed to save Diana v381 map")

report = {
    "schemaVersion": 1, "iteration": "v381",
    "status": "candidate-source-color-macos-runtime", "map": MAP,
    "mesh": MESH, "animation": ANIMATION, "materialIteration": "v380",
    "sourceTextureCount": 19, "sourceTextureMaximum": [2048, 2048],
    "explicitRgbReconstruction": True, "lightingIndependent": True,
    "humanAnimationApprovalInherited": True,
    "transparentDesktopOverlayPending": True,
    "runtimeVisualValidationPending": True, "productionReady": False,
}
REPORT.parent.mkdir(parents=True, exist_ok=False)
REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
unreal.log("DIANA_SOURCE_COLOR_RUNTIME_V381=" + json.dumps(report, sort_keys=True))
unreal.SystemLibrary.quit_editor()
