"""Fail-closed verification for the v645 Stella/Ururu Desktop runtime registry."""

import hashlib
import json
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
REGISTRY = ROOT / "character_pipeline/config/living-character-runtime-v645.json"
OUTPUT = ROOT / "artifacts/living-character-poc-v646-runtime-verification/report.json"
EXPECTED_CHARACTERS = {"stella-lily", "ururu"}
EXPECTED_ACTIONS = {"walk", "run", "standSit", "narration", "subtleReaction", "present"}
EXPECTED_ACTIVITIES = {"idle", "walk", "run", "sit", "conversation", "attention", "listening", "thinking"}


def sha256_v646(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_living_character_runtime_v646():
    if OUTPUT.exists():
        raise RuntimeError(f"refusing to overwrite immutable report: {OUTPUT}")
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    failures = []
    assets = []
    files = []
    if set(payload["characters"]) != EXPECTED_CHARACTERS:
        failures.append("unexpected selectable character set")
    if set(payload["selectionPolicy"]["desktopSelectable"]) != EXPECTED_CHARACTERS:
        failures.append("desktop selectable set does not match registry")
    for character_id, character in payload["characters"].items():
        if set(character["actionSequences"]) != EXPECTED_ACTIONS:
            failures.append(f"{character_id}: unexpected action sequence set")
        if set(character["desktopMedia"]) != EXPECTED_ACTIVITIES:
            failures.append(f"{character_id}: unexpected desktop activity set")
        if "explain" in character["actionSequences"] or "explain" in character["desktopMedia"]:
            failures.append(f"{character_id}: rejected explain asset leaked into runtime")
        unreal_paths = {
            "skeletalMesh": character["skeletalMesh"],
            "livingIdle": character["livingIdle"],
            "secondaryMotionRig": character["secondaryMotionRig"],
            "qaMap": character["qaMap"],
            **{f"action:{key}": value for key, value in character["actionSequences"].items()},
        }
        for role, path in unreal_paths.items():
            asset = unreal.load_asset(path)
            record = {
                "character": character_id,
                "role": role,
                "path": path,
                "available": asset is not None,
                "class": asset.get_class().get_name() if asset else None,
            }
            assets.append(record)
            if not record["available"]:
                failures.append(f"{character_id}: missing Unreal asset {role}")
        for role, relative in {**character["desktopMedia"], **character["evidence"]}.items():
            path = ROOT / relative
            record = {
                "character": character_id,
                "role": role,
                "path": relative,
                "available": path.is_file(),
                "bytes": path.stat().st_size if path.is_file() else 0,
                "sha256": sha256_v646(path) if path.is_file() else None,
            }
            files.append(record)
            if not record["available"] or record["bytes"] == 0:
                failures.append(f"{character_id}: missing or empty file {relative}")
    report = {
        "schemaVersion": 1,
        "iteration": "v646",
        "status": "passed" if not failures else "failed",
        "registry": str(REGISTRY.relative_to(ROOT)),
        "characterCount": len(payload["characters"]),
        "unrealAssetCount": len(assets),
        "desktopAndEvidenceFileCount": len(files),
        "failures": failures,
        "assets": assets,
        "files": files,
        "humanApproved": False,
        "releaseEligible": False,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=False)
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if failures:
        raise RuntimeError(f"v645 runtime verification failed: {failures}")
    unreal.log("LIVING_CHARACTER_RUNTIME_V646=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()


verify_living_character_runtime_v646()
