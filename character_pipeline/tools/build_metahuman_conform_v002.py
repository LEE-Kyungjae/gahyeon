#!/usr/bin/env python3
"""Build/verify a v002 conform job only from accepted human-reviewed solve evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from character_pipeline.tools.verify_metahuman_identity_solve_evidence import verify as verify_solve


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict:
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"missing or unsafe input: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def build(evidence_path: Path, character_asset: str) -> dict:
    evidence_path = evidence_path.resolve()
    result = verify_solve(evidence_path)
    if result.get("conformAllowed") is not True or result.get("decision") != "keep-for-conform":
        raise ValueError("human-reviewed Identity decision does not allow conform")
    evidence = load(evidence_path)
    identity = evidence["identityAsset"]
    if not character_asset.startswith("/Game/") or character_asset == identity["path"]:
        raise ValueError("target MetaHuman Character asset path invalid")
    return {
        "schemaVersion": 1,
        "jobId": "gahyeon-metahuman-conform-v002",
        "state": "ready-to-conform-from-reviewed-identity",
        "engine": "5.6",
        "solvedIdentityEvidence": {"path": str(evidence_path), "sha256": sha256(evidence_path)},
        "identityAsset": identity,
        "characterAsset": {"path": character_asset, "expectedClass": "MetaHumanCharacter"},
        "operation": "MetaHumanCharacterEditorSubsystem.import_from_identity",
        "params": {"useEyeMeshes": True, "useTeethMesh": True, "useMetricScale": True},
        "requiredResult": "SUCCESS",
        "replaceExisting": False,
        "automaticApproval": False,
        "productionReady": False,
        "qualityClaim": None,
        "nextState": "conformed-head-awaiting-rig-surface-groom-body-deformation-and-go-qa",
    }


def verify(job_path: Path, receipt_path: Path | None = None) -> dict:
    job = load(job_path)
    if (job.get("jobId") != "gahyeon-metahuman-conform-v002"
            or job.get("state") != "ready-to-conform-from-reviewed-identity"
            or job.get("engine") != "5.6"):
        raise ValueError("unsupported v002 conform job")
    evidence_item = job.get("solvedIdentityEvidence", {})
    evidence_path = Path(evidence_item.get("path", ""))
    if (not evidence_path.is_absolute() or not evidence_path.is_file() or evidence_path.is_symlink()
            or sha256(evidence_path) != evidence_item.get("sha256")):
        raise ValueError("conform solve evidence lineage differs")
    solve_result = verify_solve(evidence_path)
    if solve_result.get("conformAllowed") is not True:
        raise ValueError("conform no longer allowed by reviewed evidence")
    evidence = load(evidence_path)
    if job.get("identityAsset") != evidence.get("identityAsset"):
        raise ValueError("Identity asset differs from reviewed evidence")
    if job.get("params") != {"useEyeMeshes": True, "useTeethMesh": True, "useMetricScale": True}:
        raise ValueError("identity-preservation parameters differ")
    if (job.get("operation") != "MetaHumanCharacterEditorSubsystem.import_from_identity"
            or job.get("requiredResult") != "SUCCESS" or job.get("replaceExisting") is not False
            or job.get("automaticApproval") is not False or job.get("productionReady") is not False
            or job.get("qualityClaim") is not None):
        raise ValueError("conform safety policy differs")
    if receipt_path:
        receipt = load(receipt_path)
        if receipt.get("state") != "conformed-head-awaiting-production-systems":
            raise ValueError("conform receipt state differs")
        if receipt.get("job") != {"path": str(job_path), "sha256": sha256(job_path)}:
            raise ValueError("conform receipt job lineage differs")
        if receipt.get("result") != "SUCCESS" or receipt.get("headConformed") is not True:
            raise ValueError("conform receipt lacks SUCCESS")
        forbidden_true = ("faceRigGenerated", "highResolutionTexturesDownloaded", "bodyConformed",
                          "groomBound", "clothingBound", "deformationValidated", "lookingGlassGoValidated",
                          "automaticApproval", "productionReady")
        if any(receipt.get(key) is not False for key in forbidden_true) or receipt.get("qualityClaim") is not None:
            raise ValueError("conform receipt overclaims downstream quality")
    return {"valid": True, "state": job["state"], "requiredResult": "SUCCESS",
            "productionReady": False, "qualityClaim": None}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", type=Path)
    parser.add_argument("--character-asset")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    if args.verify:
        result = verify(args.output.resolve(), args.receipt.resolve() if args.receipt else None)
    else:
        if not args.evidence or not args.character_asset:
            parser.error("--evidence and --character-asset are required")
        if args.output.exists():
            raise SystemExit(f"refusing to overwrite: {args.output}")
        result = build(args.evidence, args.character_asset)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"valid": True, "state": result["state"], "productionReady": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
