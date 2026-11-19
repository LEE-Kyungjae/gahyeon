"""Reopen v075 and verify the wardrobe reset persisted exactly."""

import json
from pathlib import Path

import unreal


MAP = "/Game/Gahyeon/CharacterPipeline/v075/Preview/L_Skotukeda_WardrobeReset_v075"
EXPECTED_SKIN = (
    "/Game/Gahyeon/CharacterPipeline/v044/Materials/"
    "M_Body_SkinLit_v044.M_Body_SkinLit_v044"
)
EXPECTED_HIDDEN = {"DonorOutfit_top_v055", "DonorOutfit_bottom_v055"}
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v075-wardrobe-reset/validation.json"
)


if OUTPUT.exists():
    raise RuntimeError(f"refusing to overwrite immutable validation: {OUTPUT}")
world = unreal.EditorLoadingAndSavingUtils.load_map(MAP)
if world is None:
    raise RuntimeError(f"failed to reopen v075 map: {MAP}")

body_materials = []
hidden = []
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
for actor in actors:
    label = actor.get_actor_label()
    if label in EXPECTED_HIDDEN:
        components = actor.get_components_by_class(unreal.MeshComponent)
        if len(components) != 1:
            raise RuntimeError(f"unexpected donor component count after reload: {label}")
        component = components[0]
        if component.get_editor_property("visible") or not component.get_editor_property("hidden_in_game"):
            raise RuntimeError(f"rejected donor visibility persisted incorrectly: {label}")
        hidden.append(label)
    if label == "Skotukeda_Medium_v027":
        for component in actor.get_components_by_class(unreal.SkeletalMeshComponent):
            if component.get_name() == "Body":
                material = component.get_material(0)
                body_materials.append(material.get_path_name() if material is not None else None)

if body_materials != [EXPECTED_SKIN]:
    raise RuntimeError(f"skin-only Body material did not persist: {body_materials}")
if set(hidden) != EXPECTED_HIDDEN:
    raise RuntimeError(f"rejected donor pair did not persist hidden: {hidden}")

result = {
    "schemaVersion": 1,
    "iteration": "v075",
    "state": "validated-draft-diagnostic",
    "map": MAP,
    "bodyMaterial": body_materials[0],
    "hiddenDonorActors": sorted(hidden),
    "bakedBasewearVisible": False,
    "rejectedDonorVisible": False,
    "renderEvidenceComplete": False,
    "automaticApproval": False,
    "productionReady": False,
}
OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
unreal.log(f"Gahyeon v075 wardrobe reset validated: {OUTPUT}")
unreal.SystemLibrary.quit_editor()
