"""Measure v075 fallback hair-card transforms and bounds before a v077 alignment attempt."""

import json
from pathlib import Path

import unreal


MAP = "/Game/Gahyeon/CharacterPipeline/v075/Preview/L_Skotukeda_WardrobeReset_v075"
LABELS = {"Skotukeda_Medium_v027", "HairCards_Straight_Group0_v042", "HairCards_Straight_Group1_v042"}
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v077-hair-card-alignment/measurement.json"
)


if OUTPUT.exists():
    raise RuntimeError(f"refusing to overwrite immutable v077 measurement: {OUTPUT}")
world = unreal.EditorLoadingAndSavingUtils.load_map(MAP)
if world is None:
    raise RuntimeError(f"failed to load retained v075 map: {MAP}")
entries = []
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
for actor in actors:
    label = actor.get_actor_label()
    if label not in LABELS:
        continue
    location = actor.get_actor_location()
    rotation = actor.get_actor_rotation()
    scale = actor.get_actor_scale3d()
    origin, extent = actor.get_actor_bounds(False)
    entries.append({
        "label": label,
        "location": [location.x, location.y, location.z],
        "rotation": [rotation.roll, rotation.pitch, rotation.yaw],
        "scale": [scale.x, scale.y, scale.z],
        "boundsOrigin": [origin.x, origin.y, origin.z],
        "boundsExtent": [extent.x, extent.y, extent.z]
    })
if {entry["label"] for entry in entries} != LABELS:
    raise RuntimeError(f"expected character and exact HairCards pair: {entries}")
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(
    json.dumps({"schemaVersion": 1, "iteration": "v077", "sourceMap": MAP, "actors": entries}, indent=2) + "\n",
    encoding="utf-8"
)
unreal.log(f"Gahyeon v077 hair-card measurement written: {OUTPUT}")
unreal.SystemLibrary.quit_editor()
