"""Inventory render-critical components of the v186 KeenTools MetaHuman."""

import json
from pathlib import Path

import unreal


BLUEPRINT_PATH = (
    "/Game/Gahyeon/CharacterPipeline/v186/AssembledMedium/"
    "Gahyeon_KeenToolsMedium_v186/BP_Gahyeon_KeenToolsMedium_v186"
)
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v191-keentools-component-inventory/report.json"
)


def _optional_property_v191(value, name):
    try:
        return value.get_editor_property(name)
    except Exception:
        return None


def inspect_keentools_components_v191():
    if OUTPUT.exists():
        raise RuntimeError("refusing to overwrite immutable v191 inventory")
    character_class = unreal.EditorAssetLibrary.load_blueprint_class(BLUEPRINT_PATH)
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    character = actors.spawn_actor_from_class(character_class, unreal.Vector())
    if character is None:
        raise RuntimeError("failed to spawn v186 assembled MetaHuman")
    records = []
    for component in character.get_components_by_class(unreal.ActorComponent):
        record = {
            "name": component.get_name(),
            "class": component.get_class().get_name(),
            "active": bool(component.is_active()),
            "visible": _optional_property_v191(component, "visible"),
            "hiddenInGame": _optional_property_v191(component, "hidden_in_game"),
        }
        if isinstance(component, unreal.SceneComponent):
            record["worldLocation"] = list(component.get_world_location().to_tuple())
            record["worldScale"] = list(component.get_world_scale().to_tuple())
        if isinstance(component, unreal.SkeletalMeshComponent):
            mesh = _optional_property_v191(component, "skeletal_mesh_asset")
            record["skeletalMesh"] = mesh.get_path_name() if mesh else None
            record["materialCount"] = component.get_num_materials()
            record["materials"] = [
                component.get_material(index).get_path_name() if component.get_material(index) else None
                for index in range(component.get_num_materials())
            ]
            record["forcedLodModel"] = _optional_property_v191(component, "forced_lod_model")
            record["predictedLodLevel"] = _optional_property_v191(component, "predicted_lod_level")
        records.append(record)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps({
        "schemaVersion": 1,
        "iteration": "v191",
        "state": "read-only-render-component-inventory",
        "blueprint": BLUEPRINT_PATH,
        "components": records,
    }, indent=2) + "\n", encoding="utf-8")
    unreal.log(f"Gahyeon v191 component inventory complete: {OUTPUT}")
    unreal.SystemLibrary.quit_editor()


inspect_keentools_components_v191()
