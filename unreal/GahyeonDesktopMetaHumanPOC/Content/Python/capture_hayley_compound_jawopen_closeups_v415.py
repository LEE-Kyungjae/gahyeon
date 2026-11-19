"""Capture neutral/compound-open/return close-ups from the v414 QA map."""

from pathlib import Path


def capture_hayley_compound_jawopen_closeups_v415():
    source_path = Path(__file__).with_name("capture_hayley_jawopen_closeups_v410.py")
    source = source_path.read_text()
    source = source.replace("v410", "v415").replace("V410", "V415")
    source = source.replace("v409", "v414").replace("V409", "V414")
    source = source.replace("jaw-open-18deg", "compound-jaw-open")
    exec(compile(source, str(source_path), "exec"), {"__name__": "__main__"})


capture_hayley_compound_jawopen_closeups_v415()
