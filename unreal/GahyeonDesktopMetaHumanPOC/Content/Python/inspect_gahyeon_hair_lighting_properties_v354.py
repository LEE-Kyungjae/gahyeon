"""Discover UE 5.8 Hair Groom lighting and shadow properties without mutation."""

import json
from pathlib import Path

import unreal


BLUEPRINT = (
    "/Game/Gahyeon/CharacterPipeline/v244/AssembledMedium/"
    "Gahyeon_AnimationPOC_v244/BP_Gahyeon_AnimationPOC_v244"
)
REPORT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v354-gahyeon-hair-lighting-properties/report.json"
)


def hair_template(blueprint):
    subsystem = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    library = unreal.SubobjectDataBlueprintFunctionLibrary
    for handle in subsystem.k2_gather_subobject_data_for_blueprint(blueprint):
        data = library.get_data(handle)
        if str(library.get_variable_name(data)) != "Hair":
            continue
        value = library.get_object_for_blueprint(data, blueprint)
        if isinstance(value, unreal.GroomComponent):
            return value
    raise RuntimeError("Hair Groom template unavailable")


def inspect_gahyeon_hair_lighting_properties_v354():
    blueprint = unreal.load_asset(BLUEPRINT)
    if blueprint is None:
        raise RuntimeError(f"blueprint unavailable: {BLUEPRINT}")
    hair = hair_template(blueprint)
    candidates = sorted(
        name for name in dir(hair)
        if any(token in name.lower() for token in ("shadow", "light", "occlusion", "ray"))
    )
    properties = {}
    for name in candidates:
        try:
            value = hair.get_editor_property(name)
            properties[name] = value if isinstance(value, (bool, int, float, str)) else str(value)
        except Exception:
            continue
    report = {
        "schemaVersion": 1,
        "iteration": "v354",
        "status": "read-only-hair-lighting-property-discovery",
        "blueprint": BLUEPRINT,
        "hairTemplate": str(hair.get_path_name()),
        "candidateNames": candidates,
        "readableProperties": properties,
        "mutatedAssets": [],
        "humanApproved": False,
        "productionReady": False,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=False)
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    unreal.log("GAHYEON_V354_HAIR_LIGHTING=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()


inspect_gahyeon_hair_lighting_properties_v354()
