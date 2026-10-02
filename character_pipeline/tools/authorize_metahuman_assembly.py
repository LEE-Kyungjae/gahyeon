#!/usr/bin/env python3
"""Issue a fail-closed authorization for MetaHuman assembly after human identity QA."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from post_conform_identity_checkpoint_v002 import load, resolve, verify_decision


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def authorize(decision_path: Path, solve_receipt_path: Path, output_path: Path) -> dict:
    decision_path = decision_path.resolve()
    solve_receipt_path = solve_receipt_path.resolve()
    output_path = output_path.resolve()
    if output_path.exists():
        raise ValueError(f"refusing to overwrite: {output_path}")

    verdict = verify_decision(decision_path)
    if verdict.get("surfaceWorkAllowed") is not True:
        raise ValueError("human identity decision rejected assembly")

    decision = load(decision_path)
    solve = load(solve_receipt_path)
    if (solve.get("result") != "SUCCESS" or solve.get("status") not in {"draft", "candidate"}
            or solve.get("productionReady") is not False or solve.get("identityApproved") is not False):
        raise ValueError("solve receipt is not an unapproved successful identity solve")
    identity_asset = solve.get("identityAsset")
    if not isinstance(identity_asset, str) or not identity_asset.startswith("/Game/"):
        raise ValueError("solve receipt lacks a valid identity asset")

    capture_item = decision.get("captureManifest", {})
    capture_path = resolve(decision_path, capture_item.get("uri", ""))
    capture = load(capture_path)
    job_item = capture.get("job", {})
    job_path = Path(job_item.get("path", ""))
    job = load(job_path)
    if job.get("identityAsset") != identity_asset:
        raise ValueError("five-view capture is not bound to the solved identity asset")
    if job.get("solveReceipt", {}).get("sha256") != sha256(solve_receipt_path):
        raise ValueError("five-view capture is not bound to this solve receipt")

    iteration = solve.get("iteration")
    if decision.get("reviewedIteration") != iteration:
        raise ValueError("human decision is not bound to the solved iteration")

    result = {
        "schemaVersion": 1,
        "state": "metahuman-assembly-authorized",
        "iteration": iteration,
        "identityAsset": identity_asset,
        "decision": {"path": str(decision_path), "sha256": sha256(decision_path)},
        "captureManifest": {"path": str(capture_path), "sha256": sha256(capture_path)},
        "solveReceipt": {"path": str(solve_receipt_path), "sha256": sha256(solve_receipt_path)},
        "reviewer": decision["reviewer"],
        "canonicalIndices": [3, 6, 7, 8],
        "verifiedViews": 5,
        "automaticApproval": False,
        "productionReady": False,
        "qualityClaim": None,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--decision", type=Path, required=True)
    parser.add_argument("--solve-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = authorize(args.decision, args.solve_receipt, args.output)
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
