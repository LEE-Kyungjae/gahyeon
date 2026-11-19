"""Audit Face/Body transforms and bounds before changing the v042 neck region."""

import json
from pathlib import Path

import unreal


OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/metahuman-v042-neck-alignment.json"
)

records = {}
for actor in unreal.EditorLevelLibrary.get_all_level_actors():
    for component in actor.get_components_by_class(unreal.SkeletalMeshComponent):
        if component.get_name() not in ("Face", "Body"):
            continue
        records[component.get_name()] = {
            "relativeLocation": str(component.get_editor_property("relative_location")),
            "relativeRotation": str(component.get_editor_property("relative_rotation")),
            "relativeScale": str(component.get_editor_property("relative_scale3d")),
            "worldLocation": str(component.get_world_location()),
            "worldScale": str(component.get_world_scale()),
            "attachParent": component.get_attach_parent().get_name()
            if component.get_attach_parent()
            else None,
            "attachSocket": str(component.get_attach_socket_name()),
        }

if set(records) != {"Face", "Body"}:
    raise RuntimeError(f"expected Face and Body skeletal components, got {sorted(records)}")
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(json.dumps(records, indent=2), encoding="utf-8")
unreal.log(f"Gahyeon v042 neck alignment audit saved: {OUTPUT}")
