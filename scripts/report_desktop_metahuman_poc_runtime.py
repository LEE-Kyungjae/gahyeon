#!/usr/bin/env python3
"""Create evidence from a real UE 5.8 desktop MetaHuman POC editor run."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re


OPEN_MARKER = "Desktop POC opened MetaHumanCharacter: /Game/Fab/MetaHuman/Skotukeda"
FATAL_MARKERS = ("Fatal error:", "Assertion failed:", "Out of memory:")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def classify_runtime_log(text: str) -> dict:
    opened = OPEN_MARKER in text
    fatal = next((marker for marker in FATAL_MARKERS if marker in text), None)
    optional_missing = (
        "MetaHuman Optional Content folder not found" in text
        or "Failed to initialize texture synthesis with default models" in text
        or bool(re.search(r"Skipped package /MetaHumanCharacter/Optional/.*does not exist", text))
    )
    texture_synthesis_loaded = (
        "Loading texture synthesis model data from file" in text
        and "/Optional/TextureSynthesis/" in text
    )
    face_built = bool(re.search(r"Built Skeletal Mesh .*FaceMesh_0", text))
    body_started = "BodyMesh_1" in text
    dna_started = ".mhdna" in text and "Interchange start importing source" in text
    if fatal:
        state = "failed"
    elif opened and optional_missing:
        state = "opened-limited-mode"
    elif opened:
        state = "opened-full-feature-mode"
    else:
        state = "not-opened"
    return {
        "state": state,
        "editorOpened": opened,
        "fatalError": fatal,
        "dnaImportStarted": dna_started,
        "faceSkeletalMeshBuilt": face_built,
        "bodySkeletalMeshBuildStarted": body_started,
        "optionalContentPresent": not optional_missing,
        "textureSynthesisModelLoaded": texture_synthesis_loaded,
        "aaaQualityClaim": False,
    }


def inspect_desktop_metahuman_runtime(log_path: Path) -> dict:
    if not log_path.is_file() or log_path.is_symlink():
        raise ValueError(f"missing or unsafe Unreal log: {log_path}")
    snapshot = log_path.read_bytes()
    result = classify_runtime_log(snapshot.decode("utf-8", errors="replace"))
    result.update({
        "schemaVersion": 1,
        "engine": "Unreal Engine 5.8",
        "characterAsset": "/Game/Fab/MetaHuman/Skotukeda",
        "log": {"path": str(log_path.resolve()), "sha256": hashlib.sha256(snapshot).hexdigest()},
        "nextActions": [
            action for condition, action in (
                (not result["editorOpened"], "open the Skotukeda MetaHumanCharacter editor"),
                (not result["optionalContentPresent"], "install UE 5.8 MetaHuman Optional Content before surface-quality work"),
                (result["fatalError"] is not None, "resolve the fatal editor failure and rerun"),
            ) if condition
        ],
    })
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = inspect_desktop_metahuman_runtime(args.log)
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if report["editorOpened"] and not report["fatalError"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
