"""Apply the engine default lit material to skin slots in the open v029 map."""

import unreal


DEFAULT_MATERIAL = "/Engine/EngineMaterials/DefaultMaterial"
TARGET_COMPONENT_SLOTS = {"Body": (0,), "Face": (6, 7)}

material = unreal.EditorAssetLibrary.load_asset(DEFAULT_MATERIAL)
if material is None:
    raise RuntimeError(f"default material is unavailable: {DEFAULT_MATERIAL}")
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
replaced = 0
for actor in actors.get_all_level_actors():
    for component in actor.get_components_by_class(unreal.MeshComponent):
        slots = TARGET_COMPONENT_SLOTS.get(component.get_name())
        if slots is None:
            continue
        for slot in slots:
            component.set_material(slot, material)
            replaced += 1
if replaced != 3:
    raise RuntimeError(f"expected 3 simple-lit overrides, got {replaced}")
if not unreal.EditorLevelLibrary.save_current_level():
    raise RuntimeError("failed to save v029 simple-lit preview")
unreal.log(f"Gahyeon v029 simple-lit overrides saved: slots={replaced}")

