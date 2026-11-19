"""Build v397 with the exact v002 material set used by Diana's sharp v050 evidence."""

import json
from pathlib import Path
import unreal

ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
SOURCE_MAP = "/Game/Gahyeon/Character2/Diana/v379/Runtime/L_DianaMacRuntimePBR_v379"
OUTPUT_MAP = "/Game/Gahyeon/Character2/Diana/v397/Runtime/L_DianaMacRuntimeOriginalMaterialIdle_v397"
IDLE = "/Game/Gahyeon/Character2/Diana/v375/Animation/AS_Diana_Idle_v244_ComponentCopy_v375"
MATERIAL_ROOT = "/Game/Gahyeon/Character2/Diana/v002/Materials"
REPORT = ROOT / "artifacts/gahyeon-ch/iterations/v397-diana-original-material-idle/report.json"

if unreal.EditorAssetLibrary.does_asset_exist(OUTPUT_MAP) or REPORT.exists():
    raise RuntimeError("refusing to overwrite immutable Diana v397 runtime")
unreal.EditorLoadingAndSavingUtils.load_map(SOURCE_MAP)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
character = next(actor for actor in actors if isinstance(actor, unreal.SkeletalMeshActor))
camera = next(actor for actor in actors if isinstance(actor, unreal.CineCameraActor))
component = character.get_component_by_class(unreal.SkeletalMeshComponent)
materials = [unreal.EditorAssetLibrary.load_asset(f"{MATERIAL_ROOT}/M_Diana_Slot{i:02d}_v002") for i in range(18)]
if any(material is None for material in materials):
    raise RuntimeError("one or more original v002 materials are unavailable")
for index, material in enumerate(materials):
    component.set_material(index, material)
component.set_editor_property("forced_lod_model", 1)
idle = unreal.EditorAssetLibrary.load_asset(IDLE)
component.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
component.set_editor_property("animation_data", unreal.SingleAnimationPlayData(
    anim_to_play=idle, saved_looping=True, saved_playing=True,
    saved_position=0.0, saved_play_rate=1.0,
))
character.set_actor_label("Diana_Runtime_OriginalMaterial_Idle_v397")
camera.camera_component.set_editor_property("current_focal_length", 40.0)
camera.set_actor_label("CAM_Diana_Runtime_OriginalMaterial_Idle_v397")
if world is None or not unreal.EditorLoadingAndSavingUtils.save_map(world, OUTPUT_MAP):
    raise RuntimeError("failed to save Diana v397 runtime")

report = {
    "schemaVersion": 1,
    "iteration": "v397-diana-original-material-idle",
    "status": "candidate",
    "sourceMap": SOURCE_MAP,
    "map": OUTPUT_MAP,
    "materialRoot": MATERIAL_ROOT,
    "materialCount": len(materials),
    "visualReference": "v049/v050 Diana primary-chain renders",
    "animation": IDLE,
    "forcedLod": 0,
    "cameraFocalLengthMm": 40.0,
    "hypothesis": "The sharp original evidence came from v002 materials, not the later v377/v380 reconstructions.",
    "action": "Restore the exact 18-slot v002 material set while retaining approved idle, LOD0, lighting, and direct-alpha compatibility.",
    "expectedResult": "Match the original Diana color and detail instead of enlarging a reconstructed material result.",
    "actualResult": "Structurally validated; fixed-window visual validation pending.",
    "decision": "candidate; v393 retained as fallback and no automatic approval",
}
REPORT.parent.mkdir(parents=True, exist_ok=False)
REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
unreal.log("DIANA_ORIGINAL_MATERIAL_IDLE_V397=" + json.dumps(report, sort_keys=True))
unreal.SystemLibrary.quit_editor()
