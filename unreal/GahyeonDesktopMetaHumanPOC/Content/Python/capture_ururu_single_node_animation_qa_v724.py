"""Evaluate Ururu facial curves through UE's exposed Single Node animation path."""

from __future__ import annotations

from pathlib import Path


SOURCE = Path(__file__).with_name("capture_ururu_ue_animation_qa_v709.py")
OLD_STATES = 'STATES = (("neutral", 1), ("blink", 10), ("gaze-left", 20), ("gaze-right", 30))'
PEAK_STATES = 'STATES = (("neutral", 0), ("blink", 9), ("gaze-left", 19), ("gaze-right", 29))'
OLD_EVALUATION = "            self.component.override_animation_data(self.animation, False, False, position, 0.0)"
SINGLE_NODE_EVALUATION = '''            self.component.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
            self.component.play_animation(self.animation, False)
            self.component.set_position(position, False)'''


def capture_ururu_single_node_animation_qa_v724() -> None:
    if not SOURCE.is_file():
        raise FileNotFoundError(SOURCE)
    source = SOURCE.read_text(encoding="utf-8")
    if source.count("v709") < 10 or OLD_STATES not in source or OLD_EVALUATION not in source:
        raise RuntimeError("sealed v709 animation protocol changed unexpectedly")
    source = source.replace(OLD_STATES, PEAK_STATES)
    source = source.replace(OLD_EVALUATION, SINGLE_NODE_EVALUATION)
    source = source.replace("v709", "v724").replace("V709", "V724")
    exec(compile(source, str(SOURCE) + "::v724", "exec"), {"__name__": "__main__"})


capture_ururu_single_node_animation_qa_v724()
