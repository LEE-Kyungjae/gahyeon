#!/usr/bin/env python3
"""Build a deterministic G1 candidate submission from an extracted handoff."""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
import zipfile
import struct
from pathlib import Path


FIXED_TIMESTAMP = (2026, 8, 12, 0, 0, 0)
FORMATS = {
    "blend": ".blend",
    "fbx": ".fbx",
    "glb": ".glb",
    "zbrush-project": ".ztl",
    "metahuman-source": ".zip",
    "unreal-content-zip": ".zip",
}
ARTIST_REGIONS = {
    "body-neutral-rear": "rear-body",
    "hair-rear": "rear-hair",
    "hair-top": "top-hair",
    "outfit-rear": "rear-outfit",
}


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def validate_png(path: Path) -> None:
    header = path.read_bytes()[:24]
    if (len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n"
            or header[12:16] != b"IHDR"):
        raise ValueError(f"G1 evidence is not a PNG image: {path.name}")
    width, height = struct.unpack(">II", header[16:24])
    if width < 64 or height < 64:
        raise ValueError(f"G1 evidence image is too small: {path.name} ({width}x{height})")


def contained_file(root: Path, relative: str) -> Path:
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError(f"unsafe handoff path: {relative}")
    resolved = (root / candidate).resolve()
    if root not in resolved.parents or not resolved.is_file() or resolved.is_symlink():
        raise ValueError(f"missing or unsafe handoff file: {relative}")
    return resolved


