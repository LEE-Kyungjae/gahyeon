"""Report character mesh, material, groom, and hair-related component state in v036."""

import json
from pathlib import Path

import unreal


OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/metahuman-v036-component-audit.json"
)

records = []
for actor in unreal.EditorLevelLibrary.get_all_level_actors():
    actor_record = {
        "label": actor.get_actor_label(),
        "class": actor.get_class().get_name(),
        "components": [],
    }
    for component in actor.get_components_by_class(unreal.ActorComponent):
        component_record = {
            "name": component.get_name(),
            "class": component.get_class().get_name(),
            "visible": getattr(component, "is_visible", lambda: None)(),
        }
        if isinstance(component, unreal.SkeletalMeshComponent):
            mesh = component.get_editor_property("skeletal_mesh_asset")
            component_record["skeletalMesh"] = mesh.get_path_name() if mesh else None
            component_record["materials"] = [
                component.get_material(index).get_path_name()
                if component.get_material(index)
                else None
                for index in range(component.get_num_materials())
            ]
        component_name = component.get_class().get_name().lower()
        if "groom" in component_name or "hair" in component_name:
            for property_name in ("groom_asset", "binding_asset"):
                try:
                    value = component.get_editor_property(property_name)
                except Exception:
                    continue
                component_record[property_name] = value.get_path_name() if value else None
        actor_record["components"].append(component_record)
    records.append(actor_record)

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")
unreal.log(f"Gahyeon v036 component audit saved: {OUTPUT}")
