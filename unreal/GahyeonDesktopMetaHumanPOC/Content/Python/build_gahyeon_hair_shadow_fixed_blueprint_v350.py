"""Create a reusable Gahyeon Blueprint derivative with Hair cast shadow disabled."""

import json
from pathlib import Path

import unreal


SOURCE = (
    "/Game/Gahyeon/CharacterPipeline/v244/AssembledMedium/"
    "Gahyeon_AnimationPOC_v244/BP_Gahyeon_AnimationPOC_v244"
)
TARGET = (
    "/Game/Gahyeon/CharacterPipeline/v350/"
    "BP_Gahyeon_HairShadowFixed_v350"
)
REPORT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v350-gahyeon-hair-shadow-fixed-blueprint/report.json"
)


def hair_templates(blueprint):
    subsystem = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    library = unreal.SubobjectDataBlueprintFunctionLibrary
    unique = {}
    for handle in subsystem.k2_gather_subobject_data_for_blueprint(blueprint):
        data = library.get_data(handle)
        if str(library.get_variable_name(data)) != "Hair":
            continue
        value = library.get_object_for_blueprint(data, blueprint)
        if isinstance(value, unreal.GroomComponent):
            unique[str(value.get_path_name())] = value
    return list(unique.values())


def build_gahyeon_hair_shadow_fixed_blueprint_v350():
    if unreal.EditorAssetLibrary.does_asset_exist(TARGET):
        raise RuntimeError(f"refusing to overwrite immutable Blueprint: {TARGET}")
    if not unreal.EditorAssetLibrary.duplicate_asset(SOURCE, TARGET):
        raise RuntimeError("failed to duplicate Gahyeon production Blueprint")
    blueprint = unreal.load_asset(TARGET)
    if blueprint is None:
        raise RuntimeError(f"duplicated Blueprint unavailable: {TARGET}")
    templates = hair_templates(blueprint)
    if len(templates) != 1:
        raise RuntimeError(f"expected one unique Hair template, got {templates}")
    hair = templates[0]
    before = bool(hair.get_editor_property("cast_shadow"))
    hair.set_editor_property("cast_shadow", False)
    unreal.BlueprintEditorLibrary.compile_blueprint(blueprint)
    if not unreal.EditorAssetLibrary.save_loaded_asset(blueprint, only_if_is_dirty=False):
        raise RuntimeError("failed to save Hair-shadow-fixed Blueprint")
    reloaded = unreal.load_asset(TARGET)
    verified_templates = hair_templates(reloaded)
    if len(verified_templates) != 1:
        raise RuntimeError("Hair template missing after Blueprint compile")
    after = bool(verified_templates[0].get_editor_property("cast_shadow"))
    if after:
        raise RuntimeError("Hair cast_shadow remained enabled after save")
    report = {
        "schemaVersion": 1,
        "iteration": "v350",
        "status": "draft-hair-shadow-fixed-blueprint-built",
        "source": SOURCE,
        "blueprint": TARGET,
        "hairTemplate": str(verified_templates[0].get_path_name()),
        "castShadowBefore": before,
        "castShadowAfter": after,
        "identityChanged": False,
        "visualValidationPending": True,
        "humanApproved": False,
        "productionReady": False,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=False)
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    unreal.log("GAHYEON_V350_BLUEPRINT=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()


build_gahyeon_hair_shadow_fixed_blueprint_v350()
