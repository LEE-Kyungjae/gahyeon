"""Probe whether v024 can be previewed or assembled without opening its asset editor."""

import unreal


CHARACTER_PATH = "/Game/Gahyeon/CharacterPipeline/v024/Character/MHC_Gahyeon_CoarsePOC_v024"


def probe():
    character = unreal.EditorAssetLibrary.load_asset(CHARACTER_PATH)
    if character is None:
        raise RuntimeError(f"MetaHuman Character is unavailable: {CHARACTER_PATH}")
    subsystem = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
    if not subsystem.try_add_object_to_edit(character):
        raise RuntimeError("failed to initialize lightweight MetaHuman editing state")
    try:
        can_build = subsystem.can_build_meta_human(character, True)
        preview_collection = subsystem.get_preview_collection(character)
        unreal.log(
            "Gahyeon v024 probe: "
            f"canBuild={can_build} "
            f"previewCollection={preview_collection.get_path_name() if preview_collection else 'none'}"
        )
    finally:
        subsystem.remove_object_to_edit(character)


probe()
