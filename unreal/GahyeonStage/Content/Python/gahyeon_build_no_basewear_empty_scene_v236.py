"""Remove default BSP and reframe the immutable v235 no-basewear diagnostic."""

import json
from pathlib import Path

import unreal


SOURCE_MAP = "/Game/Gahyeon/CharacterPipeline/v235/Preview/L_Skotukeda_NoBasewearClean_v235"
TARGET_MAP = "/Game/Gahyeon/CharacterPipeline/v236/Preview/L_Skotukeda_NoBasewearEmpty_v236"
REPORT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v236-skotukeda-no-basewear-empty/build-report.json"
)


def build_no_basewear_empty_scene_v236():
    if REPORT.exists() or unreal.EditorAssetLibrary.does_asset_exist(TARGET_MAP):
        raise RuntimeError("refusing to overwrite immutable v236 output")
    world = unreal.EditorLoadingAndSavingUtils.load_map(SOURCE_MAP)
    if world is None:
        raise RuntimeError(f"failed to load v235 source: {SOURCE_MAP}")

    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    camera = next(
        (actor for actor in actors if actor.get_actor_label() == "CAM_Skotukeda_NoBasewear_v235"),
        None,
    )
    character = next(
        (actor for actor in actors if actor.get_actor_label() == "Skotukeda_NoBasewear_v235"),
        None,
    )
    if camera is None or character is None:
        raise RuntimeError("v235 character or fixed camera is missing")
    origin, extent = character.get_actor_bounds(False, True)
    target = unreal.Vector(origin.x, origin.y, origin.z)
    location = unreal.Vector(origin.x, origin.y + max(650.0, extent.z * 7.0), origin.z + 8.0)
    camera.set_actor_location(location, False, False)
    camera.set_actor_rotation(unreal.MathLibrary.find_look_at_rotation(location, target), False)
    camera.set_actor_label("CAM_Skotukeda_NoBasewear_v236")

    if not unreal.EditorLoadingAndSavingUtils.save_map(world, TARGET_MAP):
        raise RuntimeError(f"failed to save v236 map: {TARGET_MAP}")
    REPORT.parent.mkdir(parents=True, exist_ok=False)
    REPORT.write_text(json.dumps({
        "schemaVersion": 1,
        "iteration": "v236",
        "state": "built-draft-no-basewear-empty-scene",
        "sourceMap": SOURCE_MAP,
        "targetMap": TARGET_MAP,
        "foregroundOcclusionAvoidedByBoundsCamera": True,
        "characterBoundsCm": {
            "origin": [origin.x, origin.y, origin.z],
            "extent": [extent.x, extent.y, extent.z],
        },
        "cameraLocation": [location.x, location.y, location.z],
        "cameraTarget": [target.x, target.y, target.z],
        "faceGeometryModified": False,
        "faceDnaModified": False,
        "cleanSkinMaterialsRetained": True,
        "automaticApproval": False,
        "productionReady": False,
    }, indent=2) + "\n", encoding="utf-8")
    unreal.log(f"Gahyeon v236 empty no-basewear map saved: {TARGET_MAP}")
    unreal.SystemLibrary.quit_editor()


build_no_basewear_empty_scene_v236()
