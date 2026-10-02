"""Create v076 with duplicate floating hair cards hidden and a sealed head QA camera."""

import json
from datetime import datetime, timezone
from pathlib import Path

import unreal


SOURCE_MAP = "/Game/Gahyeon/CharacterPipeline/v075/Preview/L_Skotukeda_WardrobeReset_v075"
TARGET_MAP = "/Game/Gahyeon/CharacterPipeline/v076/Preview/L_Skotukeda_HairCleanup_v076"
CHARACTER_LABEL = "Skotukeda_Medium_v027"
CARD_LABELS = {"HairCards_Straight_Group0_v042", "HairCards_Straight_Group1_v042"}
CAMERA_LABEL = "CAM_Gahyeon_HeadQA_v076"
RECEIPT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v076-hair-cleanup/build-receipt.json"
)


if RECEIPT.exists():
    raise RuntimeError(f"refusing to overwrite immutable v076 receipt: {RECEIPT}")
if unreal.EditorAssetLibrary.does_asset_exist(TARGET_MAP):
    raise RuntimeError(f"refusing to overwrite immutable v076 map: {TARGET_MAP}")
world = unreal.EditorLoadingAndSavingUtils.load_map(SOURCE_MAP)
if world is None:
    raise RuntimeError(f"failed to load v075 source map: {SOURCE_MAP}")

actor_system = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
actors = actor_system.get_all_level_actors()
character = next((actor for actor in actors if actor.get_actor_label() == CHARACTER_LABEL), None)
if character is None:
    raise RuntimeError(f"character actor is unavailable: {CHARACTER_LABEL}")

groom_hair = [
    component
    for component in character.get_components_by_class(unreal.GroomComponent)
    if component.get_name() == "Hair"
]
if len(groom_hair) != 1 or not groom_hair[0].get_editor_property("visible"):
    raise RuntimeError("expected one visible MetaHuman Hair Groom before cleanup")

hidden_cards = []
for actor in actors:
    label = actor.get_actor_label()
    if label not in CARD_LABELS:
        continue
    components = actor.get_components_by_class(unreal.StaticMeshComponent)
    if len(components) != 1:
        raise RuntimeError(f"expected one static hair-card component: {label}")
    component = components[0]
    component.set_editor_property("visible", False)
    component.set_editor_property("hidden_in_game", True)
    hidden_cards.append(label)
if set(hidden_cards) != CARD_LABELS:
    raise RuntimeError(f"failed to hide the exact duplicate hair-card pair: {hidden_cards}")

head_target = character.get_actor_location() + unreal.Vector(0.0, 0.0, 165.0)
camera_location = head_target + unreal.Vector(0.0, 105.0, 0.0)
camera = actor_system.spawn_actor_from_class(unreal.CineCameraActor, camera_location)
if camera is None:
    raise RuntimeError("failed to spawn v076 head QA camera")
camera.set_actor_label(CAMERA_LABEL)
camera.set_actor_rotation(unreal.MathLibrary.find_look_at_rotation(camera_location, head_target), False)
camera_component = camera.get_cine_camera_component()
camera_component.set_editor_property("current_focal_length", 85.0)
camera_component.set_editor_property("current_aperture", 8.0)
focus = camera_component.get_editor_property("focus_settings")
focus.set_editor_property("focus_method", unreal.CameraFocusMethod.DISABLE)
camera_component.set_editor_property("focus_settings", focus)

if not unreal.EditorLoadingAndSavingUtils.save_map(world, TARGET_MAP):
    raise RuntimeError(f"failed to save immutable v076 map: {TARGET_MAP}")

receipt = {
    "schemaVersion": 1,
    "iteration": "v076",
    "state": "draft-hair-cleanup-built",
    "observedAt": datetime.now(timezone.utc).isoformat(),
    "hypothesis": "The floating helmet silhouette is caused by two legacy static HairCards rendering together with the MetaHuman Hair Groom.",
    "action": "Hide only the two inventoried static HairCards and retain the visible MetaHuman Hair Groom.",
    "expectedResult": "The duplicate outer shell disappears while the Groom hairline remains visible.",
    "sourceMap": SOURCE_MAP,
    "targetMap": TARGET_MAP,
    "hiddenHairCards": sorted(hidden_cards),
    "retainedGroomComponent": groom_hair[0].get_name(),
    "qaCamera": {
        "label": CAMERA_LABEL,
        "location": list(camera_location),
        "target": list(head_target),
        "focalLengthMm": 85.0,
        "aperture": 8.0
    },
    "automaticApproval": False,
    "productionReady": False
}
RECEIPT.parent.mkdir(parents=True, exist_ok=True)
RECEIPT.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
unreal.log(f"Gahyeon v076 hair cleanup saved: {TARGET_MAP}")
unreal.SystemLibrary.quit_editor()
