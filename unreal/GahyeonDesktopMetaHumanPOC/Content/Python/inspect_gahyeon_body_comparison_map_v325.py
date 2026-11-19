"""Read-only verification of the persistent Gahyeon body comparison map."""

import json
from pathlib import Path

import unreal


MAP = "/Game/Gahyeon/CharacterPipeline/v323/QA/L_GahyeonBodyNormalsCompare_v323"
REPORT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v325-gahyeon-body-comparison-runtime/report.json"
)


def inspect_gahyeon_body_comparison_map_v325():
    if unreal.EditorLoadingAndSavingUtils.load_map(MAP) is None:
        raise RuntimeError(f"map unavailable: {MAP}")
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    inspected = []
    for actor in actors:
        label = actor.get_actor_label()
        if not label.startswith("Gahyeon_"):
            continue
        component = actor.get_component_by_class(unreal.SkeletalMeshComponent)
        mesh = component.get_editor_property("skeletal_mesh_asset")
        inspected.append(
            {
                "label": label,
                "mesh": str(mesh.get_path_name()) if mesh is not None else None,
                "visible": bool(component.is_visible()),
                "hiddenInGame": bool(component.get_editor_property("hidden_in_game")),
            }
        )
    inspected.sort(key=lambda item: item["label"])
    if len(inspected) != 2 or len({item["mesh"] for item in inspected}) != 2:
        raise RuntimeError(f"invalid persistent comparison actors: {inspected}")
    report = {
        "schemaVersion": 1,
        "iteration": "v325",
        "status": "runtime-map-binding-verified",
        "map": MAP,
        "actors": inspected,
        "mutatedAssets": [],
        "humanApproved": False,
        "productionReady": False,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=False)
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    unreal.log("GAHYEON_V325_MAP=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()


inspect_gahyeon_body_comparison_map_v325()
