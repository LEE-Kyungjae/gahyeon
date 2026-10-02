#!/usr/bin/env python3
"""Build a fail-closed production MetaHuman hero QA job after identity approval."""

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


def build(decision_path: Path, config_path: Path, output_dir: Path) -> dict:
    decision_path, config_path = decision_path.resolve(), config_path.resolve()
    decision, config = load(decision_path), load(config_path)
    if (decision.get("state") != "post-conform-identity-human-reviewed"
            or decision.get("comparison", {}).get("decision") != "keep-and-build-surfaces"
            or decision.get("blockingFindings")):
        raise ValueError("authorized keep-and-build-surfaces identity decision required")
    reviewer = decision.get("reviewer", {})
    if not reviewer.get("name") or reviewer.get("role") not in {
        "character-owner", "character-art-director", "character-technical-artist"
    }:
        raise ValueError("authorized named identity reviewer required")
    cases = config.get("requiredCases", [])
    if len(cases) != 15 or any(len(item.get("frames", [])) != 3 for item in cases):
        raise ValueError("exact fifteen three-frame deformation cases required")
    if (config.get("displayProfile") != "looking-glass-go"
            or config.get("resolution") != [1440, 2560]
            or config.get("approvalPolicy", {}).get("automaticApproval") is not False):
        raise ValueError("Looking Glass Go human-reviewed QA contract required")
    return {
        "schemaVersion": 1,
        "jobId": "gahyeon-metahuman-hero-qa-v002",
        "state": "awaiting-production-systems-and-editor-preflight",
        "identityDecision": {"path": str(decision_path), "sha256": sha256(decision_path)},
        "qaConfig": {"path": str(config_path), "sha256": sha256(config_path)},
        "heroBlueprint": config["heroBlueprint"],
        "display": {"profile": "looking-glass-go", "singleViewResolution": [1440, 2560],
                    "quiltViewCount": 66, "quiltRequiresConnectedCalibration": True},
        "fixedScene": {
            "level": "/Game/Gahyeon/CharacterPipeline/v002/QA/L_GahyeonHeroQA_v002",
            "sequence": "/Game/Gahyeon/CharacterPipeline/v002/QA/LS_GahyeonHeroQA_v002",
            "background": "neutral-mid-gray", "exposureMode": "manual",
            "cameras": ["face-close-up", "bust", "full-body", "left-45", "right-45", "left-profile", "right-profile"],
            "lighting": ["neutral-key", "neutral-fill", "neutral-rim"],
        },
        "productionSystemsRequired": {
            "metaHumanFacialRig": True, "layeredSkin": True, "wetEyesAndTearline": True,
            "strandGroom": True, "eyebrows": True, "eyelashes": True,
            "separateClothing": True, "bodyRig": True,
        },
        "cases": cases,
        "defectChecks": config["requiredChecks"],
        "outputDirectory": str(output_dir.resolve()),
        "completionEvidence": [
            "Editor runtime preflight receipt", "seven fixed-camera neutral renders",
            "45 deformation frames", "skin/eye/groom/clothing asset provenance",
            "defect findings with confidence", "authorized human keep/reject decision",
        ],
        "automaticApproval": False,
        "qualityClaim": None,
    }


def verify(job_path: Path) -> dict:
    job = load(job_path.resolve())
    if (job.get("jobId") != "gahyeon-metahuman-hero-qa-v002"
            or job.get("automaticApproval") is not False or job.get("qualityClaim") is not None):
        raise ValueError("hero QA job identity or claims differ")
    for key in ("identityDecision", "qaConfig"):
        item = job.get(key, {}); path = Path(item.get("path", ""))
        if not path.is_absolute() or not path.is_file() or path.is_symlink() or sha256(path) != item.get("sha256"):
            raise ValueError(f"hero QA lineage differs: {key}")
    if job.get("display") != {"profile": "looking-glass-go", "singleViewResolution": [1440, 2560],
                              "quiltViewCount": 66, "quiltRequiresConnectedCalibration": True}:
        raise ValueError("hero QA display contract differs")
    if len(job.get("cases", [])) != 15 or sum(len(item.get("frames", [])) for item in job["cases"]) != 45:
        raise ValueError("hero QA deformation matrix differs")
    if not all(job.get("productionSystemsRequired", {}).values()):
        raise ValueError("hero QA production-system coverage differs")
    return {"valid": True, "cases": 15, "frames": 45, "cameras": 7,
            "displayProfile": "looking-glass-go", "automaticApproval": False}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--decision", type=Path)
    parser.add_argument("--config", type=Path, default=Path("character_pipeline/config/deformation_qa.json"))
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.verify:
        result = verify(args.output)
    else:
        if not args.decision or not args.output_dir:
            parser.error("--decision and --output-dir required")
        if args.output.exists():
            raise SystemExit(f"refusing to overwrite: {args.output}")
        result = build(args.decision, args.config, args.output_dir)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
