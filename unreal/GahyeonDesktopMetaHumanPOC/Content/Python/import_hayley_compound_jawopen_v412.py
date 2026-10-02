"""Import the v411 compound jawOpen proof into an immutable UE path."""

from pathlib import Path


def import_hayley_compound_jawopen_v412():
    source_path = Path(__file__).with_name("import_hayley_jawopen_v406.py")
    source = source_path.read_text()
    source = source.replace("v406", "v412").replace("V406", "V412")
    source = source.replace(
        "living-character-poc-v405-hayley-jawopen/Hayley_JawOpen_v405.fbx",
        "living-character-poc-v411-hayley-compound-jawopen/Hayley_CompoundJawOpen_v411.fbx",
    )
    source = source.rsplit("\nimport_hayley_jawopen_v412()\n", 1)[0] + "\n"
    namespace = {"__name__": "hayley_compound_jawopen_v412"}
    exec(compile(source, str(source_path), "exec"), namespace)
    namespace["import_hayley_jawopen_v412"]()


import_hayley_compound_jawopen_v412()
