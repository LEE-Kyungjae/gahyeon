#!/usr/bin/env python3
"""Statically verify the Editor-only character deformation QA contract."""

import argparse
import json
from pathlib import Path


REQUIRED_CASES = {
    "neutral", "blink-left", "blink-right", "blink-bilateral", "jaw-open",
    "smile", "frown", "eye-squint", "viseme-aa", "viseme-ee", "viseme-oo",
    "head-yaw", "head-pitch", "breathing", "shoulder-raise",
}
REQUIRED_CHECKS = {
    "lip-penetration", "lip-seal-gap", "eyelid-eyeball-contact",
    "eyelid-penetration", "mouth-corner-collapse", "cheek-volume-collapse",
    "neck-stretch", "shoulder-collapse", "eye-aim-consistency",
    "mesh-clipping", "temporal-popping",
}
REQUIRED_PLUGINS = {
    "PythonScriptPlugin", "EditorScriptingUtilities", "SequencerScripting",
    "MovieRenderPipeline", "ControlRig", "MetaHumanCreator", "MetaHumanAnimator",
    "MetaHumanAnimatorDepthProcessing", "RigLogic", "HairStrands",
}


def verify(config_path: Path, project_path: Path, script_path: Path) -> dict:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    project = json.loads(project_path.read_text(encoding="utf-8"))
    if project.get("EngineAssociation") != "5.6":
        raise ValueError("character QA project must remain pinned to UE 5.6")
    plugins = {item["Name"] for item in project.get("Plugins", []) if item.get("Enabled")}
    missing_plugins = REQUIRED_PLUGINS - plugins
    if missing_plugins:
        raise ValueError(f"missing QA plugins: {sorted(missing_plugins)}")
    cases = config.get("requiredCases", [])
    ids = [item.get("id") for item in cases]
    if set(ids) != REQUIRED_CASES or len(ids) != len(set(ids)):
        raise ValueError("deformation cases are missing or duplicated")
    all_frames = [frame for item in cases for frame in item.get("frames", [])]
    if any(len(item.get("frames", [])) != 3 for item in cases) or all_frames != sorted(all_frames):
        raise ValueError("each case needs three monotonically ordered frames")
    if set(config.get("requiredChecks", [])) != REQUIRED_CHECKS:
        raise ValueError("required defect checks are incomplete")
    if config.get("resolution") != [1440, 2560] or config.get("displayProfile") != "looking-glass-go":
        raise ValueError("QA capture must use the Looking Glass Go profile")
    policy = config.get("approvalPolicy", {})
    if policy.get("automaticApproval") is not False or policy.get("requireHumanReview") is not True:
        raise ValueError("QA must never automatically approve character quality")
    source = script_path.read_text(encoding="utf-8")
    for marker in ("EditorAssetLibrary.does_asset_exist", "is_child_of", "readyToAuthorQaSequence",
                   "raise RuntimeError", "qualityClaim"):
        if marker not in source:
            raise ValueError(f"Unreal preflight is missing fail-closed marker: {marker}")
    return {"valid": True, "cases": len(cases), "checks": len(REQUIRED_CHECKS),
            "plugins": len(REQUIRED_PLUGINS), "engine": "5.6",
            "displayProfile": "looking-glass-go", "editorRuntimeVerified": False}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("character_pipeline/config/deformation_qa.json"))
    parser.add_argument("--project", type=Path, default=Path("unreal/GahyeonStage/GahyeonStageCharacterQA.uproject"))
    parser.add_argument("--script", type=Path, default=Path("unreal/GahyeonStage/Content/Python/gahyeon_character_qa_preflight.py"))
    args = parser.parse_args()
    print(json.dumps(verify(args.config, args.project, args.script)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
