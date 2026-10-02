"""Apply v034 textured Default Lit materials to the open QA map."""

import unreal


BODY_MATERIAL = "/Game/Gahyeon/CharacterPipeline/v034/Materials/M_Body_TexturedLit_v034"
FACE_MATERIAL = "/Game/Gahyeon/CharacterPipeline/v034/Materials/M_Face_TexturedLit_v034"

body_material = unreal.EditorAssetLibrary.load_asset(BODY_MATERIAL)
face_material = unreal.EditorAssetLibrary.load_asset(FACE_MATERIAL)
if body_material is None or face_material is None:
    raise RuntimeError("v034 textured-lit materials are unavailable")
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
replaced = 0
for actor in actors.get_all_level_actors():
    for component in actor.get_components_by_class(unreal.MeshComponent):
        if component.get_name() == "Body":
            component.set_material(0, body_material)
            replaced += 1
        elif component.get_name() == "Face":
            component.set_material(6, face_material)
            component.set_material(7, face_material)
            replaced += 2
if replaced != 3:
    raise RuntimeError(f"expected 3 textured-lit overrides, got {replaced}")
if not unreal.EditorLevelLibrary.save_current_level():
    raise RuntimeError("failed to save v034 textured-lit preview")
unreal.log(f"Gahyeon v034 textured-lit overrides saved: slots={replaced}")

