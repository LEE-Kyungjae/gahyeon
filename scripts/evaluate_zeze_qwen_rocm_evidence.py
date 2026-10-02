#!/usr/bin/env python3
"""Fail closed when zeze Qwen ROCm evidence contains a GPU runtime failure."""

from __future__ import annotations

import argparse
from pathlib import Path


BLOCKING_MARKERS = (
    "ROCm error: unspecified launch failure",
    "CUDA error: unspecified launch failure",
    "GPU reset begin!",
    "device wedged, but recovered through reset",
    "SystemOOM",
    "Out of memory: Killed process",
)


def evaluate_zeze_qwen_rocm_evidence(*evidence: str) -> list[str]:
    combined = "\n".join(evidence)
    return [marker for marker in BLOCKING_MARKERS if marker in combined]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", nargs="+", type=Path)
    args = parser.parse_args()
    findings = evaluate_zeze_qwen_rocm_evidence(
        *(path.read_text(encoding="utf-8", errors="replace") for path in args.evidence)
    )
    if findings:
        print("zeze Qwen ROCm promotion blocked: " + ", ".join(findings))
        return 1
    print("zeze Qwen ROCm evidence contains no known blocking marker")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
