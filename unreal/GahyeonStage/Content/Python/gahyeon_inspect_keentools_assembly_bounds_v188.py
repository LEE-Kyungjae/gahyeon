"""Inspect v186 runtime assembly bounds without modifying its assets."""

import json
from pathlib import Path

import unreal


BLUEPRINT_PATH = (
    "/Game/Gahyeon/CharacterPipeline/v186/AssembledMedium/"
    "Gahyeon_KeenToolsMedium_v186/BP_Gahyeon_KeenToolsMedium_v186"
)
REPORT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v188-keentools-assembly-bounds-audit/report.json"
)


def inspect_keentools_assembly_bounds_v188():
    if REPORT.exists():
        raise RuntimeError("refusing to overwrite immutable v188 bounds audit")
    character_class = unreal.EditorAssetLibrary.load_blueprint_class(BLUEPRINT_PATH)
    if character_class is None:
        raise RuntimeError(f"v186 Blueprint unavailable: {BLUEPRINT_PATH}")
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    character = actors.spawn_actor_from_class(character_class, unreal.Vector())
    if character is None:
        raise RuntimeError("failed to spawn v186 assembled MetaHuman")
    records = []
    for component in character.get_components_by_class(unreal.SceneComponent):
        record = {
            "name": component.get_name(),
            "class": component.get_class().get_name(),
            "location": list(component.get_world_location().to_tuple()),
            "scale": list(component.get_world_scale().to_tuple()),
        }
        try:
            bounds = component.get_editor_property("bounds")
            record["bounds"] = {
                "origin": list(bounds.origin.to_tuple()),
                "extent": list(bounds.box_extent.to_tuple()),
                "heightCm": bounds.box_extent.z * 2.0,
            }
        except Exception as error:
            record["boundsError"] = str(error)
        records.append(record)
    variants = {}
    for only_colliding in (False, True):
        for include_children in (False, True):
            origin, extent = character.get_actor_bounds(only_colliding, include_children)
            variants[f"colliding={only_colliding},children={include_children}"] = {
                "origin": list(origin.to_tuple()),
                "extent": list(extent.to_tuple()),
                "heightCm": extent.z * 2.0,
            }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps({
        "schemaVersion": 1,
        "iteration": "v188",
        "state": "read-only-assembly-bounds-audit",
        "blueprint": BLUEPRINT_PATH,
        "actorLocation": list(character.get_actor_location().to_tuple()),
        "actorScale": list(character.get_actor_scale3d().to_tuple()),
        "actorBounds": variants,
        "components": records,
    }, indent=2) + "\n", encoding="utf-8")
    unreal.log(f"Gahyeon v188 assembly bounds audit complete: {REPORT}")
    unreal.SystemLibrary.quit_editor()


inspect_keentools_assembly_bounds_v188()
