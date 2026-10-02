"""Inspect Gahyeon's Blueprint SCS component templates without mutation."""

import json
from pathlib import Path

import unreal


BLUEPRINT = (
    "/Game/Gahyeon/CharacterPipeline/v244/AssembledMedium/"
    "Gahyeon_AnimationPOC_v244/BP_Gahyeon_AnimationPOC_v244"
)
REPORT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v349-gahyeon-blueprint-subobjects/report.json"
)


def inspect_gahyeon_blueprint_subobjects_v349():
    blueprint = unreal.load_asset(BLUEPRINT)
    if blueprint is None:
        raise RuntimeError(f"blueprint unavailable: {BLUEPRINT}")
    subsystem = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    handles = subsystem.k2_gather_subobject_data_for_blueprint(blueprint)
    library = unreal.SubobjectDataBlueprintFunctionLibrary
    objects = []
    for handle in handles:
        data = library.get_data(handle)
        value = library.get_object_for_blueprint(data, blueprint)
        objects.append(
            {
                "displayName": str(library.get_display_name(data)),
                "variableName": str(library.get_variable_name(data)),
                "class": str(value.get_class().get_name()) if value is not None else None,
                "path": str(value.get_path_name()) if value is not None else None,
                "castShadow": (
                    bool(value.get_editor_property("cast_shadow"))
                    if isinstance(value, unreal.GroomComponent)
                    else None
                ),
            }
        )
    report = {
        "schemaVersion": 1,
        "iteration": "v349",
        "status": "read-only-blueprint-subobject-inspection",
        "blueprint": BLUEPRINT,
        "subobjectCount": len(objects),
        "subobjects": objects,
        "hairTemplates": [item for item in objects if item["variableName"] == "Hair"],
        "mutatedAssets": [],
        "humanApproved": False,
        "productionReady": False,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=False)
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    unreal.log("GAHYEON_V349_SUBOBJECTS=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()


inspect_gahyeon_blueprint_subobjects_v349()
