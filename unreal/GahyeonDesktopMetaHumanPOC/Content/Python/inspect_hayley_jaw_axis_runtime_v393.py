"""Measure Hayley's imported cJaw animation in UE without changing assets."""

import json
from pathlib import Path

import unreal


MESH = "/Game/LivingCharacterPOC/v391/JawAxisSweepImport/Hayley_JawAxisSweep_Full_v390"
ANIMATION = "/Game/LivingCharacterPOC/v391/JawAxisSweepImport/Hayley_JawAxisSweep_Full_v390_Anim"
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/"
    "living-character-poc-v393-hayley-jaw-runtime-inspection/report.json"
)
POSES = (
    ("neutral", 0.0),
    ("jaw-x-plus-5", 0.3),
    ("jaw-x-minus-5", 0.633333),
    ("jaw-y-plus-5", 0.966667),
    ("jaw-y-minus-5", 1.3),
    ("jaw-z-plus-5", 1.633333),
    ("jaw-z-minus-5", 1.966667),
)


def inspect_hayley_jaw_axis_runtime_v393():
    if OUTPUT.exists():
        raise RuntimeError(f"refusing to overwrite immutable v393 report: {OUTPUT}")
    mesh = unreal.load_asset(MESH)
    animation = unreal.load_asset(ANIMATION)
    if mesh is None or animation is None:
        raise RuntimeError(f"missing calibration assets: mesh={mesh}, animation={animation}")
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actor = actors.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector())
    component = actor.get_component_by_class(unreal.SkeletalMeshComponent)
    component.set_editor_property("skeletal_mesh_asset", mesh)
    component.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
    component.play_animation(animation, True)
    component.set_editor_property("global_anim_rate_scale", 0.0)
    records = []
    for label, position in POSES:
        component.set_position(position, False)
        transform = component.get_socket_transform("cJaw", unreal.RelativeTransformSpace.RTS_COMPONENT)
        location = transform.translation
        rotation = transform.rotation.rotator()
        records.append({
            "label": label,
            "positionSeconds": position,
            "translation": {"x": location.x, "y": location.y, "z": location.z},
            "rotationDegrees": {"roll": rotation.roll, "pitch": rotation.pitch, "yaw": rotation.yaw},
        })
    neutral = records[0]
    deltas = []
    for record in records[1:]:
        deltas.append({
            "label": record["label"],
            "rotationDeltaDegrees": {
                key: record["rotationDegrees"][key] - neutral["rotationDegrees"][key]
                for key in ("roll", "pitch", "yaw")
            },
        })
    report = {
        "schemaVersion": 1,
        "iteration": "v393",
        "status": "runtime-jaw-axis-inspected",
        "mesh": MESH,
        "animation": ANIMATION,
        "bone": "cJaw",
        "poses": records,
        "deltas": deltas,
        "humanApproved": False,
        "releaseEligible": False,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=False)
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n")
    unreal.log("HAYLEY_V393_JAW_RUNTIME=" + json.dumps(report, sort_keys=True))
    actors.destroy_actor(actor)
    unreal.SystemLibrary.quit_editor()


inspect_hayley_jaw_axis_runtime_v393()
