"""Apply the skeletal-mesh-safe v035 materials in a separately loaded editor run."""

import unreal


MATERIALS = {
    "M_Face_TexturedLit_v034": unreal.EditorAssetLibrary.load_asset(
        "/Game/Gahyeon/CharacterPipeline/v035/Materials/M_Face_TexturedLit_v035"
    ),
    "M_Body_TexturedLit_v034": unreal.EditorAssetLibrary.load_asset(
        "/Game/Gahyeon/CharacterPipeline/v035/Materials/M_Body_TexturedLit_v035"
    ),
}
if any(material is None for material in MATERIALS.values()):
    raise RuntimeError("v035 textured-lit materials are unavailable")

replacements = 0
for actor in unreal.EditorLevelLibrary.get_all_level_actors():
    for component in actor.get_components_by_class(unreal.SkeletalMeshComponent):
        for slot_index in range(component.get_num_materials()):
            current = component.get_material(slot_index)
            if current is None or current.get_name() not in MATERIALS:
                continue
            component.set_material(slot_index, MATERIALS[current.get_name()])
            replacements += 1

if replacements != 3:
    raise RuntimeError(f"expected 3 material replacements, got {replacements}")
unreal.EditorLevelLibrary.save_current_level()
unreal.log(f"Gahyeon v035 textured-lit overrides saved: slots={replacements}")
