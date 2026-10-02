"""Inventory every v233 actor and bound, including BSP/brush geometry."""

import json
from pathlib import Path

import unreal


MAP = "/Game/Gahyeon/CharacterPipeline/v233/Preview/L_Skotukeda_CleanNoWardrobeDesktop_v233"
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v234-skotukeda-scene-geometry/inventory.json"
)


def inventory_scene_geometry_v234():
    if OUTPUT.exists():
        raise RuntimeError("refusing to overwrite immutable v234 inventory")
    world = unreal.EditorLoadingAndSavingUtils.load_map(MAP)
    if world is None:
        raise RuntimeError(f"failed to load map: {MAP}")
    records = []
    for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
        origin, extent = actor.get_actor_bounds(False, True)
        records.append({
            "label": actor.get_actor_label(),
            "class": actor.get_class().get_name(),
            "location": [actor.get_actor_location().x, actor.get_actor_location().y,
                         actor.get_actor_location().z],
            "boundsOrigin": [origin.x, origin.y, origin.z],
            "boundsExtent": [extent.x, extent.y, extent.z],
            "hiddenInGame": bool(actor.get_editor_property("hidden")),
            "componentClasses": sorted({
                component.get_class().get_name() for component in actor.get_components_by_class(unreal.ActorComponent)
            }),
        })
    OUTPUT.parent.mkdir(parents=True, exist_ok=False)
    OUTPUT.write_text(json.dumps({
        "schemaVersion": 1,
        "iteration": "v234",
        "sourceMap": MAP,
        "actors": records
    }, indent=2) + "\n", encoding="utf-8")
    unreal.log(f"Gahyeon v234 scene geometry inventory: {OUTPUT}")
    unreal.SystemLibrary.quit_editor()


inventory_scene_geometry_v234()
