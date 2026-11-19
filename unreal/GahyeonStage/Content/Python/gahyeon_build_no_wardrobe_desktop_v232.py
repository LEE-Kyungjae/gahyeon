"""Create a no-wardrobe desktop map with the verified camera activated."""

import json
from pathlib import Path

import unreal


SOURCE_MAP = "/Game/Gahyeon/CharacterPipeline/v075/Preview/L_Skotukeda_WardrobeReset_v075"
TARGET_MAP = "/Game/Gahyeon/CharacterPipeline/v232/Preview/L_Skotukeda_NoWardrobeDesktop_v232"
CAMERA_LABEL = "CAM_Gahyeon_Desktop_v025b"
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v232-skotukeda-no-wardrobe-camera/build-receipt.json"
)


def build_no_wardrobe_desktop_v232():
    if OUTPUT.exists() or unreal.EditorAssetLibrary.does_asset_exist(TARGET_MAP):
        raise RuntimeError("refusing to overwrite immutable v232 output")
    world = unreal.EditorLoadingAndSavingUtils.load_map(SOURCE_MAP)
    if world is None:
        raise RuntimeError(f"failed to load source map: {SOURCE_MAP}")
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    cameras = [actor for actor in actors if isinstance(actor, unreal.CameraActor)]
    selected = next((actor for actor in cameras if actor.get_actor_label() == CAMERA_LABEL), None)
    if selected is None:
        raise RuntimeError(f"verified camera missing: {CAMERA_LABEL}")
    for camera in cameras:
        camera.set_editor_property(
            "auto_activate_for_player",
            unreal.AutoReceiveInput.PLAYER0 if camera == selected else unreal.AutoReceiveInput.DISABLED,
        )
    if not unreal.EditorLoadingAndSavingUtils.save_map(world, TARGET_MAP):
        raise RuntimeError(f"failed to save v232 map: {TARGET_MAP}")
    OUTPUT.parent.mkdir(parents=True, exist_ok=False)
    OUTPUT.write_text(json.dumps({
        "schemaVersion": 1,
        "iteration": "v232",
        "state": "no-wardrobe-desktop-camera-activated",
        "sourceMap": SOURCE_MAP,
        "targetMap": TARGET_MAP,
        "activeCamera": CAMERA_LABEL,
        "removedGeometry": [],
        "wardrobeVisible": False,
        "faceModified": False,
        "automaticApproval": False,
        "productionReady": False
    }, indent=2) + "\n", encoding="utf-8")
    unreal.log(f"Gahyeon v232 no-wardrobe desktop map created: {TARGET_MAP}")
    unreal.SystemLibrary.quit_editor()


build_no_wardrobe_desktop_v232()
