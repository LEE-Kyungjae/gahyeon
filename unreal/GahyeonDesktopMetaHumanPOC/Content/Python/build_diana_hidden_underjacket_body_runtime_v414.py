"""Hide Diana's covered torso/shoulder body shell so it cannot pierce the jacket."""

import json
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
SOURCE_MAP = "/Game/Gahyeon/Character2/Diana/v410/Runtime/L_DianaMacRuntimeHighKeyClearance_v410"
OUTPUT_MAP = "/Game/Gahyeon/Character2/Diana/v414/Runtime/L_DianaMacRuntimeHiddenUnderJacketBody_v414"
MATERIAL_PATH = "/Game/Gahyeon/Character2/Diana/v414/Materials/M_Diana_UnderJacket_Invisible_v414"
REPORT = ROOT / "artifacts/gahyeon-ch/iterations/v414-diana-hidden-underjacket-body-runtime/report.json"
BODY_SLOT = 11

if (unreal.EditorAssetLibrary.does_asset_exist(OUTPUT_MAP)
        or unreal.EditorAssetLibrary.does_asset_exist(MATERIAL_PATH)
        or REPORT.exists()):
    raise RuntimeError("refusing to overwrite immutable Diana v414 assets")

factory = unreal.MaterialFactoryNew()
material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
    "M_Diana_UnderJacket_Invisible_v414",
    "/Game/Gahyeon/Character2/Diana/v414/Materials",
    unreal.Material,
    factory,
)
if material is None:
    raise RuntimeError("failed to create under-jacket masking material")
material.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
material.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
material.set_editor_property("two_sided", True)
opacity = unreal.MaterialEditingLibrary.create_material_expression(
    material, unreal.MaterialExpressionConstant, -220, 0
)
opacity.set_editor_property("r", 0.0)
unreal.MaterialEditingLibrary.connect_material_property(
    opacity, "", unreal.MaterialProperty.MP_OPACITY
)
unreal.MaterialEditingLibrary.recompile_material(material)
if not unreal.EditorAssetLibrary.save_loaded_asset(material, False):
    raise RuntimeError("failed to save under-jacket masking material")

unreal.EditorLoadingAndSavingUtils.load_map(SOURCE_MAP)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
characters = [actor for actor in actors if isinstance(actor, unreal.SkeletalMeshActor)]
if world is None or len(characters) != 1:
    raise RuntimeError("v410 character composition changed unexpectedly")
component = characters[0].get_component_by_class(unreal.SkeletalMeshComponent)
if component.get_num_materials() != 18:
    raise RuntimeError("Diana material slot count changed unexpectedly")
component.set_material(BODY_SLOT, material)
characters[0].set_actor_label("Diana_HiddenUnderJacketBody_v414")
if not unreal.EditorLoadingAndSavingUtils.save_map(world, OUTPUT_MAP):
    raise RuntimeError("failed to save Diana v414 runtime")

report = {
    "schemaVersion": 1,
    "iteration": "v414-diana-hidden-underjacket-body-runtime",
    "status": "candidate",
    "sourceMap": SOURCE_MAP,
    "map": OUTPUT_MAP,
    "finding": "material slot 11 contains only the covered upper torso/neck body shell; face, hands, and legs are separate slots",
    "action": "mask only slot 11 with a zero-opacity material so covered shoulder skin cannot render through the jacket",
    "bodySlot": BODY_SLOT,
    "maskMaterial": MATERIAL_PATH,
    "preservedOriginalMaterialSlots": 17,
    "preserved": ["face slot 0", "leg slot 10", "hand slot 12", "v408 hair clearance", "v409 reflections", "v410 brightness"],
    "expectedResult": "no shoulder/body breakthrough in idle or future body animations while exposed anatomy remains visible",
    "actualResult": "structurally validated; desktop neck continuity and shoulder silhouette review pending",
    "decision": "candidate; v410 and v398 retained as fallbacks",
    "humanApproved": False,
    "productionReady": False
}
REPORT.parent.mkdir(parents=True, exist_ok=False)
REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
unreal.log("DIANA_HIDDEN_UNDERJACKET_BODY_V414=" + json.dumps(report, sort_keys=True))
unreal.SystemLibrary.quit_editor()
