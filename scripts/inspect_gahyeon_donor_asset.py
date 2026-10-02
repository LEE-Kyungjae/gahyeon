#!/usr/bin/env python3
"""Create a read-only inventory for a licensed marketplace donor asset."""

import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path, PurePosixPath


GARMENT = re.compile(r"shirt|top|jacket|coat|dress|skirt|short|pants|trouser|cloth|armor|shoe|boot", re.I)
HAIR = re.compile(r"hair|brow|lash|groom", re.I)
TEXTURE = re.compile(r"base.?color|albedo|diffuse|normal|rough|metal|orm|ao|opacity|alpha|sss|flow", re.I)
SOURCE_EXTENSIONS = {".fbx", ".blend", ".glb", ".gltf", ".obj", ".usd", ".usdz", ".mhpkg", ".uasset"}


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def classify(name):
    tags = []
    if GARMENT.search(name):
        tags.append("garment")
    if HAIR.search(name):
        tags.append("hair")
    if TEXTURE.search(name):
        tags.append("texture-channel")
    if Path(name).suffix.lower() in SOURCE_EXTENSIONS:
        tags.append("source-geometry")
    return tags


def unsafe_archive_name(name):
    normalized = name.replace("\\", "/")
    path = PurePosixPath(normalized)
    return path.is_absolute() or ".." in path.parts


def file_record(path, root=None):
    relative = path.name if root is None else path.relative_to(root).as_posix()
    return {
        "path": relative,
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
        "tags": classify(relative),
    }


def inspect(source):
    report = {
        "schemaVersion": 1,
        "source": str(source.resolve()),
        "readOnlyInspection": True,
        "files": [],
        "archive": None,
    }
    if source.is_dir():
        report["sourceType"] = "directory"
        report["files"] = [
            file_record(path, source)
            for path in sorted(source.rglob("*"))
            if path.is_file() and not path.is_symlink()
        ]
    elif source.is_file():
        report["sourceType"] = source.suffix.lower().lstrip(".") or "file"
        report["files"] = [file_record(source)]
        if zipfile.is_zipfile(source):
            with zipfile.ZipFile(source) as archive:
                members = []
                for info in archive.infolist():
                    if info.is_dir():
                        continue
                    members.append(
                        {
                            "path": info.filename,
                            "bytes": info.file_size,
                            "compressedBytes": info.compress_size,
                            "unsafePath": unsafe_archive_name(info.filename),
                            "tags": classify(info.filename),
                        }
                    )
            report["archive"] = {
                "format": "zip",
                "memberCount": len(members),
                "unsafeMemberCount": sum(member["unsafePath"] for member in members),
                "members": members,
            }
    else:
        raise RuntimeError(f"donor source does not exist: {source}")

    candidates = []
    records = report["archive"]["members"] if report["archive"] else report["files"]
    for record in records:
        if record["tags"]:
            candidates.append({"path": record["path"], "tags": record["tags"]})
    report["summary"] = {
        "fileCount": len(records),
        "sourceGeometryCount": sum("source-geometry" in item["tags"] for item in records),
        "garmentCandidateCount": sum("garment" in item["tags"] for item in records),
        "hairCandidateCount": sum("hair" in item["tags"] for item in records),
        "textureChannelCandidateCount": sum("texture-channel" in item["tags"] for item in records),
        "requiresManualLicenseVerification": True,
        "safeToExtract": not report["archive"] or report["archive"]["unsafeMemberCount"] == 0,
    }
    report["candidates"] = candidates
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise RuntimeError(f"refusing to overwrite donor inspection: {args.output}")
    report = inspect(args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))


if __name__ == "__main__":
    main()
