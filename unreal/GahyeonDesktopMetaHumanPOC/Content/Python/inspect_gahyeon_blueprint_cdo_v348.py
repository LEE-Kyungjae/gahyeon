"""Inspect the production Gahyeon Blueprint CDO Groom defaults without mutation."""

import json
from pathlib import Path

import unreal


BLUEPRINT = (
    "/Game/Gahyeon/CharacterPipeline/v244/AssembledMedium/"
    "Gahyeon_AnimationPOC_v244/BP_Gahyeon_AnimationPOC_v244"
)
REPORT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v348-gahyeon-blueprint-cdo/report.json"
)


def inspect_gahyeon_blueprint_cdo_v348():
    actor_class = unreal.EditorAssetLibrary.load_blueprint_class(BLUEPRINT)
    if actor_class is None:
        raise RuntimeError(f"blueprint class unavailable: {BLUEPRINT}")
    cdo = unreal.get_default_object(actor_class)
    components = []
    for component in cdo.get_components_by_class(unreal.GroomComponent):
        components.append(
            {
                "name": str(component.get_name()),
                "path": str(component.get_path_name()),
                "castShadow": bool(component.get_editor_property("cast_shadow")),
                "visible": bool(component.is_visible()),
                "hiddenInGame": bool(component.get_editor_property("hidden_in_game")),
            }
        )
    components.sort(key=lambda item: item["name"])
    hair = [item for item in components if item["name"] == "Hair"]
    report = {
        "schemaVersion": 1,
        "iteration": "v348",
        "status": "read-only-blueprint-cdo-inspection",
        "blueprint": BLUEPRINT,
        "class": str(actor_class.get_path_name()),
        "cdo": str(cdo.get_path_name()),
        "groomComponents": components,
        "hairComponentFound": len(hair) == 1,
        "mutatedAssets": [],
        "humanApproved": False,
        "productionReady": False,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=False)
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    unreal.log("GAHYEON_V348_CDO=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()


inspect_gahyeon_blueprint_cdo_v348()
