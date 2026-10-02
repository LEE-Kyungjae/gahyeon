"""Verify persistent Face+Body seam comparison actors before rendering."""

import json
from pathlib import Path

import unreal


MAP = "/Game/Gahyeon/CharacterPipeline/v327/QA/L_GahyeonFaceBodySeam_v327"
REPORT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v329-gahyeon-face-body-seam-runtime/report.json"
)


def inspect_gahyeon_face_body_seam_map_v329():
    if unreal.EditorLoadingAndSavingUtils.load_map(MAP) is None:
        raise RuntimeError(f"map unavailable: {MAP}")
    actors = []
    for actor in unreal.get_editor_subsystem(
        unreal.EditorActorSubsystem
    ).get_all_level_actors():
        label = actor.get_actor_label()
        if not label.startswith("Gahyeon_"):
            continue
        component = actor.get_component_by_class(unreal.SkeletalMeshComponent)
        mesh = component.get_editor_property("skeletal_mesh_asset")
        actors.append(
            {
                "label": label,
                "mesh": str(mesh.get_path_name()) if mesh is not None else None,
                "visible": bool(component.is_visible()),
                "hiddenInGame": bool(component.get_editor_property("hidden_in_game")),
            }
        )
    actors.sort(key=lambda item: item["label"])
    if len(actors) != 4 or not all(item["visible"] and not item["hiddenInGame"] for item in actors):
        raise RuntimeError(f"invalid seam actors: {actors}")
    face_paths = {item["mesh"] for item in actors if "_Face_" in item["label"]}
    body_paths = {item["mesh"] for item in actors if "_Body_" in item["label"]}
    if len(face_paths) != 1 or len(body_paths) != 2:
        raise RuntimeError(f"invalid seam lineage: faces={face_paths}, bodies={body_paths}")
    report = {
        "schemaVersion": 1,
        "iteration": "v329",
        "status": "runtime-seam-bindings-verified",
        "map": MAP,
        "actors": actors,
        "mutatedAssets": [],
        "humanApproved": False,
        "productionReady": False,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=False)
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    unreal.log("GAHYEON_V329_SEAM_RUNTIME=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()


inspect_gahyeon_face_body_seam_map_v329()
