"""Open any explicit MetaHuman Character for read-only visual review."""

import os

import unreal


_review_callback = None


def open_metahuman_review(_delta_seconds):
    global _review_callback
    unreal.unregister_slate_post_tick_callback(_review_callback)
    _review_callback = None
    asset_path = os.environ.get("METAHUMAN_REVIEW_ASSET", "")
    if not asset_path.startswith("/Game/"):
        raise RuntimeError("METAHUMAN_REVIEW_ASSET must name an explicit /Game asset")
    character = unreal.load_asset(asset_path)
    if character is None or character.get_class().get_name() != "MetaHumanCharacter":
        raise RuntimeError(f"MetaHuman review asset unavailable: {asset_path}")
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).open_editor_for_assets([character])
    unreal.EditorPythonScripting.set_keep_python_script_alive(True)
    unreal.log(f"Read-only MetaHuman review opened: {asset_path}")


_review_callback = unreal.register_slate_post_tick_callback(open_metahuman_review)
