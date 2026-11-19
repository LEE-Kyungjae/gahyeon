"""Measure evaluated bounds and root motion for the failed Stella IK walk render."""

from __future__ import annotations

import json
from pathlib import Path
import time

import unreal


ITERATION = "v567"
MESH = "/Game/LivingCharacterPOC/v558/Characters/StellaLilyTextured/StellaLily_PreviewReady_v556"
ANIMATION = "/Game/LivingCharacterPOC/v565/Animation/AS_StellaLily_IKWalk_v565"
OUTPUT = Path("/Users/ze/work/gahyeonbot/artifacts/living-character-poc-v567-stella-ik-walk-diagnostics/report.json")
_driver = None
TARGET_BONES = (
    "Bip001",
    "Bip001-Pelvis",
    "Bip001-L-Thigh",
    "Bip001-R-Thigh",
    "Bip001-L-Foot",
    "Bip001-R-Foot",
)


def vector_record_v567(value):
    return {"x": float(value.x), "y": float(value.y), "z": float(value.z)}


def transform_record_v567(value):
    rotation = value.rotation
    return {
        "translation": vector_record_v567(value.translation),
        "rotation": {
            "x": float(rotation.x),
            "y": float(rotation.y),
            "z": float(rotation.z),
            "w": float(rotation.w),
        },
        "scale": vector_record_v567(value.scale3d),
    }


class WalkDiagnosticV567:
    def __init__(self):
        if OUTPUT.parent.exists():
            raise RuntimeError(f"refusing to overwrite immutable {ITERATION} diagnostics")
        OUTPUT.parent.mkdir(parents=True)
        mesh = unreal.load_asset(MESH)
        animation = unreal.load_asset(ANIMATION)
        if mesh is None or animation is None:
            raise RuntimeError("required Stella mesh or IK walk animation is unavailable")
        duration = float(animation.get_play_length())
        self.animation = animation
        self.phases = (duration * 0.1, duration * 0.5, duration * 0.9)
        actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        self.samples = []
        for index, phase in enumerate(self.phases):
            spawn = unreal.Vector((index - 1) * 100.0, 0.0, 0.0)
            actor = actors.spawn_actor_from_class(unreal.SkeletalMeshActor, spawn)
            actor.set_actor_label(f"Stella_IKWalk_Diagnostic_{index}_{ITERATION}")
            component = actor.get_component_by_class(unreal.SkeletalMeshComponent)
            component.set_editor_property("skeletal_mesh_asset", mesh)
            component.override_animation_data(animation, True, False, phase, 0.0)
            self.samples.append((actor, component, spawn, phase))
        self.ticks = 0
        self.started = time.monotonic()
        self.handle = unreal.register_slate_post_tick_callback(self.tick)

    def tick(self, _delta):
        self.ticks += 1
        if self.ticks < 30:
            return
        records = []
        for actor, component, spawn, phase in self.samples:
            origin, extent = actor.get_actor_bounds(False, True)
            actor_location = actor.get_actor_location()
            bones = {}
            for bone in TARGET_BONES:
                bones[bone] = {
                    "component": transform_record_v567(
                        component.get_socket_transform(bone, unreal.RelativeTransformSpace.RTS_COMPONENT)
                    ),
                    "world": transform_record_v567(
                        component.get_socket_transform(bone, unreal.RelativeTransformSpace.RTS_WORLD)
                    ),
                }
            records.append(
                {
                    "phaseSeconds": phase,
                    "spawn": vector_record_v567(spawn),
                    "actorLocation": vector_record_v567(actor_location),
                    "boundsOrigin": vector_record_v567(origin),
                    "boundsExtent": vector_record_v567(extent),
                    "heightCm": float(extent.z * 2.0),
                    "distanceFromSpawnCm": float((origin - spawn).length()),
                    "bones": bones,
                }
            )
        report = {
            "schemaVersion": 1,
            "iteration": ITERATION,
            "status": "measured-evaluated-ik-walk",
            "mesh": MESH,
            "animation": ANIMATION,
            "samples": records,
            "humanApproved": False,
            "releaseEligible": False,
        }
        OUTPUT.write_text(json.dumps(report, indent=2) + "\n")
        unreal.unregister_slate_post_tick_callback(self.handle)
        unreal.EditorPythonScripting.set_keep_python_script_alive(False)
        unreal.SystemLibrary.quit_editor()
        if time.monotonic() - self.started > 180:
            raise RuntimeError("v567 diagnostics timed out")


def diagnose_stella_ik_walk_v567():
    global _driver
    unreal.EditorPythonScripting.set_keep_python_script_alive(True)
    _driver = WalkDiagnosticV567()


if __name__ == "__main__":
    diagnose_stella_ik_walk_v567()
