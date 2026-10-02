"""Inspect spawnable templates and materials used by the Gahyeon talking sequence."""

import json
from pathlib import Path

import unreal


SEQUENCE = "/Game/Gahyeon/TalkingPOC/v291/Sequence/LS_GahyeonTalkingFaceClose_v291"
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v298-gahyeon-sequence-template-inspection/report.json"
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
        "visible": bool(component.is_visible()),
        "hiddenInGame": bool(safe_property(component, "hidden_in_game") or False),
        "castShadow": bool(safe_property(component, "cast_shadow") or False),
        "materials": materials,
    }


def inspect_sequence(path):
    sequence = unreal.EditorAssetLibrary.load_asset(path)
    if sequence is None:
        raise RuntimeError(f"sequence unavailable: {path}")
    bindings = []
    for binding in sequence.get_bindings():
        template = None
        try:
            template = binding.get_object_template()
        except Exception:
            pass
        components = []
        if template is not None and isinstance(template, unreal.Actor):
            components = [
                inspect_component(component)
                for component in template.get_components_by_class(
                    unreal.SkeletalMeshComponent
                )
            ]
        bindings.append(
            {
                "name": str(binding.get_name()),
                "template": object_path(template),
                "templateClass": (
                    str(template.get_class().get_name()) if template is not None else None
                ),
                "skeletalComponents": components,
            }
        )
    return {"path": path, "bindings": bindings}


report = {
    "schemaVersion": 1,
    "iteration": "v298",
    "status": "read-only-sequence-template-inspection",
    "sequence": inspect_sequence(SEQUENCE),
    "mutatedAssets": [],
    "humanApproved": False,
    "productionReady": False,
}
OUTPUT.parent.mkdir(parents=True, exist_ok=False)
OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
unreal.log("GAHYEON_V298_TEMPLATE_INSPECTION=" + json.dumps(report, sort_keys=True))
unreal.SystemLibrary.quit_editor()
