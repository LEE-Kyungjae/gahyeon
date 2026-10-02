#!/usr/bin/env python3
"""Verify the sealed Gahyeon SDXL dataset, checkpoints and comparison evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
import uuid
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = ROOT / "artifacts/gahyeon-sdxl-v1/manifest.json"
DEFAULT_CONTINUATION = ROOT / "artifacts/gahyeon-sdxl-v1-continuation/manifest.json"
DEFAULT_COMPARISON = ROOT / "artifacts/gahyeon-sdxl-v1-comparison"
DEFAULT_SELECTION = DEFAULT_COMPARISON / "selection.json"
DEFAULT_IDENTITY = ROOT / "artifacts/gahyeon-ch/identity-reference.json"

VALIDATION_INDICES = {3, 8, 15, 24, 29}
CHECKPOINTS = {
    1200: "gahyeon-sdxl-v1-continued-from0800-step00000400.safetensors",
    1600: "gahyeon-sdxl-v1-continued-from0800-step00000800.safetensors",
    2000: "gahyeon-sdxl-v1-continued-from0800-step00001200.safetensors",
    2400: "gahyeon-sdxl-v1-continued-from2000-step00000400.safetensors",
    2800: "gahyeon-sdxl-v1-continued-from2000-step00000800.safetensors",
}
VARIANTS = {
    "base": None,
    "step0200": "gahyeon-sdxl-v1-step00000200.safetensors",
    "step0400": "gahyeon-sdxl-v1-step00000400.safetensors",
    "step0600": "gahyeon-sdxl-v1-step00000600.safetensors",
    "step0800": "gahyeon-sdxl-v1-step00000800.safetensors",
    "total1200": CHECKPOINTS[1200],
    "total1600": CHECKPOINTS[1600],
    "total2000": CHECKPOINTS[2000],
    "total2400": CHECKPOINTS[2400],
    "total2800": CHECKPOINTS[2800],
}
SCENARIOS = {
    "front_portrait": {
        "slug": "front_portrait", "seed": 424201, "width": 512, "height": 512,
        "prompt": "gahyeonch woman, front-facing close-up portrait, neutral gentle expression, looking at viewer, natural soft light, detailed face, clean background, high quality photograph",
    },
    "profile_smile": {
        "slug": "profile_smile", "seed": 424202, "width": 512, "height": 512,
        "prompt": "gahyeonch woman, right side profile portrait, subtle smile, natural soft light, detailed face, clean background, high quality photograph",
    },
    "casual_fullbody": {
        "slug": "casual_fullbody", "seed": 424203, "width": 448, "height": 640,
        "prompt": "gahyeonch woman, full body, walking outdoors, casual white t-shirt and blue jeans, natural relaxed pose, daylight, high quality photograph",
    },
    "black_dress": {
        "slug": "black_dress", "seed": 424204, "width": 448, "height": 640,
        "prompt": "gahyeonch woman, full body studio portrait, elegant simple black dress, standing, neutral background, soft studio lighting, high quality photograph",
    },
}
REMOTE_OUTPUT_ROOT = PurePosixPath("/opt/zaeze-ai/comfyui/output/gahyeon_lora_compare")
SHA256 = re.compile(r"^[0-9a-f]{64}$")


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def load_object(path: Path, label: str) -> dict:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"{label} is missing or unsafe: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def local_member(root: Path, relative: str, label: str) -> Path:
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError(f"{label} path escapes its artifact root: {relative}")
    resolved = (root / candidate).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as error:
        raise ValueError(f"{label} path escapes its artifact root: {relative}") from error
    if resolved.is_symlink() or not resolved.is_file():
        raise ValueError(f"{label} is missing or unsafe: {relative}")
    return resolved


def verify_dataset(dataset_path: Path, identity_path: Path) -> dict:
    dataset = load_object(dataset_path, "SDXL dataset manifest")
    identity = load_object(identity_path, "identity manifest")
    if dataset.get("trigger") != "gahyeonch":
        raise ValueError("SDXL dataset trigger must remain gahyeonch")
    if identity.get("canonicalSource") != "user-provided-originals":
        raise ValueError("SDXL dataset identity is not rooted in user-provided originals")

    references = identity.get("references", []) + identity.get("supportingReferences", [])
    reference_by_index = {item.get("index"): item for item in references}
    if len(references) != 29 or set(reference_by_index) != set(range(1, 30)):
        raise ValueError("identity manifest must classify exactly 29 indexed source images")

    rows = []
    split_indices: dict[str, set[int]] = {}
    dataset_root = dataset_path.parent.resolve()
    declared_files: set[Path] = {dataset_path.resolve()}
    for split, expected_count in (("train", 24), ("validation", 5)):
        values = dataset.get(split)
        if not isinstance(values, list) or len(values) != expected_count:
            raise ValueError(f"SDXL dataset {split} split must contain {expected_count} rows")
        indices: set[int] = set()
        for item in values:
            index = item.get("index")
            if not isinstance(index, int) or isinstance(index, bool) or index in indices:
                raise ValueError(f"SDXL dataset {split} indices are invalid or duplicated")
            indices.add(index)
            reference = reference_by_index.get(index)
            if reference is None or item.get("source") != reference.get("file"):
                raise ValueError(f"SDXL dataset source identity mismatch at index {index}")
            expected_sha = item.get("sha256")
            if not isinstance(expected_sha, str) or not SHA256.fullmatch(expected_sha):
                raise ValueError(f"SDXL dataset has an invalid digest at index {index}")
            if reference.get("sha256") != expected_sha:
                raise ValueError(f"SDXL dataset disagrees with identity digest at index {index}")
            image = local_member(dataset_root, str(item.get("file", "")), "dataset image")
            expected_parent = "train/1_gahyeonch" if split == "train" else "validation"
            if image.parent.relative_to(dataset_root).as_posix() != expected_parent:
                raise ValueError(f"SDXL dataset image is in the wrong split at index {index}")
            source = local_member(identity_path.parent, str(item["source"]), "identity source")
            if digest(image) != expected_sha or digest(source) != expected_sha:
                raise ValueError(f"SDXL dataset image checksum mismatch at index {index}")
            caption = image.with_suffix(".txt")
            if caption.is_symlink() or not caption.is_file():
                raise ValueError(f"SDXL dataset caption is missing at index {index}")
            caption_value = caption.read_text(encoding="utf-8").strip()
            if caption_value != item.get("caption") or not caption_value.startswith("gahyeonch "):
                raise ValueError(f"SDXL dataset caption mismatch at index {index}")
            declared_files.update((image, caption.resolve()))
            rows.append(item)
        split_indices[split] = indices

    if split_indices["validation"] != VALIDATION_INDICES:
        raise ValueError("SDXL validation indices changed or leaked into training")
    if split_indices["train"] != set(range(1, 30)) - VALIDATION_INDICES:
        raise ValueError("SDXL training indices are incomplete or contain validation leakage")
    actual_files = {
        path.resolve() for path in dataset_root.rglob("*")
        if path.is_file() and path.suffix.lower() in {".png", ".txt", ".json"}
    }
    if actual_files != declared_files:
        raise ValueError("SDXL dataset contains undeclared or missing training files")
    return {"train": 24, "validation": 5, "sourceImages": 29}


def verify_continuation(path: Path) -> tuple[dict, dict[int, dict]]:
    payload = load_object(path, "SDXL continuation manifest")
    required = {
        "status": "completed", "base_total_steps": 800, "additional_steps": 2000,
        "final_total_steps": 2800, "learning_rate": 5e-05,
        "training_errors_detected": False, "registered_in_comfyui": True,
        "comparison_status": "completed",
    }
    for key, expected in required.items():
        if payload.get(key) != expected:
            raise ValueError(f"SDXL continuation field {key} is not sealed as {expected!r}")
    if not isinstance(payload.get("source_sha256"), str) or not SHA256.fullmatch(
            payload["source_sha256"]):
        raise ValueError("SDXL continuation source digest is invalid")
    if PurePosixPath(str(payload.get("source_weights", ""))).name != "gahyeon-sdxl-v1.safetensors":
        raise ValueError("SDXL continuation source weight changed")

    checkpoints = payload.get("checkpoints")
    if not isinstance(checkpoints, list) or len(checkpoints) != len(CHECKPOINTS):
        raise ValueError("SDXL continuation must contain exactly five checkpoints")
    by_step: dict[int, dict] = {}
    digests: set[str] = set()
    files: set[str] = set()
    for item in checkpoints:
        step = item.get("total_step")
        if step in by_step or step not in CHECKPOINTS:
            raise ValueError("SDXL continuation checkpoint steps are invalid or duplicated")
        if item.get("status") != "completed" or item.get("file") != CHECKPOINTS[step]:
            raise ValueError(f"SDXL checkpoint metadata mismatch at total step {step}")
        checksum = item.get("sha256")
        if not isinstance(checksum, str) or not SHA256.fullmatch(checksum):
            raise ValueError(f"SDXL checkpoint digest is invalid at total step {step}")
        if checksum in digests or item["file"] in files:
            raise ValueError("SDXL continuation checkpoint identity is duplicated")
        by_step[step] = item
        digests.add(checksum)
        files.add(item["file"])
    if list(by_step) != list(CHECKPOINTS):
        raise ValueError("SDXL continuation checkpoints are not in total-step order")
    comparison = payload.get("comparison")
    expected_comparison = {
        "records": 40, "completed": 40, "failed": 0, "missing_outputs": 0,
        "default_total_step": 2000, "closeup_specialist_total_step": 2800,
    }
    if not isinstance(comparison, dict) or any(
            comparison.get(key) != value for key, value in expected_comparison.items()):
        raise ValueError("SDXL continuation comparison completion claim is inconsistent")
    return payload, by_step


def verify_individual_results(comparison_root: Path) -> list[dict]:
    result_root = comparison_root / "results"
    image_root = comparison_root / "images"
    expected_names = {
        f"{scenario}_{variant}.json"
        for variant in VARIANTS for scenario in SCENARIOS
    }
    actual_names = {
        path.name for path in result_root.glob("*.json") if path.name != "summary.json"
    }
    if actual_names != expected_names:
        raise ValueError("SDXL comparison result matrix is incomplete or has extra records")

    rows: list[dict] = []
    declared_images: set[str] = set()
    for variant, expected_lora in VARIANTS.items():
        for scenario, expected_scenario in SCENARIOS.items():
            path = result_root / f"{scenario}_{variant}.json"
            result = load_object(path, "SDXL comparison result")
            if result.get("variant") != variant or result.get("lora") != expected_lora:
                raise ValueError(f"SDXL comparison variant identity mismatch: {scenario}/{variant}")
            if result.get("scenario") != expected_scenario:
                raise ValueError(f"SDXL comparison scenario changed: {scenario}/{variant}")
            if result.get("status") != "completed":
                raise ValueError(f"SDXL comparison is not completed: {scenario}/{variant}")
            for numeric in ("started_at", "elapsed_seconds"):
                value = result.get(numeric)
                if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
                    raise ValueError(f"SDXL comparison has invalid {numeric}: {scenario}/{variant}")
            try:
                uuid.UUID(str(result.get("prompt_id")))
            except (ValueError, TypeError, AttributeError) as error:
                raise ValueError(
                    f"SDXL comparison has invalid prompt identity: {scenario}/{variant}") from error
            filename = f"{scenario}_{variant}_00001_.png"
            if PurePosixPath(str(result.get("output", ""))) != REMOTE_OUTPUT_ROOT / filename:
                raise ValueError(f"SDXL comparison output provenance mismatch: {scenario}/{variant}")
            checksum = result.get("sha256")
            if not isinstance(checksum, str) or not SHA256.fullmatch(checksum):
                raise ValueError(f"SDXL comparison digest is invalid: {scenario}/{variant}")
            image = image_root / filename
            if image.is_symlink() or not image.is_file() or digest(image) != checksum:
                raise ValueError(f"SDXL comparison image checksum mismatch: {scenario}/{variant}")
            declared_images.add(filename)
            rows.append(result)
    actual_images = {path.name for path in image_root.glob("*.png")}
    if actual_images != declared_images:
        raise ValueError("SDXL comparison images are incomplete or contain undeclared outputs")
    return rows


def verify_summary(path: Path, individual_results: list[dict], label: str = "local summary") -> dict:
    payload = load_object(path, label)
    if set(payload) != {"results"} or payload.get("results") != individual_results:
        raise ValueError(f"{label} does not exactly match the 40 individual result records")
    return payload


def verify_selection(path: Path, continuation: dict[int, dict], identity_path: Path) -> dict:
    payload = load_object(path, "SDXL selection")
    if payload.get("status") != "auxiliary-only" or payload.get("comparisonStrength") != 0.8:
        raise ValueError("SDXL selection is not sealed as auxiliary-only strength 0.8")
    canonical = Path(str(payload.get("canonicalIdentityManifest", "")))
    if canonical.is_absolute() or ".." not in canonical.parts:
        raise ValueError("SDXL selection canonical identity reference is invalid")
    if (path.parent / canonical).resolve() != identity_path.resolve():
        raise ValueError("SDXL selection points at another canonical identity manifest")

    selected = [payload.get("default")] + list(payload.get("specialists", []))
    if len(selected) != 2 or any(not isinstance(item, dict) for item in selected):
        raise ValueError("SDXL selection must contain one default and one specialist")
    selected_by_step = {item.get("totalSteps"): item for item in selected}
    if set(selected_by_step) != {2000, 2800}:
        raise ValueError("SDXL selected checkpoint roles changed")
    for step, item in selected_by_step.items():
        checkpoint = continuation[step]
        if item.get("file") != checkpoint["file"] or item.get("sha256") != checkpoint["sha256"]:
            raise ValueError(f"SDXL selection disagrees with checkpoint identity at step {step}")
        if item.get("heroReferenceAllowed") is not False:
            raise ValueError("SDXL selection cannot become a Hero identity authority")
    approval = payload.get("approval")
    if approval != {
        "generationUse": True, "g0IdentityReference": False,
        "final3DHeroReference": False,
    }:
        raise ValueError("SDXL selection approval boundary changed")

    identity = load_object(identity_path, "identity manifest")
    models = identity.get("auxiliaryModels")
    if not isinstance(models, list) or len(models) != 2:
        raise ValueError("identity manifest must bind exactly two selected auxiliary SDXL models")
    model_by_step = {item.get("totalSteps"): item for item in models}
    if set(model_by_step) != {2000, 2800}:
        raise ValueError("identity auxiliary SDXL checkpoint steps changed")
    for step, selected_item in selected_by_step.items():
        identity_item = model_by_step[step]
        if identity_item.get("sha256") != selected_item["sha256"]:
            raise ValueError(f"identity auxiliary model digest mismatch at step {step}")
        if identity_item.get("heroReferenceAllowed") is not False:
            raise ValueError("identity manifest promoted an auxiliary SDXL model to Hero authority")
    expected_identity_roles = {
        2000: ("gahyeon-sdxl-v1-total2000", "general-concept"),
        2800: ("gahyeon-sdxl-v1-total2800", "front-face-helper"),
    }
    for step, (name, role) in expected_identity_roles.items():
        item = model_by_step[step]
        if item.get("name") != name or item.get("role") != role:
            raise ValueError(f"identity auxiliary model role mismatch at step {step}")
    return payload


def sync_summary(authoritative: Path, destination: Path, individual_results: list[dict]) -> None:
    verify_summary(authoritative, individual_results, "authoritative summary")
    if destination.is_symlink():
        raise ValueError("local summary cannot be a symbolic link")
    destination.parent.mkdir(parents=True, exist_ok=True)
    data = authoritative.read_bytes()
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", dir=destination.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
        directory = os.open(destination.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        temporary.unlink(missing_ok=True)


def verify(dataset: Path = DEFAULT_DATASET, continuation: Path = DEFAULT_CONTINUATION,
           comparison: Path = DEFAULT_COMPARISON, selection: Path = DEFAULT_SELECTION,
           identity: Path = DEFAULT_IDENTITY, *, require_summary: bool = True) -> dict:
    dataset_report = verify_dataset(dataset.resolve(), identity.resolve())
    continuation_payload, checkpoints = verify_continuation(continuation.resolve())
    results = verify_individual_results(comparison.resolve())
    if require_summary:
        verify_summary(comparison.resolve() / "results/summary.json", results)
    verify_selection(selection.resolve(), checkpoints, identity.resolve())
    return {
        "valid": True,
        "dataset": dataset_report,
        "continuation": {
            "baseTotalSteps": continuation_payload["base_total_steps"],
            "finalTotalSteps": continuation_payload["final_total_steps"],
            "checkpoints": len(checkpoints),
        },
        "comparison": {
            "variants": len(VARIANTS), "scenarios": len(SCENARIOS),
            "records": len(results), "completed": len(results),
        },
        "selection": {"defaultTotalSteps": 2000, "specialistTotalSteps": 2800,
                      "heroReferenceAllowed": False},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--continuation", type=Path, default=DEFAULT_CONTINUATION)
    parser.add_argument("--comparison", type=Path, default=DEFAULT_COMPARISON)
    parser.add_argument("--selection", type=Path, default=DEFAULT_SELECTION)
    parser.add_argument("--identity", type=Path, default=DEFAULT_IDENTITY)
    parser.add_argument(
        "--sync-summary-from", type=Path,
        help="Replace the local summary only after this authoritative copy exactly matches all local records",
    )
    args = parser.parse_args()
    report = verify(args.dataset, args.continuation, args.comparison,
                    args.selection, args.identity,
                    require_summary=args.sync_summary_from is None)
    if args.sync_summary_from is not None:
        results = verify_individual_results(args.comparison.resolve())
        sync_summary(args.sync_summary_from.resolve(),
                     args.comparison.resolve() / "results/summary.json", results)
        report = verify(args.dataset, args.continuation, args.comparison,
                        args.selection, args.identity)
        report["summarySynchronized"] = True
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
