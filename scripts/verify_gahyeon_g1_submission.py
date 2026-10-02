#!/usr/bin/env python3
"""Verify a sealed G1 candidate submission archive."""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

from verify_gahyeon_g1_review import verify as verify_review


def verify_archive(path: Path) -> dict:
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or "submission-manifest.json" not in names:
            raise ValueError("submission has duplicate entries or no manifest")
        for name in names:
            relative = PurePosixPath(name)
            if relative.is_absolute() or ".." in relative.parts or name.endswith("/"):
                raise ValueError(f"unsafe submission path: {name}")
        manifest = json.loads(archive.read("submission-manifest.json"))
        if (manifest.get("schemaVersion") != 1 or manifest.get("characterId") != "gahyeon"
                or manifest.get("gate") != "G1" or manifest.get("status") != "candidate"
                or manifest.get("review") != "g1-review.json"):
            raise ValueError("unsupported G1 submission manifest")
        entries = manifest.get("files", [])
        expected = {item.get("path"): item for item in entries}
        if len(expected) != len(entries) or set(names) - {"submission-manifest.json"} != set(expected):
            raise ValueError("submission contents do not match manifest")
        for name, item in expected.items():
            data = archive.read(name)
            if len(data) != item.get("bytes"):
                raise ValueError(f"submission byte size mismatch: {name}")
            if hashlib.sha256(data).hexdigest() != item.get("sha256"):
                raise ValueError(f"submission checksum mismatch: {name}")
        source_manifest = archive.read("source/package-manifest.json")
        if hashlib.sha256(source_manifest).hexdigest() != manifest.get("sourceHandoffSha256"):
            raise ValueError("submission source handoff binding mismatch")

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in names:
                target = root.joinpath(*PurePosixPath(name).parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.read(name))
            result = verify_review(root / "g1-review.json")
        if result.get("status") != "candidate" or result.get("evidenceCount") != 15:
            raise ValueError("G1 submission is not a complete candidate")
        return {"valid": True, "status": "candidate", "evidenceCount": 15,
                "sourceHandoffSha256": manifest["sourceHandoffSha256"]}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    args = parser.parse_args()
    try:
        result = verify_archive(args.archive)
    except (ValueError, OSError, json.JSONDecodeError, zipfile.BadZipFile) as error:
        raise SystemExit(f"G1 submission verification failed: {error}") from None
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
