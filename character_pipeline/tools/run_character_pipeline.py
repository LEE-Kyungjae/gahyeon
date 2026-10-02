#!/usr/bin/env python3
"""Run ordered character gates without shell interpolation or silent continuation."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
from typing import Any, Callable


Runner = Callable[..., subprocess.CompletedProcess[str]]


def validate_pipeline_run(config: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
    stage_ids = [stage["id"] for stage in config["stages"]]
    results = report.get("stages", [])
    observed = [stage.get("id") for stage in results]
    if observed != stage_ids[:len(observed)] or len(observed) > len(stage_ids):
        raise ValueError("pipeline stages are missing, duplicated or out of order")
    terminal = report.get("state")
    if terminal not in {"completed", "blocked", "failed"}:
        raise ValueError("invalid pipeline run state")
    if terminal == "completed" and len(results) != len(stage_ids):
        raise ValueError("completed pipeline omitted stages")
    if not results:
        raise ValueError("pipeline run has no stage evidence")
    if terminal in {"blocked", "failed"} and results[-1].get("state") != terminal:
        raise ValueError("terminal state does not match final executed stage")
    for result in results:
        if result.get("state") not in {"passed", "blocked", "failed"}:
            raise ValueError("invalid stage state")
        if not isinstance(result.get("exitCode"), int):
            raise ValueError("stage exit code missing")
        if not isinstance(result.get("stdout"), str) or not isinstance(result.get("stderr"), str):
            raise ValueError("stage logs missing")
    return {"valid": True, "state": terminal, "executedStages": len(results),
            "configuredStages": len(stage_ids), "displayProfile": report.get("displayProfile")}


def run_pipeline(config: dict[str, Any], root: Path, runner: Runner = subprocess.run) -> dict[str, Any]:
    if config.get("schemaVersion") != 1 or config.get("displayProfile") != "looking-glass-go":
        raise ValueError("unsupported orchestration config or display profile")
    if config.get("failurePolicy") != "stop-on-error-or-blocked":
        raise ValueError("pipeline must fail closed")
    report: dict[str, Any] = {
        "schemaVersion": 1,
        "observedAt": datetime.now(timezone.utc).isoformat(),
        "displayProfile": "looking-glass-go",
        "state": "completed",
        "stages": [],
    }
    for stage in config.get("stages", []):
        command = stage.get("command")
        if not isinstance(command, list) or not command or not all(isinstance(v, str) and v for v in command):
            raise ValueError(f"invalid command for {stage.get('id')}")
        completed = runner(command, cwd=root, capture_output=True, text=True, check=False)
        state = "passed"
        payload = None
        if completed.returncode != 0:
            state = "failed"
        elif stage.get("jsonStateField"):
            try:
                payload = json.loads(completed.stdout)
                observed = payload[stage["jsonStateField"]]
            except (json.JSONDecodeError, KeyError, TypeError) as error:
                completed = subprocess.CompletedProcess(command, 2, completed.stdout,
                                                        f"invalid JSON state output: {error}")
                state = "failed"
            else:
                if observed in stage.get("blockedStates", []):
                    state = "blocked"
                elif observed not in stage.get("continueStates", []):
                    state = "failed"
        result = {"id": stage["id"], "state": state, "exitCode": completed.returncode,
                  "command": command, "stdout": completed.stdout, "stderr": completed.stderr}
        if payload is not None:
            result["result"] = payload
        report["stages"].append(result)
        if state != "passed":
            report["state"] = state
            break
    validate_pipeline_run(config, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("character_pipeline/config/orchestration.json"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f"refusing to overwrite pipeline report: {args.output}")
    config = json.loads(args.config.read_text(encoding="utf-8"))
    report = run_pipeline(config, args.workspace.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(validate_pipeline_run(config, report)))
    return 0 if report["state"] == "completed" else 3


if __name__ == "__main__":
    raise SystemExit(main())
