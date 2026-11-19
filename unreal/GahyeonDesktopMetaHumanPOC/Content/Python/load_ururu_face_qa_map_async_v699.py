"""Wait for UE's asynchronous map load, then start the v697 capture driver."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
import time

import unreal


MAP = "/Game/LivingCharacterPOC/v696/QA/L_UruruTexturedFaceMorphQA_v696"
MODULE = "capture_ururu_ue_textured_face_morph_qa_v697"
_driver = None


class UruruFaceMapLoadDriverV699:
    def __init__(self):
        self.started = time.monotonic()
        unreal.EditorPythonScripting.set_keep_python_script_alive(True)
        self.handle = unreal.register_slate_post_tick_callback(self.tick)
        if not unreal.EditorLevelLibrary.load_level(MAP):
            raise RuntimeError(f"failed to request immutable Ururu QA map: {MAP}")

    def tick(self, _delta):
        if time.monotonic() - self.started > 90:
            raise RuntimeError("v699 timed out waiting for Ururu QA map")
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
        if world is None or world.get_path_name().split(".", 1)[0] != MAP:
            return
        unreal.unregister_slate_post_tick_callback(self.handle)
        script_dir = Path(__file__).resolve().parent
        if str(script_dir) not in sys.path:
            sys.path.insert(0, str(script_dir))
        importlib.import_module(MODULE)


def load_ururu_face_qa_map_async_v699():
    global _driver
    _driver = UruruFaceMapLoadDriverV699()


load_ururu_face_qa_map_async_v699()
