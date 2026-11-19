"""Measure the imported v406 jawOpen mesh bounds at UE scale 1.0."""

import json
from pathlib import Path

import unreal


MESH = "/Game/LivingCharacterPOC/v406/JawOpenImport/Hayley_JawOpen_v405"
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/living-character-poc-v408-hayley-jawopen-bounds/report.json"
)


def inspect_hayley_jawopen_bounds_v408():
    if OUTPUT.exists():
        raise RuntimeError(f"refusing to overwrite v408 report: {OUTPUT}")
    mesh = unreal.load_asset(MESH)
    if mesh is None:
        raise RuntimeError(f"mesh unavailable: {MESH}")
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actor = actors.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector())
    actor.get_component_by_class(unreal.SkeletalMeshComponent).set_editor_property(
        "skeletal_mesh_asset", mesh
    )
    origin, extent = actor.get_actor_bounds(False, True)
    report = {
        "schemaVersion": 1,
        "iteration": "v408",
        "status": "read-only-bounds-inspection",
        "mesh": MESH,
        "actorScale": 1.0,
        "originCm": {"x": origin.x, "y": origin.y, "z": origin.z},
        "extentCm": {"x": extent.x, "y": extent.y, "z": extent.z},
        "heightCm": extent.z * 2.0,
        "humanApproved": False,
        "releaseEligible": False,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=False)
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n")
    unreal.log("HAYLEY_V408_BOUNDS=" + json.dumps(report, sort_keys=True))
    actors.destroy_actor(actor)
    unreal.SystemLibrary.quit_editor()


inspect_hayley_jawopen_bounds_v408()
