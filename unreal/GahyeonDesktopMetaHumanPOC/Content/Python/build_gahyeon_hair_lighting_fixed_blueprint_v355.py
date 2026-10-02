"""Create a Gahyeon Blueprint derivative with Hair shadow/AO participation disabled."""

import json
from pathlib import Path

import unreal


SOURCE = (
    "/Game/Gahyeon/CharacterPipeline/v244/AssembledMedium/"
    "Gahyeon_AnimationPOC_v244/BP_Gahyeon_AnimationPOC_v244"
)
TARGET = "/Game/Gahyeon/CharacterPipeline/v355/BP_Gahyeon_HairLightingFixed_v355"
REPORT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v355-gahyeon-hair-lighting-fixed-blueprint/report.json"
)
PROPERTIES = (
    "cast_shadow",
    "cast_contact_shadow",
    "affect_dynamic_indirect_lighting",
    "affect_distance_field_lighting",
    "visible_in_ray_tracing",
)


def hair_templates_v355(blueprint):
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


def property_state(component):
    return {name: bool(component.get_editor_property(name)) for name in PROPERTIES}


def build_gahyeon_hair_lighting_fixed_blueprint_v355():
    if unreal.EditorAssetLibrary.does_asset_exist(TARGET):
        raise RuntimeError(f"refusing to overwrite immutable Blueprint: {TARGET}")
    if not unreal.EditorAssetLibrary.duplicate_asset(SOURCE, TARGET):
        raise RuntimeError("failed to duplicate Gahyeon production Blueprint")
    blueprint = unreal.load_asset(TARGET)
    templates = hair_templates_v355(blueprint)
    if len(templates) != 1:
        raise RuntimeError(f"expected one unique Hair template, got {templates}")
    before = property_state(templates[0])
    for name in PROPERTIES:
        templates[0].set_editor_property(name, False)
    unreal.BlueprintEditorLibrary.compile_blueprint(blueprint)
    if not unreal.EditorAssetLibrary.save_loaded_asset(blueprint, only_if_is_dirty=False):
        raise RuntimeError("failed to save Hair-lighting-fixed Blueprint")
    reloaded = unreal.load_asset(TARGET)
    verified = hair_templates_v355(reloaded)
    if len(verified) != 1:
        raise RuntimeError("Hair template missing after Blueprint compile")
    after = property_state(verified[0])
    if any(after.values()):
        raise RuntimeError(f"Hair lighting properties remained enabled: {after}")
    report = {
        "schemaVersion": 1,
        "iteration": "v355",
        "status": "draft-hair-lighting-fixed-blueprint-built",
        "source": SOURCE,
        "blueprint": TARGET,
        "hairTemplate": str(verified[0].get_path_name()),
        "before": before,
        "after": after,
        "hairVisibilityChanged": False,
        "identityChanged": False,
        "hypothesis": (
            "The neck patch is caused by Groom contact/deep AO participation, so disabling "
            "Hair shadow, indirect-lighting, distance-field, and ray-tracing participation "
            "will preserve the groom while removing the false dark neck patch."
        ),
        "visualValidationPending": True,
        "humanApproved": False,
        "productionReady": False,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=False)
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    unreal.log("GAHYEON_V355_BLUEPRINT=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()


build_gahyeon_hair_lighting_fixed_blueprint_v355()
