#!/usr/bin/env python3
"""Verify that the G1 work order is source-bound and covers every review view."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from verify_gahyeon_g1_review import ARTIST_REQUIRED, REQUIRED_VIEWS


ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / "artifacts/gahyeon-ch/g1-authoring-work-order.json"
EXPECTED_SOURCE_ROLES = {"identity", "modeling-input", "non-authoritative-drafts"}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def local_file(manifest: Path, uri: str) -> Path:
    candidate = Path(uri)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError(f"work-order URI must stay pack-local: {uri}")
    resolved = (manifest.parent / candidate).resolve()
    if manifest.parent.resolve() not in resolved.parents:
        raise ValueError(f"work-order URI escapes pack: {uri}")
    if not resolved.is_file() or resolved.is_symlink():
        raise ValueError(f"work-order source is missing or unsafe: {uri}")
    return resolved


def verify(manifest: Path) -> dict:
    if manifest.is_symlink():
        raise ValueError("work-order manifest cannot be a symbolic link")
    manifest = manifest.resolve()
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    if payload.get("schemaVersion") != 1 or payload.get("characterId") != "gahyeon":
        raise ValueError("unsupported G1 work-order identity or version")
    if payload.get("gate") != "G1" or payload.get("status") != "ready-for-authoring":
        raise ValueError("G1 work order must remain ready-for-authoring")

    sources = payload.get("sourceManifests", [])
    roles = [item.get("role") for item in sources]
    if len(roles) != len(set(roles)) or set(roles) != EXPECTED_SOURCE_ROLES:
        raise ValueError("G1 work order source roles are incomplete or duplicated")
    for source in sources:
        path = local_file(manifest, source["uri"])
        if digest(path) != source.get("sha256"):
            raise ValueError(f"G1 work-order source checksum mismatch: {source['role']}")

    identity_item = next(item for item in sources if item["role"] == "identity")
    identity = json.loads(local_file(manifest, identity_item["uri"]).read_text(encoding="utf-8"))
    known_anchors = {item["index"] for item in
                     identity["references"] + identity["supportingReferences"]}
    evidence = payload.get("requiredEvidence", [])
    views = [item.get("view") for item in evidence]
    if len(views) != len(set(views)) or set(views) != REQUIRED_VIEWS:
        raise ValueError("G1 work order must map every required review view exactly once")
    for item in evidence:
        anchors = item.get("sourceAnchors", [])
        if not anchors or not set(anchors).issubset(known_anchors):
            raise ValueError(f"invalid source anchors for {item.get('view')}")
        expected = ("artist-authored-completion" if item["view"] in ARTIST_REQUIRED
                    else "canonical-observed")
        if item.get("designAuthority") != expected:
            raise ValueError(f"wrong design authority for {item['view']}: expected {expected}")

    formats = set(payload.get("productionTarget", {}).get("deliverableFormats", []))
    if not formats or not formats.issubset(
            {"fbx", "glb", "blend", "zbrush-project", "metahuman-source", "unreal-content-zip"}):
        raise ValueError("G1 work order contains unsupported deliverable formats")
    if not payload.get("identityRules") or not payload.get("draftCorrections"):
        raise ValueError("G1 work order must retain identity and draft correction instructions")
    return {"valid": True, "requiredEvidence": len(evidence), "sourceManifests": len(sources)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path, nargs="?", default=DEFAULT)
    args = parser.parse_args()
    print(json.dumps(verify(args.manifest), ensure_ascii=False))


if __name__ == "__main__":
    main()
