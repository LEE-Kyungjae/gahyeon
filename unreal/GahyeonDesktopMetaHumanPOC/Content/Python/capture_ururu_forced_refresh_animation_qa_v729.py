"""Capture exact imported animation peaks after forcing skeletal render refresh."""

from __future__ import annotations

from pathlib import Path


SOURCE = Path(__file__).with_name("capture_ururu_ue_animation_qa_v709.py")
OLD_MESH = "/Game/LivingCharacterPOC/v693/Characters/UruruFacial/Ururu_StaticHeadMorphs_v691"
COMBINED_MESH = "/Game/LivingCharacterPOC/v705/Characters/UruruFacial/Ururu_HeadMorphs_Centimeter_v688"
OLD_STATES = 'STATES = (("neutral", 1), ("blink", 10), ("gaze-left", 20), ("gaze-right", 30))'
PEAK_STATES = 'STATES = (("neutral", 0), ("blink", 9), ("gaze-left", 19), ("gaze-right", 29))'
OLD_APPLY = '''            self.component.override_animation_data(self.animation, False, False, position, 0.0)
'''
REFRESHED_APPLY = '''            self.component.override_animation_data(self.animation, False, False, position, 0.0)
            message = unreal.GahyeonMetaHumanQALibrary.force_refresh_skeletal_morphs(
                self.component,
            )
            if not isinstance(message, str) or "refreshed" not in message:
                raise RuntimeError(f"v729 skeletal animation refresh failed: {message!r}")
'''


def capture_ururu_forced_refresh_animation_qa_v729() -> None:
    if not SOURCE.is_file():
        raise FileNotFoundError(SOURCE)
    source = SOURCE.read_text(encoding="utf-8")
    required = (OLD_MESH, OLD_STATES, OLD_APPLY)
    if source.count("v709") < 10 or not all(value in source for value in required):
        raise RuntimeError("sealed v709 animation protocol changed unexpectedly")
    source = source.replace(OLD_MESH, COMBINED_MESH)
    source = source.replace(OLD_STATES, PEAK_STATES)
    source = source.replace(OLD_APPLY, REFRESHED_APPLY)
    source = source.replace("v709", "v729").replace("V709", "V729")
    exec(compile(source, str(SOURCE) + "::v729", "exec"), {"__name__": "__main__"})


capture_ururu_forced_refresh_animation_qa_v729()
