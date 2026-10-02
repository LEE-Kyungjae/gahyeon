"""Inventory the actual v055 body and wardrobe layers before creating v075."""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import unreal


MAP = "/Game/Gahyeon/CharacterPipeline/v055/Preview/L_Skotukeda_DonorOutfit_v055"
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v075-wardrobe-reset/layer-inventory.json"
)


def asset_path(value):
    return value.get_path_name() if value is not None else None


world = unreal.EditorLoadingAndSavingUtils.load_map(MAP)
if world is None:
    raise RuntimeError(f"failed to load v055 source map: {MAP}")

entries = []
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
for actor in actors:
    components = []
    for component in actor.get_components_by_class(unreal.MeshComponent):
        mesh = None
        if isinstance(component, unreal.SkeletalMeshComponent):
            mesh = component.get_editor_property("skeletal_mesh_asset")
        elif isinstance(component, unreal.StaticMeshComponent):
            mesh = component.get_editor_property("static_mesh")
        materials = [asset_path(component.get_material(index)) for index in range(component.get_num_materials())]
        if mesh is None and not any(materials):
            continue
        components.append({
            "name": component.get_name(),
            "class": component.get_class().get_name(),
            "visible": bool(component.get_editor_property("visible")),
            "hiddenInGame": bool(component.get_editor_property("hidden_in_game")),
            "mesh": asset_path(mesh),
            "materials": materials,
        })
    if components:
        entries.append({
            "label": actor.get_actor_label(),
            "class": actor.get_class().get_name(),
            "path": actor.get_path_name(),
            "components": components,
        })

payload = {
    "schemaVersion": 1,
    "iteration": "v075",
    "state": "inspected",
    "observedAt": datetime.now(timezone.utc).isoformat(),
    "sourceMap": MAP,
    "actors": entries,
    "automaticApproval": False,
    "productionReady": False,
}
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
if OUTPUT.exists():
    raise RuntimeError(f"refusing to overwrite immutable inventory: {OUTPUT}")
OUTPUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
unreal.log(f"Gahyeon v075 wardrobe layer inventory written: {OUTPUT}")
unreal.SystemLibrary.quit_editor()
