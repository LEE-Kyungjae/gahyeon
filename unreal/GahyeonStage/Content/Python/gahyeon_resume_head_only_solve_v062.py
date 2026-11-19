"""Resume the v062 Identity solve after its imported assets are already saved."""

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import unreal


IDENTITY = "/Game/Gahyeon/CharacterPipeline/v062/Identity/MHI_Gahyeon_HeadOnly_v062"
IDENTITY_DIR = "/Game/Gahyeon/CharacterPipeline/v062/Identity"
INPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/metahuman-identity-head-only-v062/"
    "gahyeon-metahuman-head-only-v062.obj"
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def resume_head_only_solve_v062():
    workspace = Path(os.environ.get("GAHYEON_WORKSPACE", "/Users/ze/work/gahyeonbot"))
    receipt = workspace / "artifacts/gahyeon-ch/metahuman-head-only-v062-solve.json"
    if receipt.exists():
        raise RuntimeError(f"refusing to overwrite immutable solve receipt: {receipt}")
    identity = unreal.EditorAssetLibrary.load_asset(IDENTITY)
    if identity is None or identity.get_class().get_name() != "MetaHumanIdentity":
        raise RuntimeError(f"v062 Identity is unavailable: {IDENTITY}")
    result = unreal.GahyeonMetaHumanQALibrary.track_and_conform_identity(IDENTITY)
    success = bool(result[0]) if isinstance(result, tuple) else bool(result)
    diagnostic = str(result[1]) if isinstance(result, tuple) and len(result) > 1 else str(result)
    if not success:
        raise RuntimeError(f"v062 resumed solve failed: {diagnostic}")
    if not unreal.EditorAssetLibrary.save_loaded_asset(identity, only_if_is_dirty=False):
        raise RuntimeError("failed to save solved v062 Identity")
    if not unreal.EditorAssetLibrary.save_directory(IDENTITY_DIR, only_if_is_dirty=False, recursive=True):
        raise RuntimeError("failed to save solved v062 Identity dependencies")
    assets = unreal.EditorAssetLibrary.list_assets(IDENTITY_DIR, recursive=True, include_folder=False)
    value = {
        "schemaVersion": 1,
        "observedAt": datetime.now(timezone.utc).isoformat(),
        "iteration": "v062",
        "input": {"path": str(INPUT), "sha256": _sha256(INPUT)},
        "identityAsset": IDENTITY,
        "identityAssets": list(assets),
        "result": "SUCCESS",
        "diagnostic": diagnostic,
        "hypothesis": "Landmark-driven front-face narrowing and vertical partitioning improves the v061 facial proportions.",
        "status": "draft",
        "automaticApproval": False,
        "identityApproved": False,
        "productionReady": False,
        "aaaQualityClaim": False,
    }
    receipt.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    unreal.log(f"Gahyeon v062 resumed Identity solve complete: {json.dumps(value)}")


resume_head_only_solve_v062()
