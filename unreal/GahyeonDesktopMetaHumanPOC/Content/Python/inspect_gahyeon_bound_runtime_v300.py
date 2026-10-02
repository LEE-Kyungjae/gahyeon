"""Evaluate the talking sequence and inspect its spawned character components."""

import json
from pathlib import Path

import unreal


MAP = "/Game/Gahyeon/TalkingPOC/v275/QA/L_Gahyeon_TalkingPIE_v275"
SEQUENCE = "/Game/Gahyeon/TalkingPOC/v291/Sequence/LS_GahyeonTalkingFaceClose_v291"
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v300-gahyeon-bound-runtime-inspection/report.json"
)


def object_path(value):
    if value is None:
        return None
    try:
        return str(value.get_path_name())
    except Exception:
        return str(value)


def safe_property(value, name):
    try:
        return value.get_editor_property(name)
    except Exception:
        return None


def inspect_material(material):
    if material is None:
        return None
    textures = []
    try:
        textures = sorted(
            object_path(texture)
            for texture in unreal.MaterialEditingLibrary.get_used_textures(material)
            if texture is not None
        )
    except Exception:
        pass
    return {
        "path": object_path(material),
        "class": str(material.get_class().get_name()),
        "parent": object_path(safe_property(material, "parent")),
        "usedTextures": textures,
    }


def inspect_component(component):
    mesh = safe_property(component, "skeletal_mesh_asset")
    if mesh is None:
        mesh = safe_property(component, "skeletal_mesh")
    materials = []
    try:
        materials = [inspect_material(item) for item in component.get_materials()]
    except Exception:
        pass
    return {
        "name": str(component.get_name()),
        "class": str(component.get_class().get_name()),
        "path": object_path(component),
        "skeletalMesh": object_path(mesh),
        "visible": (
            bool(component.is_visible())
            if hasattr(component, "is_visible")
            else None
        ),
        "hiddenInGame": bool(safe_property(component, "hidden_in_game") or False),
        "castShadow": bool(safe_property(component, "cast_shadow") or False),
        "materials": materials,
    }


def inspect_bound_actor(actor):
    return {
        "label": actor.get_actor_label(),
        "class": str(actor.get_class().get_name()),
        "path": object_path(actor),
        "components": [
            inspect_component(component)
            for component in actor.get_components_by_class(unreal.ActorComponent)
        ],
    }


if unreal.EditorLoadingAndSavingUtils.load_map(MAP) is None:
    raise RuntimeError(f"map unavailable: {MAP}")
sequence = unreal.EditorAssetLibrary.load_asset(SEQUENCE)
if sequence is None:
    raise RuntimeError(f"sequence unavailable: {SEQUENCE}")
if not unreal.LevelSequenceEditorBlueprintLibrary.open_level_sequence(sequence):
    raise RuntimeError(f"could not open sequence: {SEQUENCE}")
unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(1)
unreal.LevelSequenceEditorBlueprintLibrary.force_update()

bindings = []
all_bound_actors = []
for binding in sequence.get_bindings():
    binding_id = unreal.MovieSceneObjectBindingID()
    binding_id.set_editor_property("guid", binding.get_id())
    objects = list(
        unreal.LevelSequenceEditorBlueprintLibrary.get_bound_objects(binding_id)
    )
    inspected = [
        inspect_bound_actor(value)
        for value in objects
        if isinstance(value, unreal.Actor)
    ]
    all_bound_actors.extend(inspected)
    bindings.append(
        {
            "name": str(binding.get_name()),
            "boundObjects": [object_path(value) for value in objects],
            "actors": inspected,
        }
    )

report = {
    "schemaVersion": 1,
    "iteration": "v300",
    "status": "read-only-evaluated-binding-inspection",
    "map": MAP,
    "sequence": SEQUENCE,
    "bindings": bindings,
    "boundActorCount": len(all_bound_actors),
    "mutatedAssets": [],
    "humanApproved": False,
    "productionReady": False,
}
OUTPUT.parent.mkdir(parents=True, exist_ok=False)
OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
unreal.log("GAHYEON_V300_BOUND_RUNTIME=" + json.dumps(report, sort_keys=True))
unreal.LevelSequenceEditorBlueprintLibrary.close_level_sequence()
unreal.SystemLibrary.quit_editor()
