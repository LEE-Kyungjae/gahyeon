#!/usr/bin/env python3
"""Run the generated-mesh cleanup/evaluation DAG without promoting it to production."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any, Callable


GO_VIEWS = [
    "face-front", "face-left-45", "face-right-45", "face-left-profile",
    "face-right-profile", "body-front", "body-left", "body-right", "body-rear",
]


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def validate_candidate_receipt(candidate: Path) -> dict[str, Any]:
    receipt_path = candidate / "raw/result.json"
    manifest_path = candidate / "candidate.json"
    if not receipt_path.is_file() or not manifest_path.is_file():
        raise ValueError("generated candidate receipt or manifest missing")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (manifest.get("status") != "generated" or
            receipt.get("claim") != "temporary-shape-estimate-not-production-mesh" or
            receipt.get("productionMeshAllowed") is not False):
        raise ValueError("candidate is not a generated temporary shape estimate")
    mesh = candidate / "raw" / receipt.get("mesh", {}).get("file", "")
    if (not mesh.is_file() or mesh.stat().st_size != receipt["mesh"].get("bytes") or
            digest(mesh) != receipt["mesh"].get("sha256")):
        raise ValueError("raw mesh differs from runner receipt")
    roles = {item.get("role"): item for item in manifest.get("outputs", [])}
    if (roles.get("raw-mesh", {}).get("sha256") != receipt["mesh"]["sha256"] or
            roles.get("runner-receipt", {}).get("sha256") != digest(receipt_path)):
        raise ValueError("candidate manifest and runner receipt differ")
    return {"model": receipt["model"], "seed": receipt["seed"], "mesh": mesh,
            "receiptSha256": digest(receipt_path)}


def _command(stage: str, argv: list[str], outputs: list[Path]) -> dict[str, Any]:
    return {"id": stage, "argv": argv, "outputs": [str(path) for path in outputs]}


def build_postprocess_plan(config: dict[str, Any], candidate: Path, blender: Path,
                           workspace: Path) -> dict[str, Any]:
    if (config.get("schemaVersion") != 1 or config.get("displayProfile") != "looking-glass-go" or
            config.get("resolution") != [1440, 2560] or config.get("views") != GO_VIEWS):
        raise ValueError("postprocess must use exact Looking Glass Go contract")
    if (config.get("productionMeshAllowed") is not False or
            config.get("failurePolicy") != "stop-on-error" or config.get("overwrite") is not False):
        raise ValueError("postprocess must fail closed")
    evidence = validate_candidate_receipt(candidate)
    output = candidate / "postprocess"
    if output.exists() and any(output.iterdir()):
        raise ValueError("postprocess output already exists")
    mesh = evidence["mesh"]
    normalized, cleanup = output / "normalized.blend", output / "cleanup-report.json"
    qa, renders = output / "qa-scene.blend", output / "renders"
    evaluation = output / "evaluation"
    face, body = evaluation / "face-measurements.json", evaluation / "body-measurements.json"
    face_delta, body_delta = evaluation / "face-comparison.json", evaluation / "body-comparison.json"
    quality = [evaluation / f"render-quality-{view}.json" for view in GO_VIEWS]
    views = sum((["--view", view] for view in GO_VIEWS), [])
    py = str(workspace / "character_pipeline/evaluation")
    commands = [
        _command("cleanup", [str(blender), "--background", "--factory-startup", "--python",
                 str(workspace / "character_pipeline/blender/scripts/cleanup_reconstruction_candidate.py"),
                 "--", "--input", str(mesh), "--output", str(normalized), "--report", str(cleanup)],
                 [normalized, cleanup]),
        _command("qa-scene", [str(blender), "--background", str(normalized), "--python",
                 str(workspace / "character_pipeline/blender/scripts/setup_reconstruction_qa_scene.py"),
                 "--", "--output", str(qa)], [qa]),
        _command("render", [str(blender), "--background", str(qa), "--python",
                 str(workspace / "character_pipeline/blender/scripts/render_fixed_baseline.py"), "--",
                 "--output-dir", str(renders), *views, "--width", "1440", "--height", "2560"],
                 [renders / "render-manifest.json", *[renders / f"{view}.png" for view in GO_VIEWS]]),
    ]
    for view, report in zip(GO_VIEWS, quality):
        commands.append(_command(f"render-quality:{view}", ["python3", f"{py}/evaluate_render_quality.py",
                        str(renders / f"{view}.png"), "--width", "1440", "--height", "2560",
                        "--view-class", "face" if view.startswith("face-") else "body", "--output", str(report)],
                        [report]))
    commands += [
        _command("face-measurement", ["python3", f"{py}/measure_face_landmarks.py",
                 str(renders / "face-front.png"), "--output", str(face)], [face]),
        _command("body-measurement", ["python3", f"{py}/measure_body_landmarks.py",
                 str(renders / "body-front.png"), "--output", str(body)], [body]),
        _command("face-comparison", ["python3", f"{py}/compare_face_measurements.py",
                 str(workspace / "character_pipeline/iterations/v001/evaluation/identity-landmarks-v1/canonical-03.json"),
                 str(face), "--prototype-eyes", "--output", str(face_delta)], [face_delta]),
        _command("body-comparison", ["python3", f"{py}/compare_body_measurements.py",
                 str(workspace / "character_pipeline/iterations/v001/evaluation/body-landmarks-v1/canonical-16.json"),
                 str(body), "--output", str(body_delta)], [body_delta]),
    ]
    return {"schemaVersion": 1, "state": "planned", "candidate": str(candidate),
            "runnerReceiptSha256": evidence["receiptSha256"], "model": evidence["model"],
            "seed": evidence["seed"], "displayProfile": "looking-glass-go",
            "panelResolution": [1440, 2560], "views": list(GO_VIEWS), "commands": commands,
            "completed": [], "productionMeshAllowed": False,
            "expected": {"normalizedBlend": str(normalized), "cleanupReport": str(cleanup),
                         "qaScene": str(qa), "renderManifest": str(renders / "render-manifest.json"),
                         "faceMeasurements": str(face), "bodyMeasurements": str(body),
                         "faceComparison": str(face_delta), "bodyComparison": str(body_delta),
                         "renderQuality": [str(path) for path in quality], "views": list(GO_VIEWS)}}


def validate_postprocess_state(config: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    if state.get("state") not in {"planned", "running", "failed", "completed"}:
        raise ValueError("invalid postprocess state")
    if (state.get("displayProfile") != "looking-glass-go" or state.get("panelResolution") != [1440, 2560]
            or state.get("productionMeshAllowed") is not False):
        raise ValueError("postprocess state overclaims output")
    ids = [item.get("id") for item in state.get("commands", [])]
    required = ["cleanup", "qa-scene", "render", *[f"render-quality:{view}" for view in GO_VIEWS],
                "face-measurement", "body-measurement", "face-comparison", "body-comparison"]
    if ids != required:
        raise ValueError("postprocess DAG differs")
    if state.get("expected", {}).get("views") != GO_VIEWS or config.get("views") != GO_VIEWS:
        raise ValueError("postprocess render views differ")
    return {"valid": True, "state": state["state"], "stages": len(ids), "views": len(GO_VIEWS),
            "productionMeshAllowed": False}


def _verify_outputs(command: dict[str, Any]) -> list[dict[str, Any]]:
    results = []
    for value in command["outputs"]:
        path = Path(value)
        if not path.is_file() or path.stat().st_size == 0:
            raise RuntimeError(f"stage {command['id']} output missing: {path}")
        results.append({"path": str(path), "bytes": path.stat().st_size, "sha256": digest(path)})
    return results


def execute_postprocess(config: dict[str, Any], state_path: Path,
                        runner: Callable[..., Any] = subprocess.run) -> dict[str, Any]:
    state = json.loads(state_path.read_text(encoding="utf-8"))
    validate_postprocess_state(config, state)
    validate_candidate_receipt(Path(state["candidate"]))
    completed = state.get("completed", [])
    if len(completed) > len(state["commands"]):
        raise ValueError("completed prefix exceeds DAG")
    for index, prior in enumerate(completed):
        command = state["commands"][index]
        if prior.get("id") != command["id"] or prior.get("outputs") != _verify_outputs(command):
            raise ValueError(f"completed prefix checksum differs at {command['id']}")
    state["state"] = "running"
    state.pop("failure", None)
    write_json_atomic(state_path, state)
    try:
        for command in state["commands"][len(completed):]:
            runner(command["argv"], check=True)
            completed.append({"id": command["id"], "outputs": _verify_outputs(command)})
            state["completed"] = completed
            write_json_atomic(state_path, state)
    except Exception as error:
        state["state"] = "failed"
        state["failure"] = {"stage": state["commands"][len(completed)]["id"],
                            "type": type(error).__name__, "message": str(error)}
        write_json_atomic(state_path, state)
        raise
    state["state"] = "completed"
    state["claim"] = "evaluated-temporary-shape-estimate-not-production-mesh"
    write_json_atomic(state_path, state)
    return state


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("character_pipeline/config/candidate_postprocess.json"))
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--blender", type=Path, default=Path("/opt/homebrew/bin/blender"))
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    if args.execute:
        result = execute_postprocess(config, args.state)
    else:
        if not args.candidate:
            parser.error("--candidate is required when planning")
        result = build_postprocess_plan(config, args.candidate.resolve(), args.blender.resolve(), args.workspace.resolve())
        if args.state.exists():
            raise SystemExit(f"refusing to overwrite: {args.state}")
        write_json_atomic(args.state, result)
    print(json.dumps(validate_postprocess_state(config, result)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
