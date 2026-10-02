"""Apply saved flat-normal material overrides to the already-open v028 map."""

import unreal


TARGET_MAP = "/Game/Gahyeon/CharacterPipeline/v028/Preview/L_Skotukeda_FlatNormal_v028"
REPLACEMENT_PATHS = (
    "/Game/Gahyeon/CharacterPipeline/v028/Materials/MI_Face_Skin_Baked_LOD3_FlatNormal_v028",
    "/Game/Gahyeon/CharacterPipeline/v028/Materials/MI_Face_Skin_Baked_LOD5to7_FlatNormal_v028",
    "/Game/Gahyeon/CharacterPipeline/v028/Materials/MI_Body_Baked_FlatNormal_v028",
)

replacements = {}
for path in REPLACEMENT_PATHS:
    material = unreal.EditorAssetLibrary.load_asset(path)
    if material is None:
        raise RuntimeError(f"replacement material is unavailable: {path}")
    source_name = material.get_name().removesuffix("_FlatNormal_v028")
    replacements[source_name] = material

actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
replaced_slots = 0
for actor in actors.get_all_level_actors():
    for component in actor.get_components_by_class(unreal.MeshComponent):
        for slot in range(component.get_num_materials()):
            current = component.get_material(slot)
            if current is None:
                continue
            replacement = replacements.get(current.get_name())
            if replacement is not None:
                component.set_material(slot, replacement)
                replaced_slots += 1
if replaced_slots == 0:
    raise RuntimeError("no assembled skin material slots were replaced")
if not unreal.EditorLevelLibrary.save_current_level():
    raise RuntimeError(f"failed to save flat-normal preview: {TARGET_MAP}")
unreal.log(f"Gahyeon v028 flat-normal overrides saved: slots={replaced_slots}")