def add_file(archive: zipfile.ZipFile, name: str, source: Path) -> dict:
    info = zipfile.ZipInfo(name, FIXED_TIMESTAMP)
    info.compress_type = zipfile.ZIP_STORED
    info.external_attr = 0o644 << 16
    data = source.read_bytes()
    archive.writestr(info, data)
    return {"path": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def add_bytes(archive: zipfile.ZipFile, name: str, data: bytes) -> dict:
    info = zipfile.ZipInfo(name, FIXED_TIMESTAMP)
    info.compress_type = zipfile.ZIP_STORED
    info.external_attr = 0o644 << 16
    archive.writestr(info, data)
    return {"path": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def package(handoff_dir: Path, model: Path, artifact_format: str,
            evidence_dir: Path, output: Path) -> dict:
    handoff = handoff_dir.resolve()
    evidence_root = evidence_dir.resolve()
    model = model.resolve()
    output = output.resolve()
    if output.exists():
        raise ValueError(f"refusing to overwrite submission: {output}")
    if artifact_format not in FORMATS:
        raise ValueError(f"unsupported G1 model format: {artifact_format}")
    if (not model.is_file() or model.is_symlink() or model.stat().st_size == 0
            or model.suffix.lower() != FORMATS[artifact_format]):
        raise ValueError(f"model file does not match {artifact_format}: {model}")

    handoff_manifest = contained_file(handoff, "package-manifest.json")
    handoff_payload = json.loads(handoff_manifest.read_text(encoding="utf-8"))
    if (handoff_payload.get("schemaVersion") != 2
            or handoff_payload.get("purpose") != "G1-model-sheet-authoring"
            or handoff_payload.get("characterId") != "gahyeon"):
        raise ValueError("unsupported G1 handoff")
    inventory = {item["path"]: item for item in handoff_payload.get("files", [])}
    if len(inventory) != len(handoff_payload.get("files", [])):
        raise ValueError("handoff inventory contains duplicates")
    for relative, item in inventory.items():
        source = contained_file(handoff, relative)
        if source.stat().st_size != item.get("bytes") or digest(source) != item.get("sha256"):
            raise ValueError(f"handoff integrity check failed: {relative}")

    identity = contained_file(handoff, "identity-reference.json")
    modeling = contained_file(handoff, "modeling-input.json")
    work_order = contained_file(handoff, "g1-authoring-work-order.json")
    order = json.loads(work_order.read_text(encoding="utf-8"))
    identity_payload = json.loads(identity.read_text(encoding="utf-8"))
    reference_aliases = {item["index"]: item for item in handoff_payload.get("references", [])}
    reference_files = []
    for group in (identity_payload.get("references", []),
                  identity_payload.get("supportingReferences", [])):
        for item in group:
            alias = reference_aliases.get(item.get("index"))
            if alias is None or alias.get("sha256") != item.get("sha256"):
                raise ValueError(f"handoff identity alias mismatch: {item.get('index')}")
            source = contained_file(handoff, alias["packagedPath"])
            original_name = Path(item["file"])
            if original_name.is_absolute() or len(original_name.parts) != 1:
                raise ValueError(f"unsafe original reference filename: {item['file']}")
            reference_files.append((original_name.as_posix(), source))
    required = order.get("requiredEvidence", [])
    views = [item.get("view") for item in required]
    if len(views) != 15 or len(set(views)) != 15:
        raise ValueError("G1 work order must contain exactly 15 unique evidence views")

    evidence_files = []
    evidence_records = []
    artist_regions = []
    for item in required:
        view = item["view"]
        source = evidence_root / f"{view}.png"
        if not source.is_file() or source.is_symlink() or source.stat().st_size == 0:
            raise ValueError(f"required G1 evidence is missing: {view}.png")
        validate_png(source)
        authority = item.get("designAuthority")
        required_region = ARTIST_REGIONS.get(view)
        if required_region:
            if authority != "artist-authored-completion":
                raise ValueError(f"G1 work order has invalid authority for {view}")
            artist_regions.append(required_region)
        packaged = f"evidence/{view}.png"
        evidence_files.append((packaged, source))
        evidence_records.append({
            "view": view,
            "captureType": "viewport-render",
            "designAuthority": authority,
            "uri": packaged,
            "sha256": digest(source),
        })

    model_name = f"model/gahyeon-g1{FORMATS[artifact_format]}"
    review = {
        "schemaVersion": 1,
        "characterId": "gahyeon",
        "gate": "G1",
        "status": "candidate",
        "sourceManifests": [
            {"kind": "identity-reference", "uri": "identity-reference.json",
             "sha256": digest(identity)},
            {"kind": "modeling-input", "uri": "modeling-input.json",
             "sha256": digest(modeling)},
        ],
        "modelArtifact": {
            "format": artifact_format,
            "uri": model_name,
            "sha256": digest(model),
            "bytes": model.stat().st_size,
        },
        "evidence": evidence_records,
        "artistAuthoredRegions": sorted(artist_regions),
        "findings": [],
        "approvals": [],
    }
    review_data = (json.dumps(review, ensure_ascii=False, indent=2) + "\n").encode("utf-8")

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=output.parent, suffix=".zip", delete=False) as handle:
        temporary = Path(handle.name)
    try:
        entries = []
        with zipfile.ZipFile(temporary, "w", allowZip64=True) as archive:
            entries.append(add_file(archive, "identity-reference.json", identity))
            entries.append(add_file(archive, "modeling-input.json", modeling))
            entries.append(add_file(archive, "source/package-manifest.json", handoff_manifest))
            entries.append(add_file(archive, "source/g1-authoring-work-order.json", work_order))
            entries.append(add_file(archive, model_name, model))
            for name, source in reference_files:
                entries.append(add_file(archive, name, source))
            for name, source in evidence_files:
                entries.append(add_file(archive, name, source))
            entries.append(add_bytes(archive, "g1-review.json", review_data))
            submission = {
                "schemaVersion": 1,
                "characterId": "gahyeon",
                "gate": "G1",
                "status": "candidate",
                "sourceHandoffSha256": digest(handoff_manifest),
                "review": "g1-review.json",
                "files": entries,
            }
            add_bytes(
                archive,
                "submission-manifest.json",
                (json.dumps(submission, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
            )
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)
    return {"valid": True, "status": "candidate", "evidenceCount": len(evidence_records),
            "output": str(output), "sha256": digest(output)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--handoff-dir", required=True, type=Path)
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--format", required=True, dest="artifact_format", choices=sorted(FORMATS))
    parser.add_argument("--evidence-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = package(args.handoff_dir, args.model, args.artifact_format,
                         args.evidence_dir, args.output)
    except (ValueError, OSError, json.JSONDecodeError) as error:
        raise SystemExit(f"G1 submission packaging failed: {error}") from None
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
