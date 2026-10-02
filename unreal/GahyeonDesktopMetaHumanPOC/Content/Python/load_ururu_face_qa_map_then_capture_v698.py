"""Load the immutable Ururu QA map before starting the v697 capture driver."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import unreal


MAP = "/Game/LivingCharacterPOC/v696/QA/L_UruruTexturedFaceMorphQA_v696"
MODULE = "capture_ururu_ue_textured_face_morph_qa_v697"


def load_ururu_face_qa_map_then_capture_v698():
    if not unreal.EditorLevelLibrary.load_level(MAP):
        raise RuntimeError(f"failed to load immutable Ururu QA map: {MAP}")
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if world is None or world.get_path_name().split(".", 1)[0] != MAP:
        raise RuntimeError(f"v698 map load did not settle: {world.get_path_name() if world else None}")
    script_dir = Path(__file__).resolve().parent
    if str(script_dir) not in sys.path:
        sys.path.insert(0, str(script_dir))
    importlib.import_module(MODULE)


load_ururu_face_qa_map_then_capture_v698()
