"""Run the v400 jaw capture as immutable v401 with UE async-script lifetime enabled."""

from pathlib import Path

import unreal


def capture_evaluated_hayley_jaw_v401():
    unreal.EditorPythonScripting.set_keep_python_script_alive(True)
    source_path = Path(__file__).with_name("capture_evaluated_hayley_jaw_v400.py")
    source = source_path.read_text()
    source = source.replace("v400", "v401").replace("V400", "V401")
    exec(compile(source, str(source_path), "exec"), {"__name__": "__main__"})


capture_evaluated_hayley_jaw_v401()
