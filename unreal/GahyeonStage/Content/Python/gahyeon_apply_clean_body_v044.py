"""Replace the baked gray body texture with the skin-only v044 material."""

import unreal


MATERIAL_PATH = "/Game/Gahyeon/CharacterPipeline/v044/Materials/M_Body_SkinLit_v044"

material = unreal.EditorAssetLibrary.load_asset(MATERIAL_PATH)
if material is None:
    raise RuntimeError(f"v044 body material is unavailable: {MATERIAL_PATH}")

replacements = 0
for actor in unreal.EditorLevelLibrary.get_all_level_actors():
    for component in actor.get_components_by_class(unreal.SkeletalMeshComponent):
        if component.get_name() != "Body":
            continue
        if component.get_num_materials() != 1:
            raise RuntimeError(
                f"expected one Body material slot, got {component.get_num_materials()}"
            )
        component.set_material(0, material)
        replacements += 1

if replacements != 1:
    raise RuntimeError(f"expected one Body replacement, got {replacements}")
if not unreal.EditorLevelLibrary.save_current_level():
    raise RuntimeError("failed to save v044 clean-body preview")
unreal.log("Gahyeon v044 clean-body preview saved: slots=1")
