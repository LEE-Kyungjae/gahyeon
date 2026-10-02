"""Open the saved v068 Identity, then solve after its toolkit becomes command-ready."""

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import unreal


IDENTITY = "/Game/Gahyeon/CharacterPipeline/v068/Identity/MHI_Gahyeon_HeadOnly_v068"
IDENTITY_DIR = "/Game/Gahyeon/CharacterPipeline/v068/Identity"
INPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/metahuman-identity-head-only-v068/"
    "gahyeon-metahuman-head-only-v068.obj"
)
_callback = None
_ticks = 0


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _run_v068_solve(_delta_seconds):
    global _callback, _ticks
    _ticks += 1
    if _ticks < 2:
        return
    handle = _callback
    _callback = None
    unreal.unregister_slate_post_tick_callback(handle)
    identity = unreal.EditorAssetLibrary.load_asset(IDENTITY)
    result = unreal.GahyeonMetaHumanQALibrary.track_and_conform_identity(IDENTITY)
    success = bool(result[0]) if isinstance(result, tuple) else bool(result)
    diagnostic = str(result[1]) if isinstance(result, tuple) and len(result) > 1 else str(result)
    if not success:
        raise RuntimeError(f"v068 deferred solve failed: {diagnostic}")
    if not unreal.EditorAssetLibrary.save_loaded_asset(identity, only_if_is_dirty=False):
        raise RuntimeError("failed to save solved v068 Identity")
    if not unreal.EditorAssetLibrary.save_directory(IDENTITY_DIR, only_if_is_dirty=False, recursive=True):
        raise RuntimeError("failed to save solved v068 Identity dependencies")
    workspace = Path(os.environ.get("GAHYEON_WORKSPACE", "/Users/ze/work/gahyeonbot"))
    receipt = workspace / "artifacts/gahyeon-ch/metahuman-head-only-v068-solve.json"
    if receipt.exists():
        raise RuntimeError(f"refusing to overwrite immutable solve receipt: {receipt}")
    value = {
        "schemaVersion": 1,
        "observedAt": datetime.now(timezone.utc).isoformat(),
        "iteration": "v068",
        "input": {"path": str(INPUT), "sha256": _sha256(INPUT)},
        "identityAsset": IDENTITY,
        "identityAssets": list(unreal.EditorAssetLibrary.list_assets(IDENTITY_DIR, recursive=True, include_folder=False)),
        "result": "SUCCESS",
        "diagnostic": diagnostic,
        "bridgeFix": "reuse-open-identity-toolkit-without-close-reopen",
        "orchestration": "saved-identity-open-then-two-slate-ticks",
        "status": "draft",
        "automaticApproval": False,
        "identityApproved": False,
        "productionReady": False,
        "aaaQualityClaim": False,
    }
    receipt.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    unreal.log(f"Gahyeon v068 deferred Identity solve complete: {json.dumps(value)}")


def resume_head_only_solve_v068_async():
    global _callback
    identity = unreal.EditorAssetLibrary.load_asset(IDENTITY)
    if identity is None or identity.get_class().get_name() != "MetaHumanIdentity":
        raise RuntimeError(f"v068 Identity is unavailable: {IDENTITY}")
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).open_editor_for_assets([identity])
    _callback = unreal.register_slate_post_tick_callback(_run_v068_solve)


resume_head_only_solve_v068_async()
