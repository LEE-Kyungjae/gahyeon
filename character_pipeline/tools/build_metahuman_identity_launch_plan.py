#!/usr/bin/env python3
"""Build a fail-closed, reproducible Unreal MetaHuman Identity launch plan."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict:
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"missing or unsafe input: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def build(session_path: Path, importer_path: Path) -> dict:
    session_path = session_path.resolve()
    importer_path = importer_path.resolve()
    session = load(session_path)
    if session.get("sessionId") != "gahyeon-metahuman-identity-v002":
        raise ValueError("only the immutable v002 Identity session is allowed")
    if session.get("state") != "ready-to-launch" or session.get("blockedChecks"):
        raise ValueError("Identity session is not ready; satisfy preflight before launch")
    unreal = session.get("unreal", {})
    editor = Path(unreal.get("editor") or "")
    project = Path(unreal.get("project") or "")
    if not editor.is_absolute() or not editor.exists():
        raise ValueError("verified Unreal Editor is missing")
    if not project.is_absolute() or not project.is_file():
        raise ValueError("Unreal project is missing")
    if not importer_path.is_file() or importer_path.is_symlink():
        raise ValueError("v002 Unreal importer is missing or unsafe")
    executable = editor / "Contents/MacOS/UnrealEditor" if editor.suffix == ".app" else editor
    if not executable.is_file():
        raise ValueError("Unreal Editor executable is missing")
    args = [
        str(executable), str(project),
        f"-ExecutePythonScript={importer_path}",
        f"-GahyeonIdentitySession={session_path}",
        "-unattended", "-NoSplash", "-NoSound",
    ]
    return {
        "schemaVersion": 1,
        "kind": "metahuman-identity-import-launch-plan",
        "state": "ready-to-launch-import-only",
        "qualityClaim": None,
        "session": {"path": str(session_path), "sha256": digest(session_path)},
        "importer": {"path": str(importer_path), "sha256": digest(importer_path)},
        "project": str(project),
        "editor": str(editor),
        "argv": args,
        "stopsBefore": ["components-from-mesh", "marker-correction", "identity-solve", "conform-character"],
        "expectedReceipt": "artifacts/gahyeon-ch/metahuman-identity-v002-import-receipt.json",
        "forbiddenClaims": ["metahuman-created", "dna-created", "identity-approved", "aaa-quality"],
    }


def verify(plan_path: Path) -> dict:
    plan = load(plan_path.resolve())
    if plan.get("state") != "ready-to-launch-import-only" or plan.get("qualityClaim") is not None:
        raise ValueError("launch plan state or quality claim differs")
    for key in ("session", "importer"):
        item = plan.get(key, {})
        path = Path(item.get("path", ""))
        if not path.is_absolute() or not path.is_file() or path.is_symlink() or digest(path) != item.get("sha256"):
            raise ValueError(f"launch plan lineage differs: {key}")
    session = load(Path(plan["session"]["path"]))
    if session.get("state") != "ready-to-launch" or session.get("blockedChecks"):
        raise ValueError("launch plan references a blocked session")
    argv = plan.get("argv", [])
    if len(argv) != 7 or not argv[2].startswith("-ExecutePythonScript=") or not argv[3].startswith("-GahyeonIdentitySession="):
        raise ValueError("launch arguments differ")
    if plan.get("stopsBefore") != ["components-from-mesh", "marker-correction", "identity-solve", "conform-character"]:
        raise ValueError("launch scope expanded beyond import-only")
    return {"valid": True, "state": plan["state"], "qualityClaim": None}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--session", type=Path, required=True)
    parser.add_argument("--importer", type=Path, default=Path("unreal/GahyeonStage/Content/Python/gahyeon_import_metahuman_identity_v002.py"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.verify:
        result = verify(args.output)
    else:
        if args.output.exists():
            raise SystemExit(f"refusing to overwrite: {args.output}")
        result = build(args.session, args.importer)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
