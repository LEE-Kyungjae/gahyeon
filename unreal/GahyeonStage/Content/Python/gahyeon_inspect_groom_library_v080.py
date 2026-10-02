"""Inspect the UE 5.8 Python GroomLibrary binding surface."""

import json
from pathlib import Path

import unreal


OUTPUT = Path("/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/v080-groom-binding/library-api.json")
if OUTPUT.exists():
    raise RuntimeError(f"refusing to overwrite v080 library API inspection: {OUTPUT}")
methods = {}
for name in dir(unreal.GroomLibrary):
    if "binding" in name.lower() or "groom" in name.lower():
        member = getattr(unreal.GroomLibrary, name)
        methods[name] = getattr(member, "__doc__", None)
OUTPUT.write_text(json.dumps({
    "schemaVersion": 1,
    "iteration": "v080",
    "state": "read-only-groom-library-inspection",
    "methods": methods,
    "optionsDoc": unreal.GroomCreateBindingOptions.__doc__,
    "automaticApproval": False,
    "productionReady": False,
}, indent=2) + "\n", encoding="utf-8")
unreal.SystemLibrary.quit_editor()
