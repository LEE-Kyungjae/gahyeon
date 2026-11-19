"""Inspect all components on the talking-sequence character template and CDO."""

import json
from pathlib import Path

import unreal


SEQUENCE = "/Game/Gahyeon/TalkingPOC/v291/Sequence/LS_GahyeonTalkingFaceClose_v291"
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v299-gahyeon-component-tree-inspection/report.json"
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


def inspect_component(component):
    mesh = safe_property(component, "skeletal_mesh_asset")
    if mesh is None:
        mesh = safe_property(component, "skeletal_mesh")
    materials = []
    try:
        materials = [object_path(item) for item in component.get_materials()]
    except Exception:
        pass
    return {
        "name": str(component.get_name()),
        "class": str(component.get_class().get_name()),
        "path": object_path(component),
        "skeletalMesh": object_path(mesh),
        "materials": materials,
        "childActorClass": object_path(safe_property(component, "child_actor_class")),
        "leaderPoseComponent": object_path(
            safe_property(component, "leader_pose_component")
        ),
    }


def inspect_component_tree(actor):
    if actor is None:
        return []
    return [
        inspect_component(component)
        for component in actor.get_components_by_class(unreal.ActorComponent)
    ]


sequence = unreal.EditorAssetLibrary.load_asset(SEQUENCE)
if sequence is None:
    raise RuntimeError(f"sequence unavailable: {SEQUENCE}")
character_binding = next(
    (
        binding
        for binding in sequence.get_bindings()
        if "BP Gahyeon Animation POC" in str(binding.get_name())
    ),
    None,
)
if character_binding is None:
    raise RuntimeError("character spawnable binding unavailable")
template = character_binding.get_object_template()
if template is None:
    raise RuntimeError("character spawnable template unavailable")
cdo = unreal.get_default_object(template.get_class())

report = {
    "schemaVersion": 1,
    "iteration": "v299",
    "status": "read-only-component-tree-inspection",
    "sequence": SEQUENCE,
    "binding": str(character_binding.get_name()),
    "template": object_path(template),
    "templateComponents": inspect_component_tree(template),
    "classDefaultObject": object_path(cdo),
    "classDefaultComponents": inspect_component_tree(cdo),
    "mutatedAssets": [],
    "humanApproved": False,
    "productionReady": False,
}
OUTPUT.parent.mkdir(parents=True, exist_ok=False)
OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
unreal.log("GAHYEON_V299_COMPONENT_TREE=" + json.dumps(report, sort_keys=True))
unreal.SystemLibrary.quit_editor()
