"""Inspect v186 skeletal mesh bounds APIs and values without mutation."""

import json
from pathlib import Path

import unreal


BLUEPRINT_PATH = (
    "/Game/Gahyeon/CharacterPipeline/v186/AssembledMedium/"
    "Gahyeon_KeenToolsMedium_v186/BP_Gahyeon_KeenToolsMedium_v186"
)
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v192-keentools-mesh-bounds-audit/report.json"
)


def inspect_keentools_mesh_bounds_v192():
    if OUTPUT.exists():
        raise RuntimeError("refusing to overwrite immutable v192 audit")
    character_class = unreal.EditorAssetLibrary.load_blueprint_class(BLUEPRINT_PATH)
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    character = actors.spawn_actor_from_class(character_class, unreal.Vector())
    records = []
    for component in character.get_components_by_class(unreal.SkeletalMeshComponent):
        mesh = component.get_editor_property("skeletal_mesh_asset")
        methods = [name for name in dir(mesh) if "bound" in name.lower()]
        values = {}
        for name in methods:
            try:
                member = getattr(mesh, name)
                values[name] = str(member() if callable(member) else member)
            except Exception as error:
                values[name] = f"ERROR: {error}"
        for name in ("imported_bounds", "positive_bounds_extension", "negative_bounds_extension"):
            try:
                values[f"property:{name}"] = str(mesh.get_editor_property(name))
            except Exception as error:
                values[f"property:{name}"] = f"ERROR: {error}"
        records.append({
            "component": component.get_name(),
            "mesh": mesh.get_path_name(),
            "boundsMembers": values,
        })
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps({
        "schemaVersion": 1,
        "iteration": "v192",
        "state": "read-only-skeletal-mesh-bounds-audit",
        "records": records,
    }, indent=2) + "\n", encoding="utf-8")
    unreal.log(f"Gahyeon v192 mesh bounds audit complete: {OUTPUT}")
    unreal.SystemLibrary.quit_editor()


inspect_keentools_mesh_bounds_v192()
