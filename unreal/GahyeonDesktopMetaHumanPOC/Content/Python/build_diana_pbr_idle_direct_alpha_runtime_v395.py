"""Build Diana v395 from the original-PBR runtime with approved idle and full-body framing."""

import json
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
SOURCE_MAP = "/Game/Gahyeon/Character2/Diana/v379/Runtime/L_DianaMacRuntimePBR_v379"
OUTPUT_MAP = "/Game/Gahyeon/Character2/Diana/v395/Runtime/L_DianaMacRuntimePBRIdleDirectAlpha_v395"
IDLE = "/Game/Gahyeon/Character2/Diana/v375/Animation/AS_Diana_Idle_v244_ComponentCopy_v375"
REPORT = ROOT / "artifacts/gahyeon-ch/iterations/v395-diana-pbr-idle-direct-alpha/report.json"

if unreal.EditorAssetLibrary.does_asset_exist(OUTPUT_MAP) or REPORT.exists():
    raise RuntimeError("refusing to overwrite immutable Diana v395 runtime")
if not unreal.EditorAssetLibrary.duplicate_asset(SOURCE_MAP, OUTPUT_MAP):
    raise RuntimeError("failed to duplicate the v379 original-PBR runtime")

unreal.EditorLoadingAndSavingUtils.load_map(OUTPUT_MAP)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
characters = [actor for actor in actors if isinstance(actor, unreal.SkeletalMeshActor)]
cameras = [actor for actor in actors if isinstance(actor, unreal.CineCameraActor)]
if world is None or len(characters) != 1 or len(cameras) != 1:
    raise RuntimeError(f"unexpected v379 composition: characters={len(characters)} cameras={len(cameras)}")

idle = unreal.EditorAssetLibrary.load_asset(IDLE)
if idle is None:
    raise RuntimeError("approved v375 component-space idle is unavailable")

character = characters[0]
character.set_actor_label("Diana_Runtime_PBR_Idle_v395")
component = character.get_component_by_class(unreal.SkeletalMeshComponent)
component.set_editor_property("forced_lod_model", 1)
component.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
component.set_editor_property(
    "animation_data",
    unreal.SingleAnimationPlayData(
        anim_to_play=idle,
        saved_looping=True,
        saved_playing=True,
        saved_position=0.0,
        saved_play_rate=1.0,
    ),
)

camera = cameras[0]
camera.set_actor_label("CAM_Diana_Runtime_PBR_Idle_v395")
camera.camera_component.set_editor_property("current_focal_length", 40.0)

materials = [material.get_path_name() if material else None for material in component.get_materials()]
if len(materials) != 18 or not all("/v377/Materials/" in path for path in materials if path):
    raise RuntimeError("v395 did not inherit all 18 v377 original-PBR materials")
if not unreal.EditorLoadingAndSavingUtils.save_map(world, OUTPUT_MAP):
    raise RuntimeError("failed to save Diana v395 PBR idle runtime")

report = {
    "schemaVersion": 1,
    "iteration": "v395-diana-pbr-idle-direct-alpha",
    "status": "candidate",
    "sourceMap": SOURCE_MAP,
    "map": OUTPUT_MAP,
    "mesh": component.get_skeletal_mesh_asset().get_path_name(),
    "animation": IDLE,
    "materials": materials,
    "forcedLod": 0,
    "cameraFocalLengthMm": 40.0,
    "hypothesis": "Runtime softness came from the v380 source-color reconstruction and temporal filtering, while the original Diana PBR source remains detailed.",
    "action": "Combine the v379 original-PBR materials and lighting with the approved v375 idle, LOD0, and full-body 40mm framing.",
    "expectedResult": "Restore original face, hair, and clothing surface detail while preserving direct alpha and the validated animation attachment.",
    "actualResult": "Structurally validated; fixed-window visual and performance validation pending.",
    "decision": "candidate; v393 retained as fallback and no automatic approval",
}
REPORT.parent.mkdir(parents=True, exist_ok=False)
REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
unreal.log("DIANA_PBR_IDLE_DIRECT_ALPHA_V395=" + json.dumps(report, sort_keys=True))
unreal.SystemLibrary.quit_editor()
