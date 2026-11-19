"""Capture UE 5.8 Python surface for automated Groom Binding creation."""

import json
from pathlib import Path

import unreal


OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/ue58-groom-binding-python-api.json"
)
class_names = (
    "GroomBindingAsset",
    "GroomBindingAssetFactory",
    "GroomComponent",
    "HairStrandsFactory",
)
payload = {}
for class_name in class_names:
    cls = getattr(unreal, class_name, None)
    if cls is None:
        payload[class_name] = None
        continue
    record = {"classDir": sorted(name for name in dir(cls) if not name.startswith("__"))}
    try:
        instance = cls()
        record["instanceDir"] = sorted(
            name for name in dir(instance) if not name.startswith("__")
        )
    except Exception as exc:
        record["instanceError"] = repr(exc)
    payload[class_name] = record

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
unreal.log(f"Gahyeon UE 5.8 Groom Binding API audit saved: {OUTPUT}")
