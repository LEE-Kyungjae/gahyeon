"""Capture Ururu morphs from a startup-loaded map using validated v585 materials."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import time

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
MAP = "/Game/LivingCharacterPOC/v696/QA/L_UruruTexturedFaceMorphQA_v696"
DONOR = "/Game/LivingCharacterPOC/v585/Characters/UruruCentimeterNormalized/Ururu_CentimeterNormalized_v584"
OUTPUT = ROOT / "artifacts/living-character-poc-v697-ururu-ue-textured-face-morph-qa"
STATES = (
    ("neutral", {}),
    ("blink", {"EyeBlink_L": 1.0, "EyeBlink_R": 1.0}),
    ("blink-left", {"EyeBlink_L": 1.0}),
    ("gaze-left", {"GazeLeft": 1.0}),
    ("gaze-right", {"GazeRight": 1.0}),
)
_driver = None


class UruruTexturedFaceMorphCaptureV697:
    def __init__(self):
        if OUTPUT.exists():
            raise RuntimeError("refusing to overwrite immutable v697 evidence")
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
        if world is None or world.get_path_name().split(".", 1)[0] != MAP:
            raise RuntimeError(f"v697 requires startup-loaded map {MAP}; actual={world.get_path_name() if world else None}")
        actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
        character = next((actor for actor in actors if actor.get_actor_label() == "UruruNativeFaceMorphQA_v695"), None)
        camera = next((actor for actor in actors if isinstance(actor, unreal.CineCameraActor)), None)
        donor = unreal.load_asset(DONOR)
        if character is None or camera is None or not isinstance(donor, unreal.SkeletalMesh):
            raise RuntimeError("v697 startup map character, camera, or material donor is unavailable")
        self.component = character.get_component_by_class(unreal.SkeletalMeshComponent)
        donor_by_name = {
            str(slot.material_slot_name): slot.material_interface
            for slot in donor.get_editor_property("materials")
            if slot.material_interface is not None
        }
        borrowed = []
        mesh = self.component.get_editor_property("skeletal_mesh_asset")
        for index, slot in enumerate(mesh.get_editor_property("materials")):
            name = str(slot.material_slot_name)
            material = donor_by_name.get(name)
            if material is not None:
                self.component.set_material(index, material)
                borrowed.append({"slot": index, "name": name, "material": material.get_path_name()})
        if len(borrowed) < 9:
            raise RuntimeError(f"too few validated material slots restored: {borrowed}")
        OUTPUT.mkdir(parents=True, exist_ok=False)
        self.camera = camera
        self.borrowed = borrowed
        self.index = 0
        self.current = None
        self.warmup = 180
        self.started = time.monotonic()
        self.frames = []
        unreal.EditorPythonScripting.set_keep_python_script_alive(True)
        self.handle = unreal.register_slate_post_tick_callback(self.tick)

    def tick(self, _delta):
        if time.monotonic() - self.started > 240:
            raise RuntimeError("v697 face morph capture timed out")
        if self.warmup:
            self.warmup -= 1
            return
        if self.index >= len(STATES):
            report = {
                "schemaVersion": 1,
                "iteration": "v697",
                "status": "captured-draft-ue-textured-native-face-morph-evidence",
                "startupMap": MAP,
                "materialDonor": DONOR,
                "borrowedMaterials": self.borrowed,
                "states": self.frames,
                "visualValidationPending": True,
                "automaticApproval": False,
                "humanApproved": False,
                "productionReady": False,
            }
            (OUTPUT / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
            unreal.log("URURU_UE_TEXTURED_FACE_MORPH_QA_V697=" + json.dumps(report, sort_keys=True))
            unreal.unregister_slate_post_tick_callback(self.handle)
            unreal.EditorPythonScripting.set_keep_python_script_alive(False)
            unreal.SystemLibrary.quit_editor()
            return
        label, values = STATES[self.index]
        output = OUTPUT / f"{label}.png"
        if self.current is None:
            self.component.clear_morph_targets()
            for name, value in values.items():
                self.component.set_morph_target(name, value, False)
            self.current = output
            unreal.AutomationLibrary.take_high_res_screenshot(1200, 1200, str(output), self.camera)
            return
        if output.is_file() and output.stat().st_size > 1024:
            self.frames.append({
                "label": label,
                "morphWeights": values,
                "file": str(output),
                "bytes": output.stat().st_size,
                "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
            })
            self.index += 1
            self.current = None
            self.warmup = 12


def capture_ururu_ue_textured_face_morph_qa_v697():
    global _driver
    _driver = UruruTexturedFaceMorphCaptureV697()


capture_ururu_ue_textured_face_morph_qa_v697()
