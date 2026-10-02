"""Create immutable v077 by seating the visible hair cards 1.5 cm closer to the scalp."""

import json
from datetime import datetime, timezone
from pathlib import Path

import unreal


SOURCE_MAP = "/Game/Gahyeon/CharacterPipeline/v075/Preview/L_Skotukeda_WardrobeReset_v075"
TARGET_MAP = "/Game/Gahyeon/CharacterPipeline/v077/Preview/L_Skotukeda_HairCardAligned_v077"
CHARACTER_LABEL = "Skotukeda_Medium_v027"
CARD_LABELS = {"HairCards_Straight_Group0_v042", "HairCards_Straight_Group1_v042"}
CAMERA_LABEL = "CAM_Gahyeon_HeadQA_v077"
DELTA_Z_CM = -1.5
RECEIPT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v077-hair-card-alignment/build-receipt.json"
)


if RECEIPT.exists():
    raise RuntimeError(f"refusing to overwrite immutable v077 receipt: {RECEIPT}")
if unreal.EditorAssetLibrary.does_asset_exist(TARGET_MAP):
    raise RuntimeError(f"refusing to overwrite immutable v077 map: {TARGET_MAP}")
world = unreal.EditorLoadingAndSavingUtils.load_map(SOURCE_MAP)
if world is None:
    raise RuntimeError(f"failed to load v075 source map: {SOURCE_MAP}")

actor_system = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
actors = actor_system.get_all_level_actors()
character = next((actor for actor in actors if actor.get_actor_label() == CHARACTER_LABEL), None)
if character is None:
    raise RuntimeError(f"character actor is unavailable: {CHARACTER_LABEL}")

changes = []
for actor in actors:
    label = actor.get_actor_label()
    if label not in CARD_LABELS:
        continue
    before = actor.get_actor_location()
    after = before + unreal.Vector(0.0, 0.0, DELTA_Z_CM)
    if not actor.set_actor_location(after, False, False):
        raise RuntimeError(f"failed to move hair card: {label}")
    changes.append(
        {
            "label": label,
            "before": [before.x, before.y, before.z],
            "after": [after.x, after.y, after.z],
        }
    )
if {change["label"] for change in changes} != CARD_LABELS:
    raise RuntimeError(f"failed to align the exact hair-card pair: {changes}")

head_target = character.get_actor_location() + unreal.Vector(0.0, 0.0, 165.0)
camera_location = head_target + unreal.Vector(0.0, 105.0, 0.0)
camera = actor_system.spawn_actor_from_class(unreal.CineCameraActor, camera_location)
if camera is None:
    raise RuntimeError("failed to spawn v077 head QA camera")
camera.set_actor_label(CAMERA_LABEL)
camera.set_actor_rotation(unreal.MathLibrary.find_look_at_rotation(camera_location, head_target), False)
camera_component = camera.get_cine_camera_component()
camera_component.set_editor_property("current_focal_length", 85.0)
camera_component.set_editor_property("current_aperture", 8.0)
focus = camera_component.get_editor_property("focus_settings")
focus.set_editor_property("focus_method", unreal.CameraFocusMethod.DISABLE)
camera_component.set_editor_property("focus_settings", focus)

if not unreal.EditorLoadingAndSavingUtils.save_map(world, TARGET_MAP):
    raise RuntimeError(f"failed to save immutable v077 map: {TARGET_MAP}")

receipt = {
    "schemaVersion": 1,
    "iteration": "v077",
    "state": "draft-hair-card-alignment-built",
    "observedAt": datetime.now(timezone.utc).isoformat(),
    "hypothesis": "The retained card hair floats because its shell sits slightly above the scalp.",
    "action": "Move both inventoried hair-card actors downward by 1.5 cm without changing scale or deleting the fallback hair.",
    "expectedResult": "The hairline seats closer to the forehead while preserving the visible hairstyle.",
    "sourceMap": SOURCE_MAP,
    "targetMap": TARGET_MAP,
    "deltaZCm": DELTA_Z_CM,
    "changes": sorted(changes, key=lambda item: item["label"]),
    "qaCamera": CAMERA_LABEL,
    "automaticApproval": False,
    "productionReady": False,
}
RECEIPT.parent.mkdir(parents=True, exist_ok=True)
RECEIPT.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
unreal.log(f"Gahyeon v077 hair-card alignment saved: {TARGET_MAP}")
unreal.SystemLibrary.quit_editor()
