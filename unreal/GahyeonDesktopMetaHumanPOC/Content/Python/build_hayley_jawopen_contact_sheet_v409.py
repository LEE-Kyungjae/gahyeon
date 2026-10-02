"""Run the v407 jawOpen QA scene at the measured v406 mesh scale of 1.0."""

from pathlib import Path


def capture_hayley_jawopen_contact_sheet_v409():
    source_path = Path(__file__).with_name("build_hayley_jawopen_contact_sheet_v407.py")
    source = source_path.read_text()
    source = source.replace("v407", "v409").replace("V407", "V409")
    source = source.replace(
        'actor.set_actor_scale3d(unreal.Vector(0.1, 0.1, 0.1))',
        'actor.set_actor_scale3d(unreal.Vector(1.0, 1.0, 1.0))',
    )
    exec(compile(source, str(source_path), "exec"), {"__name__": "__main__"})


capture_hayley_jawopen_contact_sheet_v409()
