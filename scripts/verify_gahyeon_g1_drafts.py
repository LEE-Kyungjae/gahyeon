#!/usr/bin/env python3
"""Ensure generated G1 drafts stay traceable and never become identity authority."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "artifacts/gahyeon-ch"
MANIFEST = PACK / "g1-drafts/drafts-manifest.json"


def main() -> None:
    identity = json.loads((PACK / "identity-reference.json").read_text(encoding="utf-8"))
    canonical = {item["index"] for item in identity["references"]}
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("status") != "draft" or manifest.get("identityAuthority") is not False:
        raise SystemExit("generated G1 assets must remain non-authoritative drafts")
    if len(manifest.get("assets", [])) < 2:
        raise SystemExit("expected separate face and body drafts")

    purposes = set()
    filenames = set()
    for asset in manifest["assets"]:
        name = Path(asset["file"])
        if name.is_absolute() or len(name.parts) != 1:
            raise SystemExit(f"draft must use a local filename: {name}")
        if name.name in filenames:
            raise SystemExit(f"duplicate draft filename: {name}")
        filenames.add(name.name)
        path = MANIFEST.parent / name
        if not path.is_file():
            raise SystemExit(f"missing draft: {name}")
        if hashlib.sha256(path.read_bytes()).hexdigest() != asset["sha256"]:
            raise SystemExit(f"draft checksum mismatch: {name}")
        if not set(asset["sourceAnchors"]).issubset(canonical):
            raise SystemExit(f"draft uses an unknown source anchor: {name}")
        if asset["review"]["decision"] not in {
                "needs-revision", "candidate-review", "blockout-only"}:
            raise SystemExit(f"draft was promoted without G1 approval: {name}")
        purposes.add(asset["purpose"])

    required = {"facial-turnaround-draft", "body-and-outfit-turnaround-draft"}
    if purposes != required:
        raise SystemExit("face/body draft purposes are incomplete")
    print(f"G1 drafts OK: {len(filenames)} non-authoritative, checksum-bound assets")


if __name__ == "__main__":
    main()
