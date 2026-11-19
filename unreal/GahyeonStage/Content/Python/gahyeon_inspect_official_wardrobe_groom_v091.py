"""Inventory the rendered components in the official UE 5.8 Wardrobe assembly."""

import json
from pathlib import Path

import unreal


MAP = "/Game/Gahyeon/CharacterPipeline/v089/Preview/L_Skotukeda_WardrobeGroom_v089"
LABEL = "Skotukeda_WardrobeGroomQA_v088"
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v091-official-groom-diagnostic/component-inventory.json"
)


def path_name(value):
    return value.get_path_name() if value is not None else None


def optional_property(value, name):
    try:
        return value.get_editor_property(name)
    except Exception:
        return None


def vector(value):
    return [value.x, value.y, value.z]


def component_record(component):
    record = {
        "name": component.get_name(),
        "class": component.get_class().get_name(),
        "path": component.get_path_name(),
        "visible": bool(optional_property(component, "visible")),
        "hiddenInGame": bool(optional_property(component, "hidden_in_game")),
        "active": bool(component.is_active()),
    }
    if isinstance(component, unreal.SceneComponent):
        record.update({
            "worldLocation": vector(component.get_world_location()),
            "worldScale": vector(component.get_world_scale()),
            "attachParent": path_name(component.get_attach_parent()),
            "attachSocket": str(component.get_attach_socket_name()),
        })
    if isinstance(component, unreal.SkeletalMeshComponent):
        mesh = optional_property(component, "skeletal_mesh_asset")
        record.update({
            "role": "skeletal-mesh",
            "asset": path_name(mesh),
            "forcedLodModel": optional_property(component, "forced_lod_model"),
            "predictedLodLevel": optional_property(component, "predicted_lod_level"),
            "materials": [path_name(component.get_material(index)) for index in range(component.get_num_materials())],
        })
    elif isinstance(component, unreal.StaticMeshComponent):
        mesh = optional_property(component, "static_mesh")
        record.update({
            "role": "static-mesh",
            "asset": path_name(mesh),
            "forcedLodModel": optional_property(component, "forced_lod_model"),
            "materials": [path_name(component.get_material(index)) for index in range(component.get_num_materials())],
        })
    elif isinstance(component, unreal.GroomComponent):
        record.update({
            "role": "groom",
            "groomAsset": path_name(optional_property(component, "groom_asset")),
            "bindingAsset": path_name(optional_property(component, "binding_asset")),
            "forcedLod": optional_property(component, "forced_lod"),
            "materials": [path_name(component.get_material(index)) for index in range(component.get_num_materials())],
        })
    return record


def inspect_v088_components():
    if OUTPUT.exists():
        raise RuntimeError(f"refusing to overwrite immutable v091 inventory: {OUTPUT}")
    if unreal.EditorLoadingAndSavingUtils.load_map(MAP) is None:
        raise RuntimeError(f"failed to load source map: {MAP}")
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actor = next((value for value in actor_subsystem.get_all_level_actors() if value.get_actor_label() == LABEL), None)
    if actor is None:
        raise RuntimeError(f"assembled actor unavailable: {LABEL}")
    origin, extent = actor.get_actor_bounds(False, True)
    components = actor.get_components_by_class(unreal.ActorComponent)
    records = [component_record(component) for component in components]
    OUTPUT.parent.mkdir(parents=True, exist_ok=False)
    OUTPUT.write_text(json.dumps({
        "schemaVersion": 1,
        "iteration": "v091",
        "state": "read-only-component-inventory",
        "sourceMap": MAP,
        "actor": actor.get_path_name(),
        "actorClass": actor.get_class().get_path_name(),
        "actorBounds": {"origin": vector(origin), "extent": vector(extent)},
        "componentCount": len(records),
        "components": records,
        "automaticApproval": False,
        "productionReady": False,
    }, indent=2) + "\n", encoding="utf-8")
    unreal.log(f"Gahyeon v091 component inventory written: {OUTPUT}")
    unreal.SystemLibrary.quit_editor()


inspect_v088_components()
