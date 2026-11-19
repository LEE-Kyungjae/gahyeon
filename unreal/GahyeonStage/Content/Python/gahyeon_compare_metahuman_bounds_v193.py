"""Compare the working v169 and broken v186 assembly bounds with v183 input."""

import json
from pathlib import Path

import unreal


BLUEPRINTS = {
    "v169-working-facebuilder": (
        "/Game/Gahyeon/CharacterPipeline/v169/AssembledMedium/"
        "Gahyeon_FaceBuilderMedium_v169/BP_Gahyeon_FaceBuilderMedium_v169"
    ),
    "v186-keentools": (
        "/Game/Gahyeon/CharacterPipeline/v186/AssembledMedium/"
        "Gahyeon_KeenToolsMedium_v186/BP_Gahyeon_KeenToolsMedium_v186"
    ),
}
INPUT_MESH = "/Game/Gahyeon/CharacterPipeline/v183/Input/SM_Gahyeon_KeenTools_v183"
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v193-metahuman-bounds-comparison/report.json"
)


def _bounds_record(bounds):
    origin = bounds.origin
    extent = bounds.box_extent
    return {
        "origin": [origin.x, origin.y, origin.z],
        "extent": [extent.x, extent.y, extent.z],
        "dimensions": [extent.x * 2.0, extent.y * 2.0, extent.z * 2.0],
    }


def compare_metahuman_bounds_v193():
    if OUTPUT.exists():
        raise RuntimeError("refusing to overwrite immutable v193 audit")
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    assemblies = {}
    for label, path in BLUEPRINTS.items():
        character_class = unreal.EditorAssetLibrary.load_blueprint_class(path)
        if character_class is None:
            raise RuntimeError(f"missing Blueprint: {path}")
        actor = actor_subsystem.spawn_actor_from_class(character_class, unreal.Vector())
        records = []
        for component in actor.get_components_by_class(unreal.SkeletalMeshComponent):
            mesh = component.get_editor_property("skeletal_mesh_asset")
            if mesh is None:
                continue
            records.append({
                "component": component.get_name(),
                "mesh": mesh.get_path_name(),
                "importedBounds": _bounds_record(mesh.get_imported_bounds()),
            })
        assemblies[label] = records
        actor_subsystem.destroy_actor(actor)

    input_mesh = unreal.load_asset(INPUT_MESH)
    if input_mesh is None:
        raise RuntimeError(f"missing v183 input mesh: {INPUT_MESH}")
    input_values = {"asset": INPUT_MESH}
    for method_name in ("get_bounds", "get_bounding_box"):
        try:
            value = getattr(input_mesh, method_name)()
            input_values[method_name] = str(value)
        except Exception as error:
            input_values[method_name] = f"ERROR: {error}"

    OUTPUT.parent.mkdir(parents=True, exist_ok=False)
    OUTPUT.write_text(json.dumps({
        "schemaVersion": 1,
        "iteration": "v193",
        "state": "read-only-working-vs-broken-bounds-comparison",
        "assemblies": assemblies,
        "v183InputMesh": input_values,
    }, indent=2) + "\n", encoding="utf-8")
    unreal.log(f"Gahyeon v193 bounds comparison complete: {OUTPUT}")
    unreal.SystemLibrary.quit_editor()


compare_metahuman_bounds_v193()
