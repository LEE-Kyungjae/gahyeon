"""Build v398 with a slightly wider camera so alpha-cropped desktop framing stays complete."""

import json
from pathlib import Path
import unreal

ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
SOURCE_MAP = "/Game/Gahyeon/Character2/Diana/v397/Runtime/L_DianaMacRuntimeOriginalMaterialIdle_v397"
OUTPUT_MAP = "/Game/Gahyeon/Character2/Diana/v398/Runtime/L_DianaMacRuntimeOriginalMaterialSafeFrame_v398"
REPORT = ROOT / "artifacts/gahyeon-ch/iterations/v398-diana-original-material-safe-frame/report.json"

if unreal.EditorAssetLibrary.does_asset_exist(OUTPUT_MAP) or REPORT.exists():
    raise RuntimeError("refusing to overwrite immutable Diana v398 runtime")
unreal.EditorLoadingAndSavingUtils.load_map(SOURCE_MAP)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
cameras = [actor for actor in actors if isinstance(actor, unreal.CineCameraActor)]
characters = [actor for actor in actors if isinstance(actor, unreal.SkeletalMeshActor)]
if world is None or len(cameras) != 1 or len(characters) != 1:
    raise RuntimeError("v397 composition changed unexpectedly")
cameras[0].camera_component.set_editor_property("current_focal_length", 36.0)
cameras[0].set_actor_label("CAM_Diana_OriginalMaterial_SafeFrame_v398")
if not unreal.EditorLoadingAndSavingUtils.save_map(world, OUTPUT_MAP):
    raise RuntimeError("failed to save v398 safe-frame map")

report = {
    "schemaVersion": 1,
    "iteration": "v398-diana-original-material-safe-frame",
    "status": "candidate",
    "sourceMap": SOURCE_MAP,
    "map": OUTPUT_MAP,
    "cameraFocalLengthMm": 36.0,
    "hypothesis": "At 40mm the feet touch the source-frame boundary, so alpha cropping cannot add safe pixels below them.",
    "action": "Widen only the camera to 36mm while retaining the v397 original materials, LOD0, lighting, and idle.",
    "expectedResult": "Full hair, right-side accessories, and both feet remain inside the alpha crop with UI adjacent to the compact window.",
    "actualResult": "Structurally validated; fixed-window visual validation pending.",
    "decision": "candidate; v397 and v393 retained as fallbacks",
}
REPORT.parent.mkdir(parents=True, exist_ok=False)
REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
unreal.log("DIANA_ORIGINAL_MATERIAL_SAFE_FRAME_V398=" + json.dumps(report, sort_keys=True))
unreal.SystemLibrary.quit_editor()
