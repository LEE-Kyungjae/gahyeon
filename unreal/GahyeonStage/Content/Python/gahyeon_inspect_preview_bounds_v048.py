"""Record v048 camera and actor bounds to diagnose an apparent first-person view."""

import json
from pathlib import Path

import unreal


MAP = "/Game/Gahyeon/CharacterPipeline/v048/Preview/L_Skotukeda_ConformedGarment_v048"
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/garment-conform/v048/"
    "unreal-preview-bounds.json"
)

if not unreal.EditorLoadingAndSavingUtils.load_map(MAP):
    raise RuntimeError(f"failed to load v048 preview: {MAP}")
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
report = {"schemaVersion": 1, "map": MAP, "actors": []}
for actor in actors:
    label = actor.get_actor_label()
    if label not in {
        "CAM_Gahyeon_Desktop_v025b",
        "Skotukeda_Medium_v027",
        "ConformedDefaultGarment_v048",
    }:
        continue
    origin, extent = actor.get_actor_bounds(False)
    entry = {
        "label": label,
        "class": actor.get_class().get_name(),
        "location": list(actor.get_actor_location()),
        "rotation": list(actor.get_actor_rotation()),
        "scale": list(actor.get_actor_scale3d()),
        "boundsOrigin": list(origin),
        "boundsExtent": list(extent),
    }
    if isinstance(actor, unreal.CameraActor):
        entry["autoActivateForPlayer"] = str(
            actor.get_editor_property("auto_activate_for_player")
        )
        entry["focalLength"] = actor.camera_component.get_editor_property(
            "current_focal_length"
        )
    report["actors"].append(entry)
OUTPUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
unreal.log(f"Gahyeon v048 bounds report written: {OUTPUT}")
