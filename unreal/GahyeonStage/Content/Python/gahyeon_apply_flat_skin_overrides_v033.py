"""Apply v033 flat-skin material instances to the already-open map."""

import unreal


REPLACEMENT_PATHS = (
    "/Game/Gahyeon/CharacterPipeline/v033/Materials/MI_Face_Skin_Baked_LOD3_FlatSkin_v033",
    "/Game/Gahyeon/CharacterPipeline/v033/Materials/MI_Face_Skin_Baked_LOD5to7_FlatSkin_v033",
    "/Game/Gahyeon/CharacterPipeline/v033/Materials/MI_Body_Baked_FlatSkin_v033",
)

replacements = {}
for path in REPLACEMENT_PATHS:
    material = unreal.EditorAssetLibrary.load_asset(path)
    if material is None:
        raise RuntimeError(f"replacement material is unavailable: {path}")
    replacements[material.get_name().removesuffix("_FlatSkin_v033")] = material

actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
replaced = 0
for actor in actors.get_all_level_actors():
    for component in actor.get_components_by_class(unreal.MeshComponent):
        for slot in range(component.get_num_materials()):
            current = component.get_material(slot)
            replacement = replacements.get(current.get_name()) if current else None
            if replacement is not None:
                component.set_material(slot, replacement)
                replaced += 1
if replaced != 3:
    raise RuntimeError(f"expected 3 flat-skin overrides, got {replaced}")
if not unreal.EditorLevelLibrary.save_current_level():
    raise RuntimeError("failed to save v033 flat-skin preview")
unreal.log(f"Gahyeon v033 flat-skin overrides saved: slots={replaced}")

