"""Inspect direct scalar override associations on Gahyeon's body material."""

import json
from pathlib import Path

import unreal


MATERIAL = (
    "/Game/Gahyeon/CharacterPipeline/v244/AssembledMedium/"
    "Gahyeon_AnimationPOC_v244/Body/Materials/MI_Body_Baked"
)
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v304-gahyeon-body-scalar-overrides/report.json"
)


def inspect_scalar_overrides(material):
    result = []
    for item in material.get_editor_property("scalar_parameter_values"):
        info = item.get_editor_property("parameter_info")
        result.append(
            {
                "name": str(info.get_editor_property("name")),
                "association": str(info.get_editor_property("association")),
                "index": int(info.get_editor_property("index")),
                "value": float(item.get_editor_property("parameter_value")),
            }
        )
    return result


material = unreal.EditorAssetLibrary.load_asset(MATERIAL)
if material is None:
    raise RuntimeError(f"material unavailable: {MATERIAL}")
report = {
    "schemaVersion": 1,
    "iteration": "v304",
    "status": "read-only-body-scalar-override-inspection",
    "material": MATERIAL,
    "scalarOverrides": inspect_scalar_overrides(material),
    "mutatedAssets": [],
    "humanApproved": False,
    "productionReady": False,
}
OUTPUT.parent.mkdir(parents=True, exist_ok=False)
OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
unreal.log("GAHYEON_V304_BODY_OVERRIDES=" + json.dumps(report, sort_keys=True))
unreal.SystemLibrary.quit_editor()
