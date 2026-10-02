#!/usr/bin/env python3
"""Verify the canonical Gahyeon identity pack without modifying its sources."""

import hashlib
import json
from collections import Counter
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "artifacts/gahyeon-ch/identity-reference.json"
SCHEMA = ROOT / "docs/contracts/gahyeon-identity-reference.schema.json"


def verify(pack: Path, schema_path: Path = SCHEMA) -> tuple[int, int, int]:
    pack = pack.resolve()
    manifest = json.loads(pack.read_text(encoding="utf-8"))
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(manifest)
    if manifest.get("status") not in {"source-canon", "g0-approved"}:
        raise ValueError("identity pack is not canonical")
    if manifest.get("canonicalSource") != "user-provided-originals":
        raise ValueError("generated derivatives cannot be the canonical source")

    counts = Counter()
    seen_indices = set()
    seen_files = set()
    canonical = manifest["references"]
    supporting = manifest["supportingReferences"]
    for reference in canonical + supporting:
        reference_name = Path(reference["file"])
        if reference_name.is_absolute() or len(reference_name.parts) != 1:
            raise ValueError(f"reference must be a pack-local filename: {reference['file']}")
        path = pack.parent / reference["file"]
        if reference["index"] in seen_indices or path.name in seen_files:
            raise ValueError(f"duplicate reference: {path.name}")
        seen_indices.add(reference["index"])
        seen_files.add(path.name)
        if not path.is_file():
            raise ValueError(f"missing reference: {path}")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != reference["sha256"]:
            raise ValueError(f"checksum mismatch: {path}")
        if reference["identityAuthority"] == "canonical":
            counts[reference["kind"]] += 1

    source_images = {
        path.name for path in pack.parent.glob("ChatGPT Image*")
        if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
    }
    inventory = manifest["sourceInventory"]
    if inventory["presentCount"] != len(source_images):
        raise ValueError("sourceInventory.presentCount does not match files on disk")
    discrepancy = inventory["operatorDeclaredCount"] != inventory["presentCount"]
    if discrepancy != (inventory["status"] == "count-discrepancy"):
        raise ValueError("source inventory status does not match declared/present counts")
    if source_images != seen_files:
        missing = sorted(source_images - seen_files)
        unknown = sorted(seen_files - source_images)
        raise ValueError(
            f"every source image must be classified exactly once; unclassified={missing}, unknown={unknown}")
    for reference in supporting:
        excluded = set(reference["excludedFrom"])
        if not {"neutral-face-geometry", "primary-body-geometry"}.issubset(excluded):
            raise ValueError(
                f"supporting reference must be excluded from primary geometry: {reference['file']}")

    face_count = counts["face"]
    full_body_count = counts["full-body"]
    if face_count < manifest["minimums"]["face"]:
        raise ValueError(f"insufficient face references: {face_count}")
    if full_body_count < manifest["minimums"]["fullBody"]:
        raise ValueError(f"insufficient full-body references: {full_body_count}")
    if not {"left-profile", "right-profile"}.issubset({r["view"] for r in canonical}):
        raise ValueError("both profile directions are required")
    if any(model["heroReferenceAllowed"] for model in manifest["auxiliaryModels"]):
        raise ValueError("auxiliary LoRA must not be promoted to hero identity authority")

    return len(seen_files), face_count, full_body_count


def main() -> None:
    try:
        references, face_count, full_body_count = verify(PACK)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        raise SystemExit(str(error)) from error
    print(
        f"identity pack OK: {references} classified source images "
        f"({face_count} canonical face, {full_body_count} canonical full-body)")


if __name__ == "__main__":
    main()
