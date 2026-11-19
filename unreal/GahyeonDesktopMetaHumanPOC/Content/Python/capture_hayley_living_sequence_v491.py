"""Capture one fixed-camera frame from each state in the v490 living sequence."""

import hashlib
import json
from pathlib import Path
import time

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
MAP = "/Game/LivingCharacterPOC/v490/QA/L_HayleyLivingSequence_v490"
SEQUENCE = "/Game/LivingCharacterPOC/v490/Sequence/LS_HayleyLivingSequence_v490"
OUTPUT = ROOT / "artifacts/living-character-poc-v491-hayley-living-sequence-evidence"
ITERATION = "v491"
CAMERA_DISTANCE_MULTIPLIER = 1.0
CAMERA_FOCAL_LENGTH = 50.0
USE_UNBOUND_EVIDENCE_CAMERA = False
POSES = (
    ("listening", 38), ("thinking", 136), ("speaking", 286),
    ("presenting", 413), ("emphasizing", 488), ("posture", 583),
)
_driver = None


class LivingSequenceCaptureV491:
    def __init__(self, sequence, camera):
        self.sequence = sequence
        self.camera = camera
        self.index = 0
        self.warmup = 18
        self.requested = False
        self.started = time.monotonic()
        self.records = []
        self.handle = unreal.register_slate_post_tick_callback(self.tick)

    def tick(self, _delta):
        if self.index >= len(POSES):
            report = {
                "schemaVersion": 1, "iteration": ITERATION,
                "status": "captured-draft-living-sequence-evidence",
                "map": MAP, "sequence": SEQUENCE, "frames": self.records,
                "humanApproved": False, "releaseEligible": False,
            }
            (OUTPUT / "report.json").write_text(json.dumps(report, indent=2) + "\n")
            unreal.unregister_slate_post_tick_callback(self.handle)
            unreal.LevelSequenceEditorBlueprintLibrary.close_level_sequence()
            unreal.EditorPythonScripting.set_keep_python_script_alive(False)
            unreal.SystemLibrary.quit_editor()
            return
        label, frame = POSES[self.index]
        path = OUTPUT / f"{self.index + 1:02d}-{label}-frame-{frame:04d}.png"
        if not self.requested:
            unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(frame)
            unreal.LevelSequenceEditorBlueprintLibrary.force_update()
            if self.warmup:
                self.warmup -= 1
                return
            self.requested = True
            unreal.AutomationLibrary.take_high_res_screenshot(1600, 900, str(path), self.camera)
            return
        if path.is_file() and path.stat().st_size > 24:
            self.records.append({
                "state": label, "sequenceFrame": frame, "file": str(path),
                "bytes": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            })
            self.index += 1
            self.warmup = 12
            self.requested = False
        elif time.monotonic() - self.started > 240:
            raise RuntimeError(f"v491 capture timed out at {label}: {path}")


def capture_hayley_living_sequence_v491():
    global _driver
    if OUTPUT.exists():
        raise FileExistsError(OUTPUT)
    OUTPUT.mkdir(parents=True)
    unreal.EditorLevelLibrary.load_level(MAP)
    sequence = unreal.load_asset(SEQUENCE)
    if sequence is None or not unreal.LevelSequenceEditorBlueprintLibrary.open_level_sequence(sequence):
        raise RuntimeError("failed to load/open v490 living sequence")
    cameras = [
        actor for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
        if actor.get_actor_label() == "CAM_HayleyLiving_v490"
    ]
    if len(cameras) != 1:
        raise RuntimeError(f"expected one v490 camera, got {cameras}")
    camera = cameras[0]
    if USE_UNBOUND_EVIDENCE_CAMERA:
        characters = [
            actor for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
            if actor.get_actor_label() == "Hayley_LivingCharacter_v490"
        ]
        if len(characters) != 1:
            raise RuntimeError(f"expected one v490 character, got {characters}")
        origin, extent = characters[0].get_actor_bounds(False, True)
        target = unreal.Vector(origin.x, origin.y, origin.z)
        camera_location = target + unreal.Vector(0.0, 720.0, 0.0)
        camera = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).spawn_actor_from_class(
            unreal.CineCameraActor,
            camera_location,
            unreal.MathLibrary.find_look_at_rotation(camera_location, target),
        )
        camera.set_actor_label(f"CAM_HayleyEvidence_{ITERATION}")
    else:
        camera_location = camera.get_actor_location()
        camera.set_actor_location(
            unreal.Vector(
                camera_location.x,
                camera_location.y * CAMERA_DISTANCE_MULTIPLIER,
                camera_location.z,
            ),
            False,
            False,
        )
    camera.camera_component.set_editor_property("current_focal_length", CAMERA_FOCAL_LENGTH)
    unreal.EditorPythonScripting.set_keep_python_script_alive(True)
    _driver = LivingSequenceCaptureV491(sequence, camera)


if __name__ == "__main__":
    capture_hayley_living_sequence_v491()
