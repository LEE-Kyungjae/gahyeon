"""Open the safe v243 Skotukeda complete-outfit working copy in the desktop POC editor."""

import unreal


ASSET_PATH = "/Game/Gahyeon/CharacterPipeline/v243/Character/MHC_Skotukeda_SweaterJeansHightop_v243"
_callback = None


def _open_skotukeda_poc(_delta_seconds):
    global _callback
    handle = _callback
    if handle is None:
        return

    asset = unreal.EditorAssetLibrary.load_asset(ASSET_PATH)
    if asset is None:
        # The startup script can run before the asset registry has discovered a
        # newly generated iteration. Keep the callback alive and retry next tick.
        return
    _callback = None
    unreal.unregister_slate_post_tick_callback(handle)
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).open_editor_for_assets([asset])
    unreal.log(f"Desktop POC opened MetaHumanCharacter: {ASSET_PATH}")


_command_line = unreal.SystemLibrary.get_command_line().lower()
_is_runtime = " -game" in _command_line or " -server" in _command_line
_is_automation = (
    "executepythonscript=" in _command_line
    or "-gahyeon_mrq_automation" in _command_line
)

if not _is_runtime and not _is_automation:
    _callback = unreal.register_slate_post_tick_callback(_open_skotukeda_poc)
