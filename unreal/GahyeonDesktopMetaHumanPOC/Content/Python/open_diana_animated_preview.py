"""Open and play Diana's corrected A-pose idle QA sequence in the editor."""

import unreal


MAP = "/Game/Gahyeon/Character2/Diana/v050/QA/L_Diana_VisiblePrimaryChain_v050"
SEQUENCE = "/Game/Gahyeon/Character2/Diana/v346/Sequence/LS_Diana_APoseIdleQA_v346"

unreal.EditorLoadingAndSavingUtils.load_map(MAP)
sequence = unreal.load_asset(SEQUENCE)
if sequence is None:
    raise RuntimeError(f"Diana animated preview sequence is unavailable: {SEQUENCE}")
if not unreal.LevelSequenceEditorBlueprintLibrary.open_level_sequence(sequence):
    raise RuntimeError(f"Could not open Diana animated preview sequence: {SEQUENCE}")
unreal.LevelSequenceEditorBlueprintLibrary.set_current_time(1)
unreal.LevelSequenceEditorBlueprintLibrary.force_update()
unreal.LevelSequenceEditorBlueprintLibrary.play()
unreal.log("DIANA_ANIMATED_PREVIEW_PLAYING=" + SEQUENCE)
