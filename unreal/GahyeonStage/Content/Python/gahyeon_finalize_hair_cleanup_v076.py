"""Reopen and seal the already-saved v076 hair cleanup after independent validation."""

import json
from datetime import datetime, timezone
from pathlib import Path

import unreal


MAP = "/Game/Gahyeon/CharacterPipeline/v076/Preview/L_Skotukeda_HairCleanup_v076"
CHARACTER_LABEL = "Skotukeda_Medium_v027"
CARD_LABELS = {"HairCards_Straight_Group0_v042", "HairCards_Straight_Group1_v042"}
CAMERA_LABEL = "CAM_Gahyeon_HeadQA_v076"
RECEIPT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v076-hair-cleanup/build-receipt.json"
)


if RECEIPT.exists():
    raise RuntimeError(f"refusing to overwrite immutable v076 receipt: {RECEIPT}")
world = unreal.EditorLoadingAndSavingUtils.load_map(MAP)
if world is None:
    raise RuntimeError(f"failed to reopen v076 map: {MAP}")
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
character = next((actor for actor in actors if actor.get_actor_label() == CHARACTER_LABEL), None)
camera = next((actor for actor in actors if actor.get_actor_label() == CAMERA_LABEL), None)
if character is None or camera is None or not isinstance(camera, unreal.CineCameraActor):
    raise RuntimeError("v076 character or sealed head camera is missing")
grooms = [
    component
    for component in character.get_components_by_class(unreal.GroomComponent)
    if component.get_name() == "Hair" and component.get_editor_property("visible")
]
if len(grooms) != 1:
    raise RuntimeError(f"expected one retained visible Hair Groom, got {len(grooms)}")
hidden = []
for actor in actors:
    if actor.get_actor_label() not in CARD_LABELS:
        continue
    components = actor.get_components_by_class(unreal.StaticMeshComponent)
    if len(components) != 1:
        raise RuntimeError(f"unexpected card component count: {actor.get_actor_label()}")
    component = components[0]
    if component.get_editor_property("visible") or not component.get_editor_property("hidden_in_game"):
        raise RuntimeError(f"duplicate hair card remained visible: {actor.get_actor_label()}")
    hidden.append(actor.get_actor_label())
if set(hidden) != CARD_LABELS:
    raise RuntimeError(f"exact duplicate hair-card pair was not found: {hidden}")
location = camera.get_actor_location()
camera_component = camera.get_cine_camera_component()
receipt = {
    "schemaVersion": 1,
    "iteration": "v076",
    "state": "validated-draft-hair-cleanup",
    "observedAt": datetime.now(timezone.utc).isoformat(),
    "hypothesis": "The floating helmet silhouette was caused by legacy static HairCards rendering with the MetaHuman Hair Groom.",
    "action": "Hide only the two inventoried static HairCards and retain the MetaHuman Hair Groom.",
    "map": MAP,
    "hiddenHairCards": sorted(hidden),
    "retainedGroomComponent": grooms[0].get_name(),
    "qaCamera": {
        "label": CAMERA_LABEL,
        "location": [location.x, location.y, location.z],
        "focalLengthMm": camera_component.get_editor_property("current_focal_length"),
        "aperture": camera_component.get_editor_property("current_aperture")
    },
    "renderEvidenceComplete": False,
    "automaticApproval": False,
    "productionReady": False
}
RECEIPT.parent.mkdir(parents=True, exist_ok=True)
RECEIPT.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
unreal.log(f"Gahyeon v076 hair cleanup validated: {RECEIPT}")
unreal.SystemLibrary.quit_editor()
