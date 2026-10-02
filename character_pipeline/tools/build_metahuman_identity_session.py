#!/usr/bin/env python3
"""Build an immutable, fail-closed first MetaHuman Identity session bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict:
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"missing or unsafe input: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def resolve(owner: Path, uri: str) -> Path:
    result = (owner.parent / uri).resolve()
    if not result.is_file() or result.is_symlink():
        raise ValueError(f"missing or unsafe referenced input: {result}")
    return result


def build(workspace: Path, handoff_path: Path, preflight_path: Path) -> dict:
    workspace = workspace.resolve()
    handoff_path = handoff_path.resolve()
    preflight_path = preflight_path.resolve()
    handoff = load(handoff_path)
    preflight = load(preflight_path)
    if handoff.get("iteration") != "v002" or handoff.get("stage") != "metahuman-identity-solve":
        raise ValueError("only immutable v002 MetaHuman Identity handoff is allowed")
    source = handoff.get("input", {})
    mesh = resolve(handoff_path, source.get("mesh", ""))
    manifest = resolve(handoff_path, source.get("manifest", ""))
    if sha256(mesh) != source.get("meshSha256") or sha256(manifest) != source.get("manifestSha256"):
        raise ValueError("v002 input lineage differs")
    capture = handoff.get("captureProtocol", {})
    if (capture.get("resolution") != [1440, 2560]
            or capture.get("quiltViewCount") != 66
            or capture.get("quiltRequiresConnectedCalibration") is not True
            or len(capture.get("views", [])) != 5):
        raise ValueError("Looking Glass Go capture contract differs")
    checks = preflight.get("checks", {})
    if checks.get("identityInputVerifiedShape") is not True or checks.get("immutableHandoffVerified") is not True:
        raise ValueError("preflight does not verify the exact shape and handoff")
    launch_ready = preflight.get("readyToLaunchIdentitySolve") is True
    editor = preflight.get("editor")
    if launch_ready and not editor:
        raise ValueError("ready preflight lacks Unreal Editor")
    hard_checks = {
        "launcherInstalled", "engineInstalled", "engineVersionSupported", "editorPresent",
        "metaHumanCoreDataPresent", "allRequiredPluginsPresent", "identityInputVerifiedShape",
        "immutableHandoffVerified", "minimumMemory", "minimumRuntimeFreeDiskHeadroom",
    }
    return {
        "schemaVersion": 1,
        "sessionId": "gahyeon-metahuman-identity-v002",
        "state": "ready-to-launch" if launch_ready else "blocked-before-launch",
        "qualityClaim": None,
        "workspace": str(workspace),
        "handoff": {"path": str(handoff_path), "sha256": sha256(handoff_path)},
        "preflight": {"path": str(preflight_path), "sha256": sha256(preflight_path)},
        "source": {"path": str(mesh), "sha256": sha256(mesh), "claim": source["claim"]},
        "unreal": {
            "editor": editor,
            "project": str(workspace / "unreal/GahyeonStage/GahyeonStage.uproject"),
            "identityAsset": "/Game/Gahyeon/CharacterPipeline/v002/Identity/MHI_Gahyeon_v002",
            "characterAsset": "/Game/Gahyeon/CharacterPipeline/v002/Character/MHC_Gahyeon_v002",
            "replaceExisting": False,
        },
        "guidedStages": [
            {"id": "import-static-shape", "automatic": True, "requiredEvidence": ["StaticMesh asset path", "source checksum"]},
            {"id": "components-from-mesh", "automatic": False, "requiredEvidence": ["promoted neutral frame", "component assignment"]},
            {"id": "marker-correction", "automatic": False, "requiredEvidence": ["front marker overlay", "profile marker overlay", "named reviewer"]},
            {"id": "identity-solve", "automatic": False, "requiredEvidence": ["solved Identity asset", "template A/B overlay"]},
            {"id": "conform-character", "automatic": True, "requiredEvidence": ["import_from_identity SUCCESS", "MetaHuman Character asset"]},
            {"id": "go-identity-capture", "automatic": True, "requiredEvidence": capture["views"]},
            {"id": "human-identity-decision", "automatic": False, "requiredEvidence": ["canonical 03/06/07/08 comparison", "keep/reject decision"]},
        ],
        "capture": capture,
        "blockedChecks": sorted(key for key in hard_checks if checks.get(key) is not True),
        "warningChecks": sorted(key for key, value in checks.items()
                                if key not in hard_checks and value is not True),
        "forbiddenClaimsUntilEvidence": handoff["forbiddenClaimsUntilEvidence"],
        "nextAction": (
            "launch Unreal Editor and execute guidedStages in order"
            if launch_ready else
            "satisfy every preflight check; do not launch or claim a MetaHuman solve"
        ),
    }


def verify(bundle_path: Path) -> dict:
    bundle = load(bundle_path)
    if bundle.get("sessionId") != "gahyeon-metahuman-identity-v002" or bundle.get("qualityClaim") is not None:
        raise ValueError("session identity or claim differs")
    for key in ("handoff", "preflight", "source"):
        value = bundle[key]
        path = Path(value["path"])
        if not path.is_absolute() or not path.is_file() or path.is_symlink() or sha256(path) != value["sha256"]:
            raise ValueError(f"session lineage differs: {key}")
    expected_stages = [
        "import-static-shape", "components-from-mesh", "marker-correction",
        "identity-solve", "conform-character", "go-identity-capture", "human-identity-decision",
    ]
    if [stage.get("id") for stage in bundle.get("guidedStages", [])] != expected_stages:
        raise ValueError("guided stage order differs")
    capture = bundle.get("capture", {})
    if capture.get("resolution") != [1440, 2560] or capture.get("quiltViewCount") != 66:
        raise ValueError("session is not bound to Looking Glass Go")
    preflight = load(Path(bundle["preflight"]["path"]))
    should_be_ready = preflight.get("readyToLaunchIdentitySolve") is True
    if (bundle.get("state") == "ready-to-launch") != should_be_ready:
        raise ValueError("session readiness contradicts preflight")
    if should_be_ready and bundle.get("blockedChecks"):
        raise ValueError("ready session contains blocked checks")
    if bundle.get("unreal", {}).get("replaceExisting") is not False:
        raise ValueError("session could overwrite an Unreal asset")
    return {"valid": True, "state": bundle["state"], "stages": 7,
            "displayProfile": "looking-glass-go", "qualityClaim": None}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--handoff", type=Path, default=Path("character_pipeline/metahuman/identity/v002/handoff.json"))
    parser.add_argument("--preflight", type=Path, default=Path("artifacts/gahyeon-ch/metahuman-toolchain-preflight-v3.json"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.verify:
        result = verify(args.output.resolve())
    else:
        if args.output.exists():
            raise SystemExit(f"refusing to overwrite: {args.output}")
        result = build(args.workspace, args.handoff, args.preflight)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"valid": True, "state": result["state"], "qualityClaim": None}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
